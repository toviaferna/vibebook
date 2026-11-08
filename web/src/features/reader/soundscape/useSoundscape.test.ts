import { describe, expect, it } from "vitest";

import type { AmbienceEffect, ChapterTiming } from "../../../api/types";
import { cueDelayMs, effectStartMs } from "./useSoundscape";

const timing: ChapterTiming = {
  schema_version: 1,
  chapter_index: 1,
  duration_ms: 20_000,
  precision: "estimated",
  segments: [
    { id: "s1", start_ms: 4_000, end_ms: 5_000, precision: "estimated", words: [] },
    { id: "s2", start_ms: 12_000, end_ms: 13_000, precision: "estimated", words: [] },
  ],
};

function effect(segmentId: string, offsetMs = 0): AmbienceEffect {
  return {
    asset_id: "bell",
    kind: "effect",
    anchor: { segment_id: segmentId, offset_ms: offsetMs },
    duration_ms: 1_800,
    gain_db: -16,
    confidence: 0.7,
    reason: "",
  };
}

describe("ambience scheduler", () => {
  it("calcula el inicio absoluto de un efecto", () => {
    expect(effectStartMs(effect("s1", 1_200), timing)).toBe(5_200);
    expect(effectStartMs(effect("s2"), timing)).toBe(12_000);
  });

  it("devuelve null si el anchor no existe", () => {
    expect(effectStartMs(effect("missing"), timing)).toBeNull();
  });

  it("calcula el delay con la velocidad de reproducción", () => {
    expect(cueDelayMs(10_000, 4_000, 1)).toBe(6_000);
    expect(cueDelayMs(10_000, 4_000, 2)).toBe(3_000);
    expect(cueDelayMs(2_000, 4_000, 1)).toBe(0);
  });

  it("no divide por una velocidad menor a 0.5", () => {
    expect(cueDelayMs(10_000, 4_000, 0.25)).toBe(12_000);
  });
});
