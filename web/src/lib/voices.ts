import type { Voice } from "../api/types";

const DEFAULT_BY_ENGINE: Record<string, string> = {
  piper: "es_MX-ald-medium",
  kokoro: "ef_dora",
  espeak: "es-419",
  edge: "es-MX-JorgeNeural",
  gemini: "Kore",
  elevenlabs: "pNInz6obpgDQGcFmaJgB",
  azure: "es-MX-JorgeNeural",
};

const LABELS: Record<string, { name: string; detail: string }> = {
  "es-MX-JorgeNeural": { name: "Jorge", detail: "Masculino · México" },
  "es-MX-DaliaNeural": { name: "Dalia", detail: "Femenino · México" },
  "es-PY-MarioNeural": { name: "Mario", detail: "Masculino · Paraguay" },
  "es-PY-TaniaNeural": { name: "Tania", detail: "Femenino · Paraguay" },
  "es_MX-ald-medium": { name: "Aldo", detail: "Masculino · México · Piper local" },
  ef_dora: { name: "Dora", detail: "Femenino · Kokoro local" },
  em_alex: { name: "Alex", detail: "Masculino · Kokoro local" },
  em_santa: { name: "Santa", detail: "Masculino · Kokoro local" },
  Kore: { name: "Kore", detail: "Femenino · Gemini" },
  Orus: { name: "Orus", detail: "Masculino · Gemini" },
  Puck: { name: "Puck", detail: "Masculino · Gemini" },
  Charon: { name: "Charon", detail: "Masculino · Gemini" },
  Aoede: { name: "Aoede", detail: "Femenino · Gemini" },
  Sulafat: { name: "Sulafat", detail: "Femenino · Gemini" },
  pNInz6obpgDQGcFmaJgB: { name: "Adam", detail: "Masculino · ElevenLabs" },
  ErXwobaYiN019PkySvjV: { name: "Antoni", detail: "Masculino · ElevenLabs" },
  VR6AewLTigWG4xSOukaG: { name: "Arnold", detail: "Masculino · ElevenLabs" },
  EXAVITQu4vr4xnSDxMaL: { name: "Bella", detail: "Femenino · ElevenLabs" },
};

export function voiceLabel(voice: Voice): { name: string; detail: string } {
  return LABELS[voice.id] ?? { name: voice.id, detail: `${voice.gender} · ${voice.locale}` };
}

export function defaultVoiceForEngine(engine: string, voices: Voice[]): string | undefined {
  const preferred = DEFAULT_BY_ENGINE[engine];
  const match = voices.find((voice) => voice.id === preferred && voice.engines.includes(engine));
  return match?.id ?? voices.find((voice) => voice.engines.includes(engine))?.id;
}
