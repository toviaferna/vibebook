import type { ManifestChapter, ManifestImage, ManifestSegment } from "../../../api/types";
import {
  bookFlow,
  chapterParagraphs,
  chapterTextLength,
  pageIndexForOffset,
  paginateChapter,
  segmentRanges,
} from "./paginator";

function chapter(texts: string[]): ManifestChapter {
  const segments: ManifestSegment[] = texts.map((text, index) => ({
    id: `c001p${String(index + 1).padStart(4, "0")}s00`,
    chapter_index: 1,
    paragraph_index: index + 1,
    chunk_index: 0,
    text,
  }));
  return {
    index: 1,
    title: "La casa",
    duration_ms: null,
    audio: null,
    timing: null,
    segments,
  };
}

function measure(blocks: { text: string }[]): number {
  return blocks.reduce((total, block) => total + Math.ceil(block.text.length / 20) * 10, 0);
}

describe("paginator", () => {
  it("agrupa segmentos por pÃ¡rrafo y calcula offsets", () => {
    const source = chapter(["Hola", "mundo", "AdiÃ³s"]);
    source.segments[1] = { ...source.segments[1], paragraph_index: 1 };
    const paragraphs = chapterParagraphs(source);

    expect(paragraphs.map((paragraph) => paragraph.text)).toEqual(["Hola mundo", "AdiÃ³s"]);
    expect(paragraphs[0].startOffset).toBe(0);
    expect(paragraphs[1].startOffset).toBe("Hola mundo".length + 1);
    expect(chapterTextLength(chapter(["Hola mundo", "Adiós mundo"]))).toBe(
      "Hola mundo".length + 1 + "Adiós mundo".length,
    );
  });

  it("calcula rangos de segmento en el texto paginado", () => {
    const source = chapter(["Hola", "mundo", "Adios"]);
    source.segments[1] = { ...source.segments[1], paragraph_index: 1 };
    const ranges = segmentRanges(source);

    expect(ranges.get("c001p0001s00")).toEqual({ start: 0, end: 4 });
    expect(ranges.get("c001p0002s00")).toEqual({ start: 5, end: 10 });
    expect(ranges.get("c001p0003s00")).toEqual({ start: 11, end: 16 });
  });

  it("pagina sin perder texto y mantiene offsets", () => {
    const text = "uno dos tres cuatro cinco seis siete ocho nueve diez";
    const pages = paginateChapter(chapter([text]), [], measure, 20);

    expect(pages.length).toBeGreaterThan(1);
    expect(pages[0].startOffset).toBe(0);
    expect(pages.every((page) => page.blocks.length > 0)).toBe(true);
    expect(
      pages
        .flatMap((page) => page.blocks.map((block) => block.text))
        .join(" ")
        .replace(/\s+/g, " ")
        .trim(),
    ).toBe(text);
    expect(pages.map((page) => page.startOffset)).toEqual(
      [...pages.map((page) => page.startOffset)].sort((a, b) => a - b),
    );
  });

  it("rellena la página en curso partiendo el párrafo siguiente", () => {
    const first = Array.from({ length: 18 }, () => "uno").join(" ");
    const second = Array.from({ length: 20 }, () => "dos").join(" ");
    const pages = paginateChapter(chapter([first, second]), [], measure, 40);

    expect(measure(pages[0].blocks)).toBe(40);
    expect(measure(pages[1].blocks)).toBe(40);
    expect(
      pages
        .flatMap((page) => page.blocks.map((block) => block.text))
        .join(" ")
        .replace(/\s+/g, " ")
        .trim(),
    ).toBe(`${first} ${second}`);
  });

  it("intercala imágenes después del párrafo anclado", () => {
    const source = chapter(["Antes de la figura.", "Después de la figura."]);
    const image: ManifestImage = {
      id: "img-1",
      path: "images/1.png",
      alt: "Una casa",
      caption: "La casa",
      role: "illustration",
      chapter_index: 1,
      paragraph_index: 1,
      position: "after",
      width: 320,
      height: 200,
    };

    const flow = bookFlow(source, [image]);

    expect(flow.map((item) => item.kind)).toEqual(["text", "image", "text"]);
    const imageItem = flow[1];
    expect(imageItem.kind).toBe("image");
    if (imageItem.kind === "image") {
      expect(imageItem.image.id).toBe("img-1");
    }
  });

  it("encuentra la pÃ¡gina para un offset", () => {
    const pages = [
      { blocks: [], startOffset: 0 },
      { blocks: [], startOffset: 100 },
      { blocks: [], startOffset: 200 },
    ];

    expect(pageIndexForOffset(pages, 0)).toBe(0);
    expect(pageIndexForOffset(pages, 99)).toBe(0);
    expect(pageIndexForOffset(pages, 100)).toBe(1);
    expect(pageIndexForOffset(pages, 999)).toBe(2);
  });

  it("prefiere la primera página cuando dos comparten offset", () => {
    const pages = [
      { blocks: [], startOffset: 0 },
      { blocks: [], startOffset: 100 },
      { blocks: [], startOffset: 100 },
      { blocks: [], startOffset: 200 },
    ];

    expect(pageIndexForOffset(pages, 100)).toBe(1);
    expect(pageIndexForOffset(pages, 150)).toBe(2);
  });
});
