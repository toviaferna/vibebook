import { Play, Star, Volume2 } from "lucide-react";
import { useMemo, useState } from "react";

import type { Voice } from "../../api/types";
import { voiceLabel } from "../../lib/voices";

const FAVORITES_KEY = "vibebook.voice-favorites";

function readFavorites(): Set<string> {
  try {
    const raw = window.localStorage.getItem(FAVORITES_KEY);
    const parsed = raw ? (JSON.parse(raw) as unknown) : [];
    return new Set(Array.isArray(parsed) ? parsed.filter((item) => typeof item === "string") : []);
  } catch {
    return new Set();
  }
}

interface VoicePickerProps {
  voices: Voice[];
  selected: string;
  engine: string;
  previewing: string | null;
  onSelect: (voiceId: string) => void;
  onPreview: (voiceId: string) => void;
}

export function VoicePicker({
  voices,
  selected,
  engine,
  previewing,
  onSelect,
  onPreview,
}: VoicePickerProps) {
  const [favorites, setFavorites] = useState<Set<string>>(readFavorites);
  const [favoritesOnly, setFavoritesOnly] = useState(false);

  const ordered = useMemo(() => {
    const visible = voices.filter((voice) => !favoritesOnly || favorites.has(voice.id));
    return [...visible].sort((left, right) => {
      const leftFavorite = favorites.has(left.id) ? 0 : 1;
      const rightFavorite = favorites.has(right.id) ? 0 : 1;
      return leftFavorite - rightFavorite || left.id.localeCompare(right.id);
    });
  }, [favorites, favoritesOnly, voices]);

  const toggleFavorite = (voiceId: string) => {
    setFavorites((current) => {
      const next = new Set(current);
      if (next.has(voiceId)) {
        next.delete(voiceId);
      } else {
        next.add(voiceId);
      }
      window.localStorage.setItem(FAVORITES_KEY, JSON.stringify([...next]));
      return next;
    });
  };

  return (
    <fieldset className="voice-grid" aria-label="Voces disponibles">
      <legend className="sr-only">Voces disponibles</legend>
      <div className="voice-toolbar">
        <span className="hint">{favorites.size} favoritas</span>
        <button
          type="button"
          className="link-button"
          aria-pressed={favoritesOnly}
          onClick={() => setFavoritesOnly((current) => !current)}
        >
          <Star size={14} fill={favoritesOnly ? "currentColor" : "none"} aria-hidden="true" />
          Solo favoritas
        </button>
      </div>
      {ordered.map((voice) => {
        const label = voiceLabel(voice);
        const available = engine === "fake" || voice.engines.includes(engine);
        const active = selected === voice.id;
        const favorite = favorites.has(voice.id);
        return (
          <div
            className={`voice-card${active ? " is-selected" : ""}`}
            key={voice.id}
            aria-disabled={!available || undefined}
          >
            <button
              type="button"
              className="link-button"
              onClick={() => onSelect(voice.id)}
              disabled={!available}
              style={{ textAlign: "left" }}
              aria-pressed={active}
            >
              <strong style={{ display: "block" }}>{label.name}</strong>
              <span>{label.detail}</span>
            </button>
            <div className="voice-actions">
              <span className="hint">{available ? "Disponible" : "No disponible"}</span>
              <button
                type="button"
                className={`icon-button voice-favorite${favorite ? " is-active" : ""}`}
                onClick={() => toggleFavorite(voice.id)}
                aria-pressed={favorite}
                aria-label={
                  favorite
                    ? `Quitar ${label.name} de favoritas`
                    : `Marcar ${label.name} como favorita`
                }
                title={favorite ? "Quitar de favoritas" : "Marcar como favorita"}
              >
                <Star size={15} fill={favorite ? "currentColor" : "none"} aria-hidden="true" />
              </button>
              <button
                type="button"
                className="icon-button"
                onClick={() => onPreview(voice.id)}
                disabled={!available || previewing === voice.id}
                aria-label={`Escuchar muestra de ${label.name}`}
                title={`Escuchar muestra de ${label.name}`}
              >
                {previewing === voice.id ? (
                  <Volume2 size={16} className="pulse" />
                ) : (
                  <Play size={16} />
                )}
              </button>
            </div>
          </div>
        );
      })}
      {ordered.length === 0 ? (
        <p className="hint voice-empty">
          Todavía no marcaste voces favoritas. Usá la estrella de una voz para guardarla acá.
        </p>
      ) : null}
    </fieldset>
  );
}
