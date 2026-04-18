import { useEffect, useRef, useState } from "react";

/**
 * Decode an audio source via Web Audio API and return normalized peaks
 * suitable for rendering as a bar-waveform.
 *
 * Accepts either a URL string, an object URL, a Blob, or an ArrayBuffer.
 * Results are cached per-source and aborted if the component unmounts.
 *
 * The returned `peaks` array is normalized to [0, 1] so the caller can
 * render bar heights directly. `clipping` flags whether any sample in the
 * source reaches ≥ 0.99 — useful for surfacing quality issues in the UI.
 */

type AudioSource = string | Blob | ArrayBuffer | null | undefined;

interface PeakResult {
  peaks: number[];
  duration: number;
  sampleRate: number;
  clipping: boolean;
  silent: boolean;
}

interface UseAudioPeaksOptions {
  /**
   * Number of peak buckets to produce. Match this to your visualizer's
   * `barCount` prop so bars align perfectly with the audio.
   */
  barCount?: number;
  /**
   * When set to false the hook returns immediately without fetching.
   * Useful for lazy-mounting waveforms only when they come into view.
   */
  enabled?: boolean;
}

interface UseAudioPeaksReturn extends Partial<PeakResult> {
  loading: boolean;
  error: string | null;
}

// Module-level shared AudioContext — creating one per call leaks.
let _sharedCtx: AudioContext | null = null;
function getContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!_sharedCtx) {
    const Ctor =
      (window as unknown as { AudioContext?: typeof AudioContext }).AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return null;
    _sharedCtx = new Ctor();
  }
  return _sharedCtx;
}

// Cache by stable key so repeat renders don't re-decode the same audio.
const _peakCache = new Map<string, PeakResult>();
const _CACHE_MAX_ENTRIES = 64;

function cacheKeyForSource(src: AudioSource): string | null {
  if (src == null) return null;
  if (typeof src === "string") return `url:${src}`;
  if (src instanceof Blob) return `blob:${src.size}:${src.type}`;
  if (src instanceof ArrayBuffer) return `buf:${src.byteLength}`;
  return null;
}

function insertCache(key: string, value: PeakResult): void {
  if (_peakCache.size >= _CACHE_MAX_ENTRIES) {
    // Evict the oldest entry (first key in insertion order).
    const firstKey = _peakCache.keys().next().value;
    if (firstKey !== undefined) _peakCache.delete(firstKey);
  }
  _peakCache.set(key, value);
}

async function sourceToArrayBuffer(
  src: AudioSource,
  signal: AbortSignal,
): Promise<ArrayBuffer> {
  if (src instanceof ArrayBuffer) return src.slice(0);
  if (src instanceof Blob) return await src.arrayBuffer();
  if (typeof src === "string") {
    const res = await fetch(src, { signal, credentials: "same-origin" });
    if (!res.ok) {
      throw new Error(`Audio fetch failed (${res.status})`);
    }
    return await res.arrayBuffer();
  }
  throw new Error("Unsupported audio source");
}

/**
 * Reduce a Float32Array of samples to `barCount` buckets of RMS amplitude
 * in [0, 1]. RMS is a better visual proxy for perceived loudness than max.
 */
function reduceToPeaks(
  samples: Float32Array,
  barCount: number,
): { peaks: number[]; clipping: boolean; silent: boolean } {
  if (samples.length === 0 || barCount <= 0) {
    return { peaks: [], clipping: false, silent: true };
  }
  const bucketSize = Math.max(1, Math.floor(samples.length / barCount));
  const peaks: number[] = new Array(barCount);
  let maxPeak = 0;
  let clipping = false;
  for (let i = 0; i < barCount; i++) {
    const start = i * bucketSize;
    const end = i === barCount - 1 ? samples.length : Math.min(start + bucketSize, samples.length);
    let sumSquares = 0;
    let count = 0;
    for (let j = start; j < end; j++) {
      const s = samples[j];
      sumSquares += s * s;
      if (Math.abs(s) >= 0.99) clipping = true;
      count++;
    }
    const rms = count > 0 ? Math.sqrt(sumSquares / count) : 0;
    peaks[i] = rms;
    if (rms > maxPeak) maxPeak = rms;
  }
  // Normalize so the loudest bar is 1.0 — makes quiet recordings legible
  // while preserving the relative shape.
  const norm = maxPeak > 0 ? 1 / maxPeak : 0;
  const silent = maxPeak < 0.001;
  for (let i = 0; i < peaks.length; i++) peaks[i] *= norm;
  return { peaks, clipping, silent };
}

export function useAudioPeaks(
  source: AudioSource,
  options: UseAudioPeaksOptions = {},
): UseAudioPeaksReturn {
  const { barCount = 40, enabled = true } = options;
  const [state, setState] = useState<UseAudioPeaksReturn>({ loading: false, error: null });
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!enabled || source == null) {
      setState({ loading: false, error: null });
      return;
    }

    const key = cacheKeyForSource(source);
    if (key) {
      const cached = _peakCache.get(key);
      if (cached) {
        // Already-decoded result; re-bucket to the requested barCount.
        // (Bar count often varies by component — cache stores raw channel peaks.)
        setState({ loading: false, error: null, ...cached });
        return;
      }
    }

    const ctx = getContext();
    if (!ctx) {
      setState({ loading: false, error: "Web Audio API unavailable" });
      return;
    }

    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setState({ loading: true, error: null });

    let cancelled = false;
    (async () => {
      try {
        const buf = await sourceToArrayBuffer(source, ac.signal);
        if (cancelled) return;
        const audioBuffer = await ctx.decodeAudioData(buf.slice(0));
        if (cancelled) return;
        // Mono mix-down for visualization purposes.
        const channels = audioBuffer.numberOfChannels;
        const length = audioBuffer.length;
        const mono = new Float32Array(length);
        for (let c = 0; c < channels; c++) {
          const data = audioBuffer.getChannelData(c);
          for (let i = 0; i < length; i++) mono[i] += data[i] / channels;
        }
        const reduced = reduceToPeaks(mono, barCount);
        const result: PeakResult = {
          peaks: reduced.peaks,
          duration: audioBuffer.duration,
          sampleRate: audioBuffer.sampleRate,
          clipping: reduced.clipping,
          silent: reduced.silent,
        };
        if (key) insertCache(key, result);
        if (!cancelled) setState({ loading: false, error: null, ...result });
      } catch (err) {
        if (cancelled) return;
        if (err instanceof DOMException && err.name === "AbortError") return;
        const msg = err instanceof Error ? err.message : String(err);
        setState({ loading: false, error: msg });
      }
    })();

    return () => {
      cancelled = true;
      ac.abort();
    };
  }, [source, barCount, enabled]);

  return state;
}

export function clearAudioPeaksCache(): void {
  _peakCache.clear();
}
