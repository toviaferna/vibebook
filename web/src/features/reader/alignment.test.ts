import type { ChapterTiming, ManifestSegment, TimingSegment } from "../../api/types";
import { alignSegment, findActive, findActiveWord, normalizeToken, tokenize } from "./alignment";

const segment: ManifestSegment = {
  id: "c001p0001s00",
  chapter_index: 1,
  paragraph_index: 1,
  chunk_index: 0,
  text: "Hola, mundo. ¿Qué tal?",
};

const timing: TimingSegment = {
  id: segment.id,
  start_ms: 0,
  end_ms: 2000,
  precision: "exact",
  words: [
    { text: "Hola,", start_ms: 0, end_ms: 500 },
    { text: "mundo.", start_ms: 500, end_ms: 1000 },
    { text: "¿Qué", start_ms: 1100, end_ms: 1500 },
    { text: "tal?", start_ms: 1500, end_ms: 2000 },
  ],
};

describe("alignment", () => {
  it("tokeniza conservando posiciones y puntuación", () => {
    expect(tokenize("Hola, mundo.")).toEqual([
      { text: "Hola,", start: 0, end: 5 },
      { text: "mundo.", start: 6, end: 12 },
    ]);
    expect(normalizeToken("¡Hola!")).toBe("hola");
  });

  it("alinea palabras con el texto original", () => {
    const aligned = alignSegment(segment, timing);

    expect(aligned.coverage).toBe(1);
    expect(aligned.words.map((word) => word.text)).toEqual(["Hola,", "mundo.", "¿Qué", "tal?"]);
    expect(aligned.words[0]).toMatchObject({ startMs: 0, endMs: 500 });
  });

  it("cae a segmento cuando la cobertura es baja", () => {
    const aligned = alignSegment(segment, {
      ...timing,
      words: [{ text: "otra", start_ms: 0, end_ms: 100 }],
    });

    expect(aligned.words).toEqual([]);
    expect(aligned.coverage).toBeLessThan(0.8);
  });

  it("rellena tokens sin timing entre vecinos", () => {
    const aligned = alignSegment(
      { ...segment, text: "Hola, mundo, otra vez, ahora." },
      {
        ...timing,
        words: [
          { text: "Hola,", start_ms: 0, end_ms: 400 },
          { text: "mundo,", start_ms: 400, end_ms: 800 },
          { text: "vez,", start_ms: 1200, end_ms: 1600 },
          { text: "ahora.", start_ms: 1600, end_ms: 2000 },
        ],
      },
    );

    expect(aligned.words).toHaveLength(5);
    expect(aligned.words[2].startMs).toBe(800);
    expect(aligned.words[2].endMs).toBe(1200);
  });

  it("no resalta palabras cuando el timing es estimado", () => {
    const aligned = alignSegment(segment, { ...timing, precision: "estimated" });
    expect(aligned.words).toEqual([]);
  });

  it("encuentra segmento y palabra activos", () => {
    const chapterTiming: ChapterTiming = {
      schema_version: 1,
      chapter_index: 1,
      duration_ms: 3000,
      precision: "exact",
      segments: [
        timing,
        {
          ...timing,
          id: "c001p0002s00",
          start_ms: 2000,
          end_ms: 3000,
          words: [{ text: "Adiós", start_ms: 2000, end_ms: 2500 }],
        },
      ],
    };

    expect(findActive(chapterTiming, 0)).toEqual({ segmentIndex: 0, wordIndex: 0 });
    expect(findActive(chapterTiming, 700)).toEqual({ segmentIndex: 0, wordIndex: 1 });
    expect(findActive(chapterTiming, 1050)).toEqual({ segmentIndex: 0, wordIndex: 1 });
    expect(findActive(chapterTiming, 2200)).toEqual({ segmentIndex: 1, wordIndex: 0 });
    expect(findActive(chapterTiming, 2900)).toEqual({ segmentIndex: 1, wordIndex: 0 });
    expect(findActive(chapterTiming, 3600)).toEqual({ segmentIndex: 1, wordIndex: null });
    expect(findActive(null, 100)).toEqual({ segmentIndex: -1, wordIndex: null });
    expect(findActive({ ...chapterTiming, precision: "estimated" }, 700)).toEqual({
      segmentIndex: 0,
      wordIndex: null,
    });
  });

  it("mantiene la palabra anterior durante huecos cortos y la quita en silencios largos", () => {
    const words = alignSegment(
      { ...segment, text: "Hola, mundo." },
      {
        ...timing,
        words: [
          { text: "Hola,", start_ms: 0, end_ms: 500 },
          { text: "mundo.", start_ms: 1_200, end_ms: 1_500 },
        ],
      },
    ).words;

    expect(findActiveWord(words, 600)).toBe(0);
    expect(findActiveWord(words, 1_100)).toBe(0);
    expect(findActiveWord(words, 1_600)).toBe(1);
    expect(findActiveWord(words, 2_700)).toBeNull();
  });

  it("no resalta una palabra antes de su primer inicio", () => {
    const words = alignSegment(
      { ...segment, text: "Hola," },
      {
        ...timing,
        words: [{ text: "Hola,", start_ms: 500, end_ms: 900 }],
      },
    ).words;

    expect(findActiveWord(words, 100)).toBeNull();
    expect(findActiveWord(words, 600)).toBe(0);
  });
});
