import type { ManifestChapter } from "../../../api/types";

export interface PageBlock {
  text: string;
  paragraphIndex: number;
  startOffset: number;
  continuation: boolean;
}

export interface BookPage {
  blocks: PageBlock[];
  startOffset: number;
}

export type MeasurePage = (blocks: PageBlock[]) => number;

interface Paragraph {
  text: string;
  paragraphIndex: number;
  startOffset: number;
}

export function chapterParagraphs(chapter: ManifestChapter): Paragraph[] {
  const groups = new Map<number, string[]>();
  for (const segment of chapter.segments) {
    const group = groups.get(segment.paragraph_index) ?? [];
    group.push(segment.text);
    groups.set(segment.paragraph_index, group);
  }
  const paragraphs: Paragraph[] = [];
  let offset = 0;
  for (const [paragraphIndex, parts] of [...groups.entries()].sort(([a], [b]) => a - b)) {
    const text = parts.join(" ").replace(/\s+/g, " ").trim();
    if (!text) {
      continue;
    }
    paragraphs.push({ text, paragraphIndex, startOffset: offset });
    offset += text.length + 1;
  }
  return paragraphs;
}

export function paginateChapter(
  chapter: ManifestChapter,
  measure: MeasurePage,
  pageHeight: number,
): BookPage[] {
  const paragraphs = chapterParagraphs(chapter);
  const pages: BookPage[] = [];
  let current: PageBlock[] = [];

  const flush = () => {
    if (current.length === 0) {
      return;
    }
    pages.push({ blocks: current, startOffset: current[0]?.startOffset ?? 0 });
    current = [];
  };

  for (const paragraph of paragraphs) {
    let block: PageBlock = {
      text: paragraph.text,
      paragraphIndex: paragraph.paragraphIndex,
      startOffset: paragraph.startOffset,
      continuation: false,
    };
    while (block.text) {
      const candidate = [...current, block];
      if (measure(candidate) <= pageHeight) {
        current = candidate;
        block = { ...block, text: "" };
        break;
      }
      if (current.length > 0) {
        flush();
        continue;
      }
      const split = splitBlock(block, measure, pageHeight);
      current.push(split.fitted);
      flush();
      block = split.rest;
    }
  }
  flush();
  if (pages.length === 0) {
    pages.push({ blocks: [], startOffset: 0 });
  }
  return pages;
}

function splitBlock(
  block: PageBlock,
  measure: MeasurePage,
  pageHeight: number,
): { fitted: PageBlock; rest: PageBlock } {
  const words = block.text.split(/\s+/).filter(Boolean);
  let low = 1;
  let high = words.length;
  let best = 0;
  while (low <= high) {
    const middle = Math.floor((low + high) / 2);
    const text = words.slice(0, middle).join(" ");
    if (measure([{ ...block, text }]) <= pageHeight) {
      best = middle;
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  const fittedWords = Math.max(1, best);
  const fittedText = words.slice(0, fittedWords).join(" ");
  const restText = words.slice(fittedWords).join(" ");
  return {
    fitted: { ...block, text: fittedText },
    rest: {
      ...block,
      text: restText,
      startOffset: block.startOffset + fittedText.length + (restText ? 1 : 0),
      continuation: true,
    },
  };
}

export function pageIndexForOffset(pages: BookPage[], offset: number): number {
  if (pages.length === 0) {
    return 0;
  }
  let low = 0;
  let high = pages.length - 1;
  let found = 0;
  while (low <= high) {
    const middle = Math.floor((low + high) / 2);
    if (pages[middle].startOffset <= offset) {
      found = middle;
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  return found;
}
