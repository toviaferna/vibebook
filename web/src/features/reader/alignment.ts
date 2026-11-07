import type { ChapterTiming, ManifestSegment, TimingSegment, WordTiming } from "../../api/types";

export interface TextToken {
  text: string;
  start: number;
  end: number;
}

export interface AlignedWord extends TextToken {
  startMs: number;
  endMs: number;
}

export interface AlignedSegment {
  segment: ManifestSegment;
  tokens: TextToken[];
  words: AlignedWord[];
  coverage: number;
}

const TOKEN_PATTERN = /\S+/g;
const TRIM_PUNCTUATION = /^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu;

export function tokenize(text: string): TextToken[] {
  return [...text.matchAll(TOKEN_PATTERN)].map((match) => ({
    text: match[0],
    start: match.index ?? 0,
    end: (match.index ?? 0) + match[0].length,
  }));
}

export function normalizeToken(text: string): string {
  return text.toLocaleLowerCase("es").replace(TRIM_PUNCTUATION, "");
}

function matchIndex(
  tokens: TextToken[],
  words: WordTiming[],
  tokenIndex: number,
  wordIndex: number,
): number {
  const normalized = normalizeToken(tokens[tokenIndex].text);
  if (!normalized) {
    return -1;
  }
  const limit = Math.min(words.length, wordIndex + 4);
  for (let index = wordIndex; index < limit; index += 1) {
    if (normalizeToken(words[index].text) === normalized) {
      return index;
    }
  }
  return -1;
}

export function alignSegment(
  segment: ManifestSegment,
  timing: TimingSegment | undefined,
): AlignedSegment {
  const tokens = tokenize(segment.text);
  if (!timing || timing.words.length === 0 || tokens.length === 0) {
    return { segment, tokens, words: [], coverage: 0 };
  }

  const words = timing.words.filter((word) => word.text.trim().length > 0);
  if (timing.precision !== "exact") {
    return { segment, tokens, words: [], coverage: 0 };
  }
  const pairs = new Map<number, WordTiming>();
  let wordIndex = 0;
  for (let tokenIndex = 0; tokenIndex < tokens.length; tokenIndex += 1) {
    const found = matchIndex(tokens, words, tokenIndex, wordIndex);
    if (found >= 0) {
      pairs.set(tokenIndex, words[found]);
      wordIndex = found + 1;
    }
  }

  const coverage = pairs.size / tokens.length;
  if (coverage < 0.8) {
    return { segment, tokens, words: [], coverage };
  }

  const aligned: AlignedWord[] = tokens.map((token, index) => {
    const paired = pairs.get(index);
    if (paired) {
      return {
        ...token,
        startMs: clamp(paired.start_ms, timing.start_ms, timing.end_ms),
        endMs: clamp(paired.end_ms, timing.start_ms, timing.end_ms),
      };
    }
    let previous = timing.start_ms;
    for (let cursor = index - 1; cursor >= 0; cursor -= 1) {
      const word = alignedWordAt(pairs, tokens, cursor, timing);
      if (word) {
        previous = word.endMs;
        break;
      }
    }
    let next = timing.end_ms;
    for (let cursor = index + 1; cursor < tokens.length; cursor += 1) {
      const word = alignedWordAt(pairs, tokens, cursor, timing);
      if (word) {
        next = word.startMs;
        break;
      }
    }
    return {
      ...token,
      startMs: previous,
      endMs: Math.max(previous + 1, next),
    };
  });

  for (let index = 1; index < aligned.length; index += 1) {
    aligned[index].startMs = Math.max(aligned[index].startMs, aligned[index - 1].endMs);
    aligned[index].endMs = Math.max(aligned[index].startMs + 1, aligned[index].endMs);
  }

  return { segment, tokens, words: aligned, coverage };
}

function alignedWordAt(
  pairs: Map<number, WordTiming>,
  tokens: TextToken[],
  index: number,
  timing: TimingSegment,
): AlignedWord | null {
  const paired = pairs.get(index);
  if (!paired) {
    return null;
  }
  return {
    ...tokens[index],
    startMs: clamp(paired.start_ms, timing.start_ms, timing.end_ms),
    endMs: clamp(paired.end_ms, timing.start_ms, timing.end_ms),
  };
}

export interface ActiveTiming {
  segmentIndex: number;
  wordIndex: number | null;
}

export function findActive(timing: ChapterTiming | null, timeMs: number): ActiveTiming {
  if (!timing || timing.segments.length === 0 || timeMs < 0) {
    return { segmentIndex: -1, wordIndex: null };
  }
  let low = 0;
  let high = timing.segments.length - 1;
  let found = -1;
  while (low <= high) {
    const middle = Math.floor((low + high) / 2);
    if (timing.segments[middle].start_ms <= timeMs) {
      found = middle;
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  if (found < 0) {
    return { segmentIndex: -1, wordIndex: null };
  }
  const segment = timing.segments[found];
  if (timeMs >= segment.end_ms) {
    return { segmentIndex: found, wordIndex: null };
  }
  if (timing.precision !== "exact" || segment.precision !== "exact" || segment.words.length === 0) {
    return { segmentIndex: found, wordIndex: null };
  }
  let wordLow = 0;
  let wordHigh = segment.words.length - 1;
  let wordFound = -1;
  while (wordLow <= wordHigh) {
    const middle = Math.floor((wordLow + wordHigh) / 2);
    if (segment.words[middle].start_ms <= timeMs) {
      wordFound = middle;
      wordLow = middle + 1;
    } else {
      wordHigh = middle - 1;
    }
  }
  if (wordFound < 0) {
    return { segmentIndex: found, wordIndex: null };
  }
  const word = segment.words[wordFound];
  if (timeMs >= word.end_ms) {
    return { segmentIndex: found, wordIndex: null };
  }
  return { segmentIndex: found, wordIndex: wordFound };
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}
