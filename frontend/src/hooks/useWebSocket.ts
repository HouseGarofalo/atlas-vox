import { useEffect, useRef, useState, useCallback } from "react";

interface WSProgress {
  job_id: string;
  state: string;
  percent: number;
  status: string;
  version_id?: string;
  error?: string;
}

export function useTrainingProgress(jobId: string | null) {
  const [progress, setProgress] = useState<WSProgress | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!jobId) return;
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${proto}//${window.location.host}/api/v1/training/jobs/${jobId}/progress`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onmessage = (e) => {
      try {
        const data: WSProgress = JSON.parse(e.data);
        setProgress(data);
        // Auto-close on terminal states
        if (["DONE", "FAILURE", "REVOKED"].includes(data.state)) {
          ws.close();
        }
      } catch { /* ignore parse errors */ }
    };
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
  }, [jobId]);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { progress, connected };
}
