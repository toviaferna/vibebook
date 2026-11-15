import type { ManifestChapter, ManifestSegment, TimingSegment } from "../../../api/types";
import { alignSegment } from "../alignment";
import { blockWords, buildChapterHighlight, wordsText } from "./highlight";
import { chapterParagraphs } from "./paginator";

function segment(
  id: string,
  paragraphIndex: number,
  text: string,
  chunkIndex = 0,
): ManifestSegment {
  return {
    id,
    chapter_index: 1,
    paragraph_index: paragraphIndex,
    chunk_index: chunkIndex,
    text,
  };
}

function chapter(segments: ManifestSegment[]): ManifestChapter {
  return {
    index: 1,
    title: "La casa",
    duration_ms: null,
    audio: null,
    timing: null,
    segments,
  };
}

function timing(id: string, words: string[]): TimingSegment {
  let start = 0;
  return {
    id,
    start_ms: 0,
    end_ms: words.length * 300,
    precision: "exact",
    words: words.map((text) => {
      const word = {
        text,
        start_ms: start,
        end_ms: start + 280,
      };
      start += 300;
      return word;
    }),
  };
}

describe("book highlight", () => {
  it("mapea cada palabra a su segmento y conserva el texto del paginador", () => {
    const first = segment("c001p0001s00", 1, "Hola mundo,");
    const second = segment("c001p0001s01", 1, "adiós.", 1);
    const alignments = new Map([
      [first.id, alignSegment(first, timing(first.id, ["Hola", "mundo,"]))],
      [second.id, alignSegment(second, timing(second.id, ["adiós."]))],
    ]);

    const highlight = buildChapterHighlight(chapter([first, second]), alignments);
    const paragraph = highlight.paragraphs.get(1);

    expect(paragraph?.text).toBe("Hola mundo, adiós.");
    expect(paragraph?.text).toBe(chapterParagraphs(chapter([first, second]))[0].text);
    expect(paragraph?.words.map((word) => word.text)).toEqual(["Hola", "mundo,", "adiós."]);
    expect(paragraph?.words.map((word) => word.segmentId)).toEqual([first.id, first.id, second.id]);
    expect(paragraph?.words.map((word) => word.wordIndex)).toEqual([0, 1, 0]);
    expect(highlight.segmentOffsets.get(second.id)).toBe("Hola mundo, ".length);
    expect(highlight.segmentRanges.get(second.id)).toEqual({
      start: "Hola mundo, ".length,
      end: "Hola mundo, adiós.".length,
    });
    expect(highlight.segmentWordOffsets.get(first.id)).toEqual([0, "Hola ".length]);
    expect(highlight.segmentWordOffsets.get(second.id)).toEqual(["Hola mundo, ".length]);
  });

  it("separa un bloque partido sin perder palabras", () => {
    const first = segment("c001p0001s00", 1, "Hola mundo,");
    const second = segment("c001p0001s01", 1, "adiós.", 1);
    const highlight = buildChapterHighlight(chapter([first, second]), new Map());
    const paragraph = highlight.paragraphs.get(1);
    if (!paragraph) {
      throw new Error("missing paragraph");
    }

    const tail = {
      kind: "text" as const,
      text: "mundo, adiós.",
      paragraphIndex: 1,
      startOffset: "Hola ".length,
      continuation: true,
    };
    const words = blockWords(tail, paragraph);

    expect(wordsText(words)).toBe(tail.text);
    expect(words.map((word) => word.segmentId)).toEqual([first.id, second.id]);
    expect(words.map((word) => word.wordIndex)).toEqual([null, null]);
  });

  it("recorta un bloque en un párrafo que no empieza en cero", () => {
    const first = segment("c001p0001s00", 1, "Hola mundo");
    const second = segment("c001p0002s00", 2, "Adiós mundo");
    const highlight = buildChapterHighlight(chapter([first, second]), new Map());
    const paragraph = highlight.paragraphs.get(2);
    if (!paragraph) {
      throw new Error("missing paragraph");
    }

    const tail = {
      kind: "text" as const,
      text: "mundo",
      paragraphIndex: 2,
      startOffset: paragraph.startOffset + "Adiós ".length,
      continuation: true,
    };

    expect(wordsText(blockWords(tail, paragraph))).toBe("mundo");
    expect(blockWords(tail, paragraph).map((word) => word.text)).toEqual(["mundo"]);
  });

  it("usa el índice alineado aunque el segmento no tenga timing exacto", () => {
    const only = segment("c001p0001s00", 1, "Hola mundo");
    const highlight = buildChapterHighlight(chapter([only]), new Map());
    const paragraph = highlight.paragraphs.get(1);

    expect(paragraph?.words.every((word) => word.wordIndex === null)).toBe(true);
  });

  it("mantiene los offsets de párrafos alineados con el paginador", () => {
    const first = segment("c001p0001s00", 1, "Hola mundo");
    const second = segment("c001p0002s00", 2, "Adiós mundo");
    const source = chapter([first, second]);
    const highlight = buildChapterHighlight(source, new Map());
    const paginated = chapterParagraphs(source);
    const secondParagraph = highlight.paragraphs.get(2);

    expect(secondParagraph?.startOffset).toBe(paginated[1].startOffset);
    expect(secondParagraph?.words[0].start).toBe(paginated[1].startOffset);
    expect(highlight.segmentOffsets.get(second.id)).toBe(paginated[1].startOffset);
  });
});
