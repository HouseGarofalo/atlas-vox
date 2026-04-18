import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useTrainingProgress } from '../../hooks/useWebSocket';

vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

vi.mock('../../services/api', () => ({
  default: {
    getTrainingJob: vi.fn(),
  },
}));
import apiClient from '../../services/api';

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static CLOSED = 3;
  static OPEN = 1;
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = 0;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  close() {
    this.readyState = 3;
    this.onclose?.();
  }

  send(_data: string) {
    // noop
  }
}
(MockWebSocket as unknown as { CLOSED: number }).CLOSED = 3;

beforeEach(() => {
  MockWebSocket.instances = [];
  vi.stubGlobal('WebSocket', MockWebSocket);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('useTrainingProgress', () => {
  it('returns null progress initially', () => {
    const { result } = renderHook(() => useTrainingProgress(null));
    expect(result.current.progress).toBeNull();
    expect(result.current.connected).toBe(false);
  });

  it('does not create WebSocket when jobId is null', () => {
    renderHook(() => useTrainingProgress(null));
    expect(MockWebSocket.instances).toHaveLength(0);
  });

  it('creates WebSocket when jobId is provided', () => {
    renderHook(() => useTrainingProgress('job-123'));
    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toContain('job-123');
  });

  it('cleans up WebSocket on unmount', () => {
    const { unmount } = renderHook(() => useTrainingProgress('job-123'));
    const ws = MockWebSocket.instances[0];
    const closeSpy = vi.spyOn(ws, 'close');
    unmount();
    expect(closeSpy).toHaveBeenCalled();
  });

  it('does not reconnect on terminal state', () => {
    vi.useFakeTimers();

    renderHook(() => useTrainingProgress('job-1'));

    // Should have created exactly one WebSocket
    expect(MockWebSocket.instances).toHaveLength(1);
    const ws = MockWebSocket.instances[0];

    // Simulate connection open
    act(() => {
      ws.onopen?.();
    });

    // Simulate a message with terminal state (DONE)
    act(() => {
      const msg = JSON.stringify({ job_id: 'job-1', state: 'DONE', percent: 100, status: 'Complete' });
      ws.onmessage?.({ data: msg });
    });

    // The hook should have called ws.close() which triggers onclose.
    // After close, advance timers to ensure no reconnect timer fires.
    vi.advanceTimersByTime(10000);

    // WebSocket constructor should NOT have been called again (no reconnect)
    expect(MockWebSocket.instances).toHaveLength(1);

    vi.useRealTimers();
  });

  it('exposes reconnecting status after a transient close', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useTrainingProgress('job-re'));
    const ws = MockWebSocket.instances[0];
    act(() => {
      ws.onopen?.();
    });
    expect(result.current.connectionStatus).toBe('connected');

    // Simulate an unexpected close.
    act(() => {
      ws.onclose?.();
    });
    expect(result.current.connectionStatus).toBe('reconnecting');
    expect(result.current.connectionBanner).toContain('Reconnecting');

    vi.useRealTimers();
  });

  it('falls back to polling after MAX_RECONNECT_ATTEMPTS WebSocket failures', async () => {
    vi.useFakeTimers();
    // Every getTrainingJob resolves with a non-terminal state so polling keeps ticking.
    (apiClient.getTrainingJob as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 'job-poll',
      status: 'training',
      progress: 0.42,
      current_step: 'Training model',
    });

    const { result } = renderHook(() => useTrainingProgress('job-poll'));
    expect(MockWebSocket.instances).toHaveLength(1);

    // Burn through all WebSocket reconnects: close the current ws, advance
    // past its backoff timer, repeat. MAX_RECONNECT_ATTEMPTS = 5 so we need
    // 6 closes in total (1 initial + 5 retries) before the hook gives up and
    // falls back to HTTP polling.
    for (let attempt = 0; attempt < 6; attempt++) {
      const ws = MockWebSocket.instances[MockWebSocket.instances.length - 1];
      await act(async () => {
        ws.onclose?.();
        // Let any synchronously-scheduled reconnect timer fire.
        await vi.advanceTimersByTimeAsync(60000);
      });
    }

    // After exhausting WS attempts, hook should be polling.
    expect(result.current.connectionStatus).toBe('polling');
    expect(result.current.connectionBanner).toContain('polling');

    // The initial poll should have fired already; confirm it was called.
    expect(apiClient.getTrainingJob).toHaveBeenCalledWith('job-poll');

    // Let the poll's async chain resolve and flush any pending microtasks.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(result.current.progress?.percent).toBe(42);
    expect(result.current.progress?.state).toBe('PROGRESS');

    vi.useRealTimers();
  });

  it('stops polling on terminal state', async () => {
    vi.useFakeTimers();
    (apiClient.getTrainingJob as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 'job-done',
      status: 'completed',
      progress: 1.0,
      current_step: 'Done',
    });

    const { result } = renderHook(() => useTrainingProgress('job-done'));

    // Force-drop to polling by burning through reconnects.
    for (let attempt = 0; attempt < 6; attempt++) {
      const ws = MockWebSocket.instances[MockWebSocket.instances.length - 1];
      await act(async () => {
        ws.onclose?.();
        await vi.advanceTimersByTimeAsync(60000);
      });
    }

    // Let the poll's async chain resolve.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(result.current.progress?.state).toBe('DONE');
    expect(result.current.connectionStatus).toBe('idle');

    vi.useRealTimers();
  });
});
