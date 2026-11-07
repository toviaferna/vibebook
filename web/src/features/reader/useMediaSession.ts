import { useEffect } from "react";

interface MediaSessionOptions {
  title: string;
  artist: string;
  album: string;
  artwork?: string;
  isPlaying: boolean;
  rate: number;
  currentTimeMs: number;
  durationMs: number;
  onPlay: () => void;
  onPause: () => void;
  onSeekBackward: () => void;
  onSeekForward: () => void;
  onPrevious: () => void;
  onNext: () => void;
}

export function useMediaSession(options: MediaSessionOptions) {
  const {
    title,
    artist,
    album,
    artwork,
    isPlaying,
    rate,
    currentTimeMs,
    durationMs,
    onPlay,
    onPause,
    onSeekBackward,
    onSeekForward,
    onPrevious,
    onNext,
  } = options;

  useEffect(() => {
    if (!("mediaSession" in navigator) || !("MediaMetadata" in window)) {
      return;
    }
    navigator.mediaSession.metadata = new MediaMetadata({
      title,
      artist,
      album,
      artwork: artwork ? [{ src: artwork }] : undefined,
    });

    const handlers: Array<[MediaSessionAction, MediaSessionActionHandler]> = [
      ["play", onPlay],
      ["pause", onPause],
      ["seekbackward", onSeekBackward],
      ["seekforward", onSeekForward],
      ["previoustrack", onPrevious],
      ["nexttrack", onNext],
    ];
    for (const [action, handler] of handlers) {
      navigator.mediaSession.setActionHandler(action, handler);
    }

    return () => {
      for (const [action] of handlers) {
        navigator.mediaSession.setActionHandler(action, null);
      }
    };
  }, [
    album,
    artist,
    artwork,
    onNext,
    onPause,
    onPlay,
    onPrevious,
    onSeekBackward,
    onSeekForward,
    title,
  ]);

  useEffect(() => {
    if (!("mediaSession" in navigator) || durationMs <= 0) {
      return;
    }
    try {
      navigator.mediaSession.playbackState = isPlaying ? "playing" : "paused";
      navigator.mediaSession.setPositionState({
        duration: durationMs / 1000,
        playbackRate: rate,
        position: Math.min(currentTimeMs / 1000, durationMs / 1000),
      });
    } catch {
      // Some browsers reject position state during seek; the next update retries.
    }
  }, [currentTimeMs, durationMs, isPlaying, rate]);
}
