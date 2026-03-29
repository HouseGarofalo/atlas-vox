import { useEffect, useRef, useState, useCallback } from "react";
import { createLogger } from "../utils/logger";

const logger = createLogger("useWebSocket");

interface WSProgress {
  job_id: string;
  state: string;
  percent: number;
  status: string;
  version_id?: string;
  error?: string;
}

const MAX_RECONNECT_ATTEMPTS = 3;
const TERMINAL_STATES = ["DONE", "FAILURE", "REVOKED"];

export function useTrainingProgress(jobId: string | null) {
  const [progress, setProgress] = useState<WSProgress | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const isTerminalRef = useRef(false);

  const connect = useCallback(() => {
    if (!jobId) return;
    // Don't reconnect if we reached a terminal state
    if (isTerminalRef.current) return;

    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${proto}//${window.location.host}/api/v1/training/jobs/${jobId}/progress`);
    wsRef.current = ws;

    ws.onopen = () => {
      logger.info("connection_open", { job_id: jobId });
      setConnected(true);
      reconnectAttemptRef.current = 0; // Reset on successful connection
    };
    ws.onmessage = (e) => {
      try {
        const data: WSProgress = JSON.parse(e.data);
        setProgress(data);
        // Auto-close on terminal states
        if (TERMINAL_STATES.includes(data.state)) {
          logger.info("terminal_state", { job_id: jobId, state: data.state });
          isTerminalRef.current = true;
          ws.close();
        }
      } catch (err) {
        logger.warn("parse_error", { data: String(e.data), error: String(err) });
      }
    };
    ws.onclose = () => {
      logger.info("connection_close", { job_id: jobId });
      setConnected(false);

      // Attempt reconnect if not terminal and under max attempts
      if (!isTerminalRef.current && reconnectAttemptRef.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = Math.pow(2, reconnectAttemptRef.current) * 1000; // 1s, 2s, 4s
        logger.info("reconnect_scheduled", { job_id: jobId, attempt: reconnectAttemptRef.current + 1, delay_ms: delay });
        reconnectAttemptRef.current += 1;
        reconnectTimerRef.current = setTimeout(connect, delay);
      }
    };
    ws.onerror = () => {
      logger.error("connection_error", { job_id: jobId });
      setConnected(false);
      // onclose will fire after onerror, so reconnect is handled there
    };
  }, [jobId]);

  useEffect(() => {
    isTerminalRef.current = false;
    reconnectAttemptRef.current = 0;
    connect();
    return () => {
      clearTimeout(reconnectTimerRef.current);
      isTerminalRef.current = true; // Prevent reconnect during cleanup
      wsRef.current?.close();
    };
  }, [connect]);

  return { progress, connected };
}
