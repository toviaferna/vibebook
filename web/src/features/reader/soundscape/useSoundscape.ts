import { useCallback, useEffect, useRef, useState } from "react";

import { apiUrl } from "../../../api/client";
import type {
  AmbienceChapter,
  AmbienceEffect,
  BookAmbience,
  ChapterTiming,
} from "../../../api/types";

interface SoundscapeOptions {
  chapterIndex: number;
  ambience: BookAmbience | undefined;
  timing: ChapterTiming | null;
  audioTimeMs: number;
  playing: boolean;
  rate: number;
  hasAudio: boolean;
  volume: number;
}

interface SoundscapeState {
  available: boolean;
  active: boolean;
  scene: string | null;
  error: string | null;
  toggle: () => void;
}

interface EffectCue {
  startMs: number;
  buffer: AudioBuffer;
  gainDb: number;
}

export function useSoundscape({
  chapterIndex,
  ambience,
  timing,
  audioTimeMs,
  playing,
  rate,
  hasAudio,
  volume,
}: SoundscapeOptions): SoundscapeState {
  const [active, setActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const engineRef = useRef<SoundscapeEngine | null>(null);
  const volumeRef = useRef(volume);
  const playingRef = useRef(playing);
  const timeRef = useRef(audioTimeMs);
  const rateRef = useRef(rate);
  const hasAudioRef = useRef(hasAudio);

  volumeRef.current = volume;
  playingRef.current = playing;
  timeRef.current = audioTimeMs;
  rateRef.current = rate;
  hasAudioRef.current = hasAudio;

  const chapter = ambience?.plan.chapters.find((item) => item.chapter_index === chapterIndex);
  const available = Boolean(chapter && (chapter.bed || chapter.effects.length > 0));

  useEffect(() => {
    if (!active || !ambience || !chapter || !available) {
      return;
    }
    let cancelled = false;
    const engine = new SoundscapeEngine();
    engineRef.current = engine;
    setError(null);
    void engine
      .load(chapter, timing, ambience.settings)
      .then(() => {
        if (cancelled) return;
        engine.setVolume(volumeRef.current);
        engine.start(
          hasAudioRef.current ? timeRef.current : 0,
          hasAudioRef.current ? playingRef.current : true,
          rateRef.current,
          hasAudioRef.current,
        );
      })
      .catch((reason: unknown) => {
        if (cancelled) return;
        setError(reason instanceof Error ? reason.message : "No se pudo iniciar el ambiente.");
        setActive(false);
      });
    return () => {
      cancelled = true;
      engine.dispose();
      if (engineRef.current === engine) {
        engineRef.current = null;
      }
    };
  }, [active, ambience, available, chapter, timing]);

  useEffect(() => {
    engineRef.current?.setVolume(volume);
  }, [volume]);

  useEffect(() => {
    const engine = engineRef.current;
    if (!engine) return;
    if (hasAudio) {
      engine.setPlaying(playing);
      engine.sync(audioTimeMs);
    } else {
      engine.setPlaying(true);
    }
  }, [audioTimeMs, hasAudio, playing]);

  const toggle = useCallback(() => {
    setError(null);
    setActive((current) => !current);
  }, []);

  return {
    available,
    active,
    scene: active ? (chapter?.bed?.reason ?? "Ambiente de lectura") : null,
    error,
    toggle,
  };
}

class SoundscapeEngine {
  private context: AudioContext | null = null;
  private master: GainNode | null = null;
  private bedSource: AudioBufferSourceNode | null = null;
  private bedBuffer: AudioBuffer | null = null;
  private cues: EffectCue[] = [];
  private timers: number[] = [];
  private settings = { master_gain_db: -18, ducking_db: -12 };
  private volume = 1;
  private playing = false;
  private hasAudio = false;
  private rate = 1;
  private lastTimeMs = 0;

  async load(
    chapter: AmbienceChapter,
    timing: ChapterTiming | null,
    settings: { master_gain_db: number; ducking_db: number },
  ): Promise<void> {
    if (typeof window === "undefined" || typeof AudioContext === "undefined") {
      throw new Error("Este navegador no soporta Web Audio.");
    }
    this.settings = settings;
    this.context = new AudioContext();
    this.master = this.context.createGain();
    this.master.connect(this.context.destination);
    const buffers = new Map<string, AudioBuffer>();
    if (chapter.bed) {
      this.bedBuffer = await this._loadBuffer(chapter.bed.asset_id, buffers);
    }
    this.cues = [];
    if (timing) {
      for (const effect of chapter.effects) {
        const startMs = effectStartMs(effect, timing);
        if (startMs === null) continue;
        const buffer = await this._loadBuffer(effect.asset_id, buffers);
        this.cues.push({ startMs, buffer, gainDb: effect.gain_db });
      }
    }
    this.cues.sort((a, b) => a.startMs - b.startMs);
  }

  start(fromMs: number, playing: boolean, rate: number, hasAudio: boolean): void {
    if (!this.context || !this.master) return;
    this.rate = Math.max(0.5, rate);
    this.hasAudio = hasAudio;
    this.playing = playing;
    this.lastTimeMs = fromMs;
    this.setVolume(this.volume);
    if (this.bedBuffer) {
      this.bedSource = this.context.createBufferSource();
      this.bedSource.buffer = this.bedBuffer;
      this.bedSource.loop = true;
      const bedGain = this.context.createGain();
      bedGain.gain.value = dbToGain(-24);
      this.bedSource.connect(bedGain);
      bedGain.connect(this.master);
      const offset = (fromMs / 1000) % this.bedBuffer.duration;
      this.bedSource.start(0, offset);
    }
    this.restartEffects(fromMs);
    this.setPlaying(playing);
  }

  setVolume(volume: number): void {
    this.volume = Math.max(0, Math.min(1, volume));
    this._applyMasterGain();
  }

  setPlaying(playing: boolean): void {
    this.playing = playing;
    if (!this.context) return;
    if (playing) {
      void this.context.resume();
    } else {
      void this.context.suspend();
    }
    this._applyMasterGain();
  }

  sync(timeMs: number): void {
    if (!this.hasAudio || !this.playing) {
      this.lastTimeMs = timeMs;
      return;
    }
    if (Math.abs(timeMs - this.lastTimeMs) > 2_000) {
      this.lastTimeMs = timeMs;
      this.restartEffects(timeMs);
    }
  }

  dispose(): void {
    this.clearTimers();
    this.bedSource?.stop();
    this.bedSource?.disconnect();
    this.bedSource = null;
    void this.context?.close();
    this.context = null;
    this.master = null;
  }

  private restartEffects(fromMs: number): void {
    this.clearTimers();
    if (!this.context || !this.master) return;
    if (!this.hasAudio) return;
    for (const cue of this.cues) {
      if (cue.startMs < fromMs) continue;
      const delay = cueDelayMs(cue.startMs, fromMs, this.rate);
      const timer = window.setTimeout(() => this._playCue(cue), delay);
      this.timers.push(timer);
    }
  }

  private _playCue(cue: EffectCue): void {
    if (!this.context || !this.master || !this.playing) return;
    const source = this.context.createBufferSource();
    source.buffer = cue.buffer;
    const gain = this.context.createGain();
    gain.gain.value = dbToGain(cue.gainDb);
    source.connect(gain);
    gain.connect(this.master);
    source.start();
  }

  private _applyMasterGain(): void {
    if (!this.master || !this.context) return;
    const duck = this.hasAudio && this.playing ? dbToGain(this.settings.ducking_db) : 1;
    const value = this.volume * dbToGain(this.settings.master_gain_db) * duck;
    this.master.gain.setTargetAtTime(value, this.context.currentTime, 0.03);
  }

  private async _loadBuffer(
    assetId: string,
    cache: Map<string, AudioBuffer>,
  ): Promise<AudioBuffer> {
    const existing = cache.get(assetId);
    if (existing) return existing;
    const response = await fetch(apiUrl(`/api/ambience/assets/${assetId}/audio`));
    if (!response.ok) {
      throw new Error("No se pudo cargar un sonido del ambiente.");
    }
    const bytes = await response.arrayBuffer();
    const buffer = await this.context?.decodeAudioData(bytes);
    if (!buffer) {
      throw new Error("No se pudo decodificar un sonido del ambiente.");
    }
    cache.set(assetId, buffer);
    return buffer;
  }

  private clearTimers(): void {
    for (const timer of this.timers) {
      window.clearTimeout(timer);
    }
    this.timers = [];
  }
}

export function effectStartMs(effect: AmbienceEffect, timing: ChapterTiming): number | null {
  const segment = timing.segments.find((item) => item.id === effect.anchor.segment_id);
  if (!segment) return null;
  return segment.start_ms + effect.anchor.offset_ms;
}

export function cueDelayMs(startMs: number, fromMs: number, rate: number): number {
  return Math.max(0, (startMs - fromMs) / Math.max(0.5, rate));
}

function dbToGain(db: number): number {
  return 10 ** (db / 20);
}
