/**
 * Unified audio playback hook — replaces 4 separate audio player implementations
 * across VoiceLibrary, Comparison, Synthesis, and AudioDesign pages.
 *
 * Usage:
 *   const { play, pause, stop, isPlaying, currentUrl } = useAudioPlayer();
 *   <button onClick={() => isPlaying ? pause() : play(url)}>Play</button>
 */

import { useCallback, useEffect, useRef, useState } from "react";

interface AudioPlayerState {
  isPlaying: boolean;
  currentUrl: string | null;
  loading: boolean;
  duration: number;
  currentTime: number;
}

interface AudioPlayerActions {
  play: (url: string) => void;
  pause: () => void;
  stop: () => void;
  toggle: (url: string) => void;
  seek: (time: number) => void;
  setVolume: (volume: number) => void;
  setPlaybackRate: (rate: number) => void;
}

export function useAudioPlayer(): AudioPlayerState & AudioPlayerActions {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentUrl, setCurrentUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setIsPlaying(false);
    setCurrentTime(0);
  }, []);

  const play = useCallback((url: string) => {
    // If playing something else, stop it first
    if (audioRef.current && currentUrl !== url) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    if (!audioRef.current || currentUrl !== url) {
      setLoading(true);
      const audio = new Audio(url);
      audio.onended = () => { setIsPlaying(false); setCurrentTime(0); };
      audio.onerror = () => { setIsPlaying(false); setLoading(false); };
      audio.oncanplay = () => setLoading(false);
      audio.onloadedmetadata = () => setDuration(audio.duration);
      audio.ontimeupdate = () => setCurrentTime(audio.currentTime);
      audioRef.current = audio;
      setCurrentUrl(url);
    }

    audioRef.current.play();
    setIsPlaying(true);
  }, [currentUrl]);

  const pause = useCallback(() => {
    audioRef.current?.pause();
    setIsPlaying(false);
  }, []);

  const toggle = useCallback((url: string) => {
    if (isPlaying && currentUrl === url) {
      pause();
    } else {
      play(url);
    }
  }, [isPlaying, currentUrl, pause, play]);

  const seek = useCallback((time: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      setCurrentTime(time);
    }
  }, []);

  const setVolume = useCallback((volume: number) => {
    if (audioRef.current) {
      audioRef.current.volume = Math.max(0, Math.min(1, volume));
    }
  }, []);

  const setPlaybackRate = useCallback((rate: number) => {
    if (audioRef.current) {
      audioRef.current.playbackRate = rate;
    }
  }, []);

  return {
    isPlaying,
    currentUrl,
    loading,
    duration,
    currentTime,
    play,
    pause,
    stop,
    toggle,
    seek,
    setVolume,
    setPlaybackRate,
  };
}
