import type { ManifestChapter, ManifestSegment } from "../../../api/types";
import { type AlignedSegment, tokenize } from "../alignment";
import type { TextBlock } from "./paginator";

export interface HighlightWord {
  text: string;
  segmentId: string;
  wordIndex: number | null;
  start: number;
  end: number;
}

export interface ParagraphHighlight {
  text: string;
  startOffset: number;
  words: HighlightWord[];
}

export interface ChapterHighlight {
  paragraphs: Map<number, ParagraphHighlight>;
  segmentOffsets: Map<string, number>;
}

/**
 * Rebuilds each paragraph exactly like the paginator does, but keeps a link
 * from every word back to its segment and aligned-word index. The paginator
 * splits paragraphs at word boundaries, so a page block can be sliced from
 * these words without changing the text.
 */
export function buildChapterHighlight(
  chapter: ManifestChapter,
  alignments: Map<string, AlignedSegment>,
): ChapterHighlight {
  const groups = new Map<number, ManifestSegment[]>();
  for (const segment of chapter.segments) {
    const group = groups.get(segment.paragraph_index) ?? [];
    group.push(segment);
    groups.set(segment.paragraph_index, group);
  }

  const paragraphs = new Map<number, ParagraphHighlight>();
  const segmentOffsets = new Map<string, number>();
  let offset = 0;

  for (const [paragraphIndex, segments] of [...groups.entries()].sort(([a], [b]) => a - b)) {
    const words: HighlightWord[] = [];
    for (const segment of segments) {
      const aligned = alignments.get(segment.id);
      const tokens = aligned?.words.length ? aligned.words : tokenize(segment.text);
      for (let index = 0; index < tokens.length; index += 1) {
        const token = tokens[index];
        if (!segmentOffsets.has(segment.id)) {
          segmentOffsets.set(segment.id, offset);
        }
        words.push({
          text: token.text,
          segmentId: segment.id,
          wordIndex: aligned?.words.length ? index : null,
          start: offset,
          end: offset + token.text.length,
        });
        offset += token.text.length + 1;
      }
    }

    if (words.length === 0) {
      continue;
    }
    offset -= 1;
    const text = words.map((word) => word.text).join(" ");
    paragraphs.set(paragraphIndex, { text, startOffset: offset - text.length, words });
    offset += 1;
  }

  return { paragraphs, segmentOffsets };
}

export function blockWords(block: TextBlock, paragraph: ParagraphHighlight): HighlightWord[] {
  const start = block.startOffset - paragraph.startOffset;
  const end = start + block.text.length;
  return paragraph.words.filter((word) => word.end > start && word.start < end);
}

export function wordsText(words: HighlightWord[]): string {
  return words.map((word) => word.text).join(" ");
}
