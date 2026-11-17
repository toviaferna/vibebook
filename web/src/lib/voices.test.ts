import type { Voice } from "../api/types";
import { voiceLanguageMismatch } from "./voices";

const english: Voice = {
  id: "pNInz6obpgDQGcFmaJgB",
  locale: "en-US",
  gender: "male",
  engines: ["elevenlabs"],
  styles: ["chat"],
};

const spanish: Voice = {
  id: "dlGxemPxFMTY7iXagmOj",
  locale: "es-419",
  gender: "male",
  engines: ["elevenlabs"],
  styles: ["chat"],
};

const multi: Voice = {
  ...english,
  locale: "multi",
};

describe("voiceLanguageMismatch", () => {
  it("detecta una voz inglesa para un libro español", () => {
    expect(voiceLanguageMismatch(english, "es")).toBe(true);
  });

  it("acepta una voz del mismo idioma", () => {
    expect(voiceLanguageMismatch(spanish, "es")).toBe(false);
    expect(voiceLanguageMismatch(english, "en-US")).toBe(false);
  });

  it("acepta voces multilingües y datos faltantes", () => {
    expect(voiceLanguageMismatch(multi, "es")).toBe(false);
    expect(voiceLanguageMismatch(undefined, "es")).toBe(false);
    expect(voiceLanguageMismatch(english, null)).toBe(false);
  });
});
