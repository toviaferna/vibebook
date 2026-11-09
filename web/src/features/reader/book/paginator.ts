import type { ManifestChapter, ManifestImage } from "../../../api/types";

export interface TextBlock {
  kind: "text";
  text: string;
  paragraphIndex: number;
  startOffset: number;
  continuation: boolean;
}

export interface ImageBlock {
  kind: "image";
  image: ManifestImage;
  text: "";
  paragraphIndex: number;
  startOffset: number;
  continuation: false;
}

export type PageBlock = TextBlock | ImageBlock;
export type BookItem = TextBlock | ImageBlock;

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

export function bookFlow(chapter: ManifestChapter, images: ManifestImage[]): BookItem[] {
  const paragraphs = chapterParagraphs(chapter);
  const byParagraph = new Map<number, ManifestImage[]>();
  for (const image of images) {
    if (image.chapter_index !== chapter.index) {
      continue;
    }
    const group = byParagraph.get(image.paragraph_index) ?? [];
    group.push(image);
    byParagraph.set(image.paragraph_index, group);
  }

  const flow: BookItem[] = [];
  const used = new Set<string>();
  const pushImage = (image: ManifestImage, offset: number) => {
    if (used.has(image.id)) {
      return;
    }
    used.add(image.id);
    flow.push({
      kind: "image",
      image,
      text: "",
      paragraphIndex: image.paragraph_index,
      startOffset: offset,
      continuation: false,
    });
  };

  let offset = 0;
  for (const image of byParagraph.get(0) ?? []) {
    pushImage(image, offset);
  }
  for (const paragraph of paragraphs) {
    for (const image of byParagraph.get(paragraph.paragraphIndex) ?? []) {
      if (image.position === "before") {
        pushImage(image, paragraph.startOffset);
      }
    }
    flow.push({
      kind: "text",
      text: paragraph.text,
      paragraphIndex: paragraph.paragraphIndex,
      startOffset: paragraph.startOffset,
      continuation: false,
    });
    offset = paragraph.startOffset + paragraph.text.length + 1;
    for (const image of byParagraph.get(paragraph.paragraphIndex) ?? []) {
      if (image.position !== "before") {
        pushImage(image, offset);
      }
    }
  }
  for (const image of images) {
    if (image.chapter_index === chapter.index) {
      pushImage(image, offset);
    }
  }
  return flow;
}

export function paginateChapter(
  chapter: ManifestChapter,
  images: ManifestImage[],
  measure: MeasurePage,
  pageHeight: number,
): BookPage[] {
  const flow = bookFlow(chapter, images);
  const pages: BookPage[] = [];
  let current: PageBlock[] = [];

  const flush = () => {
    if (current.length === 0) {
      return;
    }
    pages.push({ blocks: current, startOffset: current[0]?.startOffset ?? 0 });
    current = [];
  };

  for (const item of flow) {
    if (item.kind === "image") {
      if (measure([...current, item]) <= pageHeight) {
        current.push(item);
        continue;
      }
      flush();
      current.push(item);
      if (measure(current) > pageHeight) {
        flush();
      }
      continue;
    }

    let block: TextBlock = { ...item };
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
  block: TextBlock,
  measure: MeasurePage,
  pageHeight: number,
): { fitted: TextBlock; rest: TextBlock } {
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
  let high = pages.length;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (pages[middle].startOffset < offset) {
      low = middle + 1;
    } else {
      high = middle;
    }
  }
  if (low < pages.length && pages[low].startOffset === offset) {
    return low;
  }
  return Math.max(0, low - 1);
}
