import type { Voice } from "../api/types";

const DEFAULT_BY_ENGINE: Record<string, string> = {
  piper: "es_MX-ald-medium",
  espeak: "es-419",
  edge: "es-MX-JorgeNeural",
  azure: "es-MX-JorgeNeural",
};

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

export function defaultVoiceForEngine(engine: string, voices: Voice[]): string | undefined {
  const preferred = DEFAULT_BY_ENGINE[engine];
  const match = voices.find((voice) => voice.id === preferred && voice.engines.includes(engine));
  return match?.id ?? voices.find((voice) => voice.engines.includes(engine))?.id;
}
