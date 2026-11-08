import type { Voice } from "../api/types";

const LABELS: Record<string, { name: string; detail: string }> = {
  "es-MX-JorgeNeural": { name: "Jorge", detail: "Masculino · México" },
  "es-MX-DaliaNeural": { name: "Dalia", detail: "Femenino · México" },
  "es-PY-MarioNeural": { name: "Mario", detail: "Masculino · Paraguay" },
  "es-PY-TaniaNeural": { name: "Tania", detail: "Femenino · Paraguay" },
  "es_MX-ald-medium": { name: "Aldo", detail: "Masculino · México · Piper local" },
};

export function voiceLabel(voice: Voice): { name: string; detail: string } {
  return LABELS[voice.id] ?? { name: voice.id, detail: `${voice.gender} · ${voice.locale}` };
}
