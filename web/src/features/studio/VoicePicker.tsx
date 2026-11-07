import { Play, Volume2 } from "lucide-react";

import type { Voice } from "../../api/types";
import { voiceLabel } from "../../lib/voices";

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
  return (
    <div className="voice-grid" role="radiogroup" aria-label="Voces disponibles">
      {voices.map((voice) => {
        const label = voiceLabel(voice);
        const available = engine === "fake" || voice.engines.includes(engine);
        const active = selected === voice.id;
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
    </div>
  );
}
