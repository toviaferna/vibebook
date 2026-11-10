import {
  BookOpenCheck,
  ChevronLeft,
  ChevronRight,
  Moon,
  Pause,
  Play,
  RotateCcw,
  RotateCw,
  Volume2,
  VolumeX,
} from "lucide-react";

import { formatTime } from "../../lib/format";

interface ReaderPlayerProps {
  chapterTitle: string;
  isPlaying: boolean;
  currentTimeMs: number;
  durationMs: number;
  rate: number;
  volume: number;
  skipSeconds: number;
  sleepMinutes: number;
  follow: boolean;
  audioError: string | null;
  onToggle: () => void;
  onSkip: (seconds: number) => void;
  onPrevious: () => void;
  onNext: () => void;
  onSeek: (ms: number) => void;
  onRate: (rate: number) => void;
  onVolume: (volume: number) => void;
  onSleep: (minutes: number) => void;
  onFollow: () => void;
}

export function ReaderPlayer({
  chapterTitle,
  isPlaying,
  currentTimeMs,
  durationMs,
  rate,
  volume,
  skipSeconds,
  sleepMinutes,
  follow,
  audioError,
  onToggle,
  onSkip,
  onPrevious,
  onNext,
  onSeek,
  onRate,
  onVolume,
  onSleep,
  onFollow,
}: ReaderPlayerProps) {
  return (
    <section className="reader-player" aria-label="Reproductor de audio">
      <div className="reader-player-main">
        <div className="reader-player-meta">
          <p className="eyebrow">Ahora</p>
          <strong>{chapterTitle || "Sin capítulo"}</strong>
        </div>
        <div className="reader-player-controls">
          <button
            type="button"
            className="icon-button"
            onClick={onPrevious}
            aria-label="Capítulo anterior"
            title="Capítulo anterior"
          >
            <ChevronLeft size={20} />
          </button>
          <button
            type="button"
            className="icon-button"
            onClick={() => onSkip(-skipSeconds)}
            aria-label={`Retroceder ${skipSeconds} segundos`}
            title={`Retroceder ${skipSeconds} s`}
          >
            <RotateCcw size={18} />
          </button>
          <button
            type="button"
            className="reader-play"
            onClick={onToggle}
            aria-label={isPlaying ? "Pausar" : "Reproducir"}
            title={isPlaying ? "Pausar" : "Reproducir"}
          >
            {isPlaying ? (
              <Pause size={22} fill="currentColor" />
            ) : (
              <Play size={22} fill="currentColor" />
            )}
          </button>
          <button
            type="button"
            className="icon-button"
            onClick={() => onSkip(skipSeconds)}
            aria-label={`Adelantar ${skipSeconds} segundos`}
            title={`Adelantar ${skipSeconds} s`}
          >
            <RotateCw size={18} />
          </button>
          <button
            type="button"
            className="icon-button"
            onClick={onNext}
            aria-label="Capítulo siguiente"
            title="Capítulo siguiente"
          >
            <ChevronRight size={20} />
          </button>
        </div>
        <div className="reader-player-tools">
          <label className="sr-only" htmlFor="reader-rate">
            Velocidad
          </label>
          <select
            id="reader-rate"
            className="reader-mini-select"
            value={rate}
            onChange={(event) => onRate(Number(event.target.value))}
            title="Velocidad"
          >
            {[0.75, 1, 1.25, 1.5, 2].map((value) => (
              <option value={value} key={value}>
                {value}×
              </option>
            ))}
          </select>
          <button
            type="button"
            className="icon-button"
            onClick={() => onVolume(volume > 0 ? 0 : 1)}
            aria-label={volume > 0 ? "Silenciar" : "Activar sonido"}
            title={volume > 0 ? "Silenciar" : "Activar sonido"}
          >
            {volume > 0 ? <Volume2 size={18} /> : <VolumeX size={18} />}
          </button>
          <label className="sr-only" htmlFor="reader-volume">
            Volumen
          </label>
          <input
            id="reader-volume"
            className="reader-volume"
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={volume}
            onChange={(event) => onVolume(Number(event.target.value))}
          />
          <label className="sr-only" htmlFor="reader-sleep">
            Temporizador
          </label>
          <span className="reader-timer">
            <Moon size={15} aria-hidden="true" />
            <select
              id="reader-sleep"
              className="reader-mini-select"
              value={sleepMinutes}
              onChange={(event) => onSleep(Number(event.target.value))}
              title="Temporizador"
            >
              <option value={0}>Sin temporizador</option>
              <option value={15}>15 min</option>
              <option value={30}>30 min</option>
              <option value={60}>60 min</option>
            </select>
          </span>
          <button
            type="button"
            className={`reader-follow${follow ? " is-active" : ""}`}
            onClick={onFollow}
            aria-pressed={follow}
            title="Seguir la lectura"
          >
            <BookOpenCheck size={16} />
            Seguir
          </button>
        </div>
      </div>

      {audioError ? (
        <p className="reader-audio-error" role="alert">
          {audioError}
        </p>
      ) : null}

      <div className="reader-progress">
        <span className="reader-time">{formatTime(currentTimeMs)}</span>
        <input
          className="reader-range"
          type="range"
          min={0}
          max={Math.max(durationMs, 1)}
          step={100}
          value={Math.min(currentTimeMs, durationMs || 0)}
          onChange={(event) => onSeek(Number(event.target.value))}
          aria-label="Posición del audio"
        />
        <span className="reader-time">{formatTime(durationMs)}</span>
      </div>
    </section>
  );
}
