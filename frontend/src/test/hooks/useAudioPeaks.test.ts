import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useAudioPeaks, clearAudioPeaksCache } from "../../hooks/useAudioPeaks";

// Minimal mock of the Web Audio API.
// - decodeAudioData returns a synthetic AudioBuffer whose channel data we
//   control so we can verify peak reduction and clipping detection.
// - fetch returns the raw ArrayBuffer encoded as the "WAV-ish" blob we fed in.

class MockAudioBuffer {
  readonly numberOfChannels = 1;
  readonly sampleRate = 44100;
  readonly length: number;
  private readonly samples: Float32Array;
  constructor(samples: Float32Array) {
    this.samples = samples;
    this.length = samples.length;
  }
  get duration() {
    return this.length / this.sampleRate;
  }
  getChannelData(_channel: number) {
    return this.samples;
  }
}

function makeAudioContextCtor(samples: Float32Array) {
  return class MockAudioContext {
    // Mirror the minimal API our hook uses.
    async decodeAudioData(_buf: ArrayBuffer): Promise<MockAudioBuffer> {
      return new MockAudioBuffer(samples);
    }
  };
}

function installMocks(samples: Float32Array) {
  // Some envs only have webkitAudioContext; we set both for safety.
  const Ctor = makeAudioContextCtor(samples);
  (globalThis as unknown as { AudioContext: unknown }).AudioContext = Ctor;
  (globalThis as unknown as { webkitAudioContext: unknown }).webkitAudioContext = Ctor;
}

describe("useAudioPeaks", () => {
  beforeEach(() => {
    clearAudioPeaksCache();
    // Reset any lazily-built shared context between tests so swapping the
    // AudioContext mock per test actually takes effect.
    // (The hook lazy-creates one on first call; importing it fresh is cleaner
    // than poking its module internals.)
    vi.resetModules();
  });

  afterEach(() => {
    delete (globalThis as unknown as { fetch?: unknown }).fetch;
  });

  it("returns empty state when source is null", () => {
    const { result } = renderHook(() => useAudioPeaks(null));
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.peaks).toBeUndefined();
  });

  it("decodes a Blob and produces normalized peaks", async () => {
    // Sine wave at amplitude 0.5 — avoids tripping the clipping flag (>=0.99).
    const samples = new Float32Array(44100);
    for (let i = 0; i < samples.length; i++) {
      samples[i] = 0.5 * Math.sin((i / 44100) * 2 * Math.PI * 440);
    }
    installMocks(samples);
    // Re-import the hook so it picks up the fresh mocked AudioContext.
    const { useAudioPeaks: freshHook } = await import("../../hooks/useAudioPeaks?mock1");
    const blob = new Blob([new Uint8Array(8)], { type: "audio/wav" });
    const { result } = renderHook(() => freshHook(blob, { barCount: 8 }));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeNull();
    expect(result.current.peaks).toHaveLength(8);
    // Each bar should be finite and within [0, 1.0].
    for (const p of result.current.peaks!) {
      expect(p).toBeGreaterThanOrEqual(0);
      expect(p).toBeLessThanOrEqual(1.0001);
    }
    // Max peak should be normalized to 1.
    expect(Math.max(...result.current.peaks!)).toBeCloseTo(1, 1);
    expect(result.current.clipping).toBe(false);
    expect(result.current.silent).toBe(false);
  });

  it("flags clipping when samples reach full scale", async () => {
    const samples = new Float32Array(1024).fill(1.0); // Pure clipping.
    installMocks(samples);
    const { useAudioPeaks: freshHook } = await import("../../hooks/useAudioPeaks?mock2");
    const blob = new Blob([new Uint8Array(8)], { type: "audio/wav" });
    const { result } = renderHook(() => freshHook(blob, { barCount: 4 }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.clipping).toBe(true);
  });

  it("flags silence when samples are near zero", async () => {
    const samples = new Float32Array(1024); // all zeros
    installMocks(samples);
    const { useAudioPeaks: freshHook } = await import("../../hooks/useAudioPeaks?mock3");
    const blob = new Blob([new Uint8Array(8)], { type: "audio/wav" });
    const { result } = renderHook(() => freshHook(blob, { barCount: 4 }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.silent).toBe(true);
  });

  it("is a no-op when enabled=false", () => {
    const blob = new Blob([new Uint8Array(8)], { type: "audio/wav" });
    const { result } = renderHook(() => useAudioPeaks(blob, { enabled: false }));
    expect(result.current.loading).toBe(false);
    expect(result.current.peaks).toBeUndefined();
  });
});
