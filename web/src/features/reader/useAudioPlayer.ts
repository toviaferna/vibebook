import { useCallback, useEffect, useRef, useState } from "react";

interface UseAudioPlayerOptions {
  initialRate?: number;
  onEnded?: () => void;
}

export function useAudioPlayer(
  audio: HTMLAudioElement | null,
  { initialRate = 1, onEnded }: UseAudioPlayerOptions = {},
) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTimeMs, setCurrentTimeMs] = useState(0);
  const [durationMs, setDurationMs] = useState(0);
  const [rate, setRateState] = useState(initialRate);
  const [volume, setVolumeState] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const endedRef = useRef(onEnded);
  const lastTimeRef = useRef(0);
  endedRef.current = onEnded;

  useEffect(() => {
    if (!audio) {
      return;
    }

    lastTimeRef.current = Number.isFinite(audio.currentTime) ? audio.currentTime * 1000 : 0;
    const syncTime = (force = false) => {
      if (!Number.isFinite(audio.currentTime)) {
        return;
      }
      const next = audio.currentTime * 1000;
      if (force || Math.abs(next - lastTimeRef.current) >= 10) {
        lastTimeRef.current = next;
        setCurrentTimeMs(next);
      }
    };
    const syncDuration = () => {
      setDurationMs(Number.isFinite(audio.duration) ? audio.duration * 1000 : 0);
      syncTime(true);
      setError(null);
    };
    let frame = 0;
    let lastUpdate = 0;
    const tick = (timestamp: number) => {
      if (audio.paused) {
        frame = 0;
        return;
      }
      if (timestamp - lastUpdate > 60) {
        syncTime();
        lastUpdate = timestamp;
      }
      frame = requestAnimationFrame(tick);
    };
    const startLoop = () => {
      if (frame === 0) {
        lastUpdate = 0;
        frame = requestAnimationFrame(tick);
      }
    };
    const stopLoop = () => {
      if (frame !== 0) {
        cancelAnimationFrame(frame);
        frame = 0;
      }
    };
    const onPlay = () => {
      setIsPlaying(true);
      startLoop();
    };
    const onPause = () => {
      setIsPlaying(false);
      stopLoop();
      syncTime(true);
    };
    const onEndedEvent = () => {
      setIsPlaying(false);
      stopLoop();
      syncTime(true);
      endedRef.current?.();
    };
    const onTimeUpdate = () => syncTime();
    const onSeeked = () => syncTime(true);
    const onRateChange = () => setRateState(audio.playbackRate);
    const onVolumeChange = () => setVolumeState(audio.volume);
    const onError = () => setError("No se pudo cargar el audio de este capítulo.");

    syncDuration();
    audio.addEventListener("loadedmetadata", syncDuration);
    audio.addEventListener("durationchange", syncDuration);
    audio.addEventListener("play", onPlay);
    audio.addEventListener("pause", onPause);
    audio.addEventListener("ended", onEndedEvent);
    audio.addEventListener("timeupdate", onTimeUpdate);
    audio.addEventListener("seeking", onSeeked);
    audio.addEventListener("seeked", onSeeked);
    audio.addEventListener("ratechange", onRateChange);
    audio.addEventListener("volumechange", onVolumeChange);
    audio.addEventListener("error", onError);
    if (!audio.paused) {
      startLoop();
    }

    return () => {
      stopLoop();
      audio.removeEventListener("loadedmetadata", syncDuration);
      audio.removeEventListener("durationchange", syncDuration);
      audio.removeEventListener("play", onPlay);
      audio.removeEventListener("pause", onPause);
      audio.removeEventListener("ended", onEndedEvent);
      audio.removeEventListener("timeupdate", onTimeUpdate);
      audio.removeEventListener("seeking", onSeeked);
      audio.removeEventListener("seeked", onSeeked);
      audio.removeEventListener("ratechange", onRateChange);
      audio.removeEventListener("volumechange", onVolumeChange);
      audio.removeEventListener("error", onError);
    };
  }, [audio]);

  useEffect(() => {
    if (audio) {
      audio.playbackRate = rate;
    }
  }, [audio, rate]);

  useEffect(() => {
    if (audio) {
      audio.volume = volume;
    }
  }, [audio, volume]);

  const play = useCallback(() => {
    if (!audio) {
      return;
    }
    void audio.play().catch(() => {
      // Autoplay may be blocked; the user can press play again.
    });
  }, [audio]);

  const pause = useCallback(() => {
    audio?.pause();
  }, [audio]);

  const toggle = useCallback(() => {
    if (!audio) {
      return;
    }
    if (audio.paused) {
      play();
    } else {
      pause();
    }
  }, [audio, pause, play]);

  const seekMs = useCallback(
    (value: number) => {
      if (!audio) {
        return;
      }
      const maximum = Number.isFinite(audio.duration) ? audio.duration * 1000 : value;
      const clamped = Math.max(0, Math.min(maximum, value));
      audio.currentTime = clamped / 1000;
      lastTimeRef.current = clamped;
      setCurrentTimeMs(clamped);
    },
    [audio],
  );

  const skip = useCallback(
    (seconds: number) => {
      if (!audio) {
        return;
      }
      seekMs(audio.currentTime * 1000 + seconds * 1000);
    },
    [audio, seekMs],
  );

  const setRate = useCallback((value: number) => {
    setRateState(value);
  }, []);

  const setVolume = useCallback((value: number) => {
    setVolumeState(Math.max(0, Math.min(1, value)));
  }, []);

  return {
    isPlaying,
    currentTimeMs,
    durationMs,
    rate,
    volume,
    error,
    play,
    pause,
    toggle,
    seekMs,
    skip,
    setRate,
    setVolume,
  };
}
