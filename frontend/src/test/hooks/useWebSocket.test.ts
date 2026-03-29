import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTrainingProgress } from '../../hooks/useWebSocket';

vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
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
});
