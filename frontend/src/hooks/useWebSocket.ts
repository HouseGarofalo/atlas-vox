import { useEffect, useRef, useState, useCallback } from "react";
import { createLogger } from "../utils/logger";
import apiClient from "../services/api";

const logger = createLogger("useWebSocket");

interface WSProgress {
  job_id: string;
  state: string;
  percent: number;
  status: string;
  version_id?: string;
  error?: string;
}

/**
 * Reported connection mode for the progress feed.
 *
 * - ``connecting``: first WebSocket attempt in flight.
 * - ``connected``: live WebSocket, real-time updates.
 * - ``reconnecting``: transient WebSocket failure, backoff in progress.
 * - ``polling``: WebSocket unreachable after ``MAX_RECONNECT_ATTEMPTS``
 *   attempts — HTTP polling fallback active so the UI keeps updating.
 * - ``failed``: polling itself has failed; no live updates at all.
 * - ``idle``: no ``jobId`` currently subscribed.
 */
export type ProgressConnectionStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "polling"
  | "failed";

interface UseTrainingProgressResult {
  progress: WSProgress | null;
  connected: boolean;
  connectionStatus: ProgressConnectionStatus;
  /**
   * Human-readable message suitable for a banner when
   * ``connectionStatus`` is ``reconnecting`` / ``polling`` / ``failed``.
   * ``null`` when the feed is healthy or idle.
   */
  connectionBanner: string | null;
}

const MAX_RECONNECT_ATTEMPTS = 5;
const POLL_INTERVAL_MS = 5000;
const TERMINAL_STATES = ["DONE", "FAILURE", "REVOKED"];

function trainingJobToProgress(job: {
  id: string;
  status: string;
  progress?: number;
  current_step?: string;
  error_message?: string;
  version_id?: string;
}): WSProgress {
  // Map backend TrainingJob into the same shape WebSocket frames produce.
  const pct =
    typeof job.progress === "number"
      ? job.progress > 1
        ? job.progress
        : Math.round(job.progress * 100)
      : 0;
  const statusMap: Record<string, string> = {
    completed: "DONE",
    failed: "FAILURE",
    cancelled: "REVOKED",
    training: "PROGRESS",
    queued: "PENDING",
    preprocessing: "PROGRESS",
  };
  return {
    job_id: job.id,
    state: statusMap[job.status] ?? job.status.toUpperCase(),
    percent: pct,
    status: job.current_step ?? job.status,
    version_id: job.version_id,
    error: job.error_message,
  };
}

export function useTrainingProgress(jobId: string | null): UseTrainingProgressResult {
  const [progress, setProgress] = useState<WSProgress | null>(null);
  const [connectionStatus, setConnectionStatus] =
    useState<ProgressConnectionStatus>("idle");

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const pollTimerRef = useRef<ReturnType<typeof setInterval>>();
  const isTerminalRef = useRef(false);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = undefined;
    }
  }, []);

  const pollOnce = useCallback(async (id: string): Promise<boolean> => {
    try {
      const job = await apiClient.getTrainingJob(id);
      const mapped = trainingJobToProgress(job as unknown as {
        id: string;
        status: string;
        progress?: number;
        current_step?: string;
        error_message?: string;
        version_id?: string;
      });
      setProgress(mapped);
      if (TERMINAL_STATES.includes(mapped.state)) {
        isTerminalRef.current = true;
        stopPolling();
        setConnectionStatus("idle");
      }
      return true;
    } catch (err) {
      logger.warn("poll_fetch_failed", { job_id: id, error: String(err) });
      return false;
    }
  }, [stopPolling]);

  const startPolling = useCallback(
    (id: string) => {
      if (pollTimerRef.current) return;
      setConnectionStatus("polling");
      // Immediate first fetch so the UI updates right away.
      pollOnce(id);
      pollTimerRef.current = setInterval(async () => {
        if (isTerminalRef.current) {
          stopPolling();
          return;
        }
        const ok = await pollOnce(id);
        if (!ok) setConnectionStatus("failed");
        else if (!isTerminalRef.current) setConnectionStatus("polling");
      }, POLL_INTERVAL_MS);
    },
    [pollOnce, stopPolling],
  );

  const connect = useCallback(() => {
    if (!jobId) return;
    if (isTerminalRef.current) return;
    // If we have already given up on WebSocket and fallen back to polling,
    // don't resurrect a new socket — the polling loop owns updates now.
    if (pollTimerRef.current) return;

    // If a previous WebSocket is still around, tear it down first.
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      try { wsRef.current.close(); } catch { /* ignore */ }
    }

    setConnectionStatus(reconnectAttemptRef.current === 0 ? "connecting" : "reconnecting");
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(
      `${proto}//${window.location.host}/api/v1/training/jobs/${jobId}/progress`,
    );
    wsRef.current = ws;

    ws.onopen = () => {
      logger.info("connection_open", { job_id: jobId });
      setConnectionStatus("connected");
      reconnectAttemptRef.current = 0;
      // Stop polling if we'd fallen back previously.
      stopPolling();
    };
    ws.onmessage = (e) => {
      try {
        const data: WSProgress = JSON.parse(e.data);
        setProgress(data);
        if (TERMINAL_STATES.includes(data.state)) {
          logger.info("terminal_state", { job_id: jobId, state: data.state });
          isTerminalRef.current = true;
          setConnectionStatus("idle");
          ws.close();
        }
      } catch (err) {
        logger.warn("parse_error", { data: String(e.data), error: String(err) });
      }
    };
    ws.onclose = () => {
      logger.info("connection_close", { job_id: jobId });

      if (isTerminalRef.current) {
        setConnectionStatus("idle");
        return;
      }

      if (reconnectAttemptRef.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = Math.min(30000, Math.pow(2, reconnectAttemptRef.current) * 1000);
        logger.info("reconnect_scheduled", {
          job_id: jobId,
          attempt: reconnectAttemptRef.current + 1,
          delay_ms: delay,
        });
        reconnectAttemptRef.current += 1;
        setConnectionStatus("reconnecting");
        reconnectTimerRef.current = setTimeout(connect, delay);
      } else {
        // Final failure — fall back to HTTP polling so the user still gets updates.
        logger.warn("ws_unreachable_switching_to_polling", { job_id: jobId });
        startPolling(jobId);
      }
    };
    ws.onerror = () => {
      logger.error("connection_error", { job_id: jobId });
      // onclose will fire after onerror — reconnect/polling handled there.
    };
  }, [jobId, startPolling, stopPolling]);

  useEffect(() => {
    if (!jobId) {
      setConnectionStatus("idle");
      return;
    }
    isTerminalRef.current = false;
    reconnectAttemptRef.current = 0;
    connect();
    return () => {
      clearTimeout(reconnectTimerRef.current);
      stopPolling();
      isTerminalRef.current = true;
      try {
        wsRef.current?.close();
      } catch {
        /* ignore */
      }
    };
  }, [jobId, connect, stopPolling]);

  const connectionBanner =
    connectionStatus === "reconnecting"
      ? "Reconnecting to live training feed…"
      : connectionStatus === "polling"
        ? "Live updates unavailable — polling every 5 seconds."
        : connectionStatus === "failed"
          ? "Cannot reach training service. Check your connection."
          : null;

  return {
    progress,
    connected: connectionStatus === "connected",
    connectionStatus,
    connectionBanner,
  };
}
