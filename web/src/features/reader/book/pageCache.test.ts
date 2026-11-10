import type { ManifestChapter, ManifestImage } from "../../../api/types";
import {
  chapterSignature,
  clearPageCache,
  getCachedPages,
  pageCacheKey,
  setCachedPages,
} from "./pageCache";
import { type BookPage, paginateChapter } from "./paginator";

function chapter(texts: string[]): ManifestChapter {
  return {
    index: 1,
    title: "La casa",
    duration_ms: null,
    audio: null,
    timing: null,
    segments: texts.map((text, index) => ({
      id: `c001p${String(index + 1).padStart(4, "0")}s00`,
      chapter_index: 1,
      paragraph_index: index + 1,
      chunk_index: 0,
      text,
    })),
  };
}

function measure(blocks: { text: string }[]): number {
  return blocks.reduce((total, block) => total + Math.ceil(block.text.length / 20) * 10, 0);
}

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

describe("pageCache", () => {
  beforeEach(() => clearPageCache());

  it("no comparte páginas entre libros con el mismo índice de capítulo", () => {
    const first = chapter(["Texto del libro uno."]);
    const second = chapter(["Texto completamente distinto."]);
    const keyA = pageCacheKey({
      bookId: "a",
      chapter: first,
      width: 600,
      height: 200,
      font: "serif",
      size: 19,
      album: false,
    });
    const keyB = pageCacheKey({
      bookId: "b",
      chapter: second,
      width: 600,
      height: 200,
      font: "serif",
      size: 19,
      album: false,
    });

    expect(keyA).not.toBe(keyB);
    expect(chapterSignature(first)).not.toBe(chapterSignature(second));
  });

  it("invalida la clave cuando cambia el texto o la imagen", () => {
    const first = chapter(["Texto uno."]);
    const second = chapter(["Texto dos."]);
    const base = {
      bookId: "a",
      width: 600,
      height: 200,
      font: "serif",
      size: 19,
      album: false,
    };

    expect(pageCacheKey({ ...base, chapter: first })).not.toBe(
      pageCacheKey({ ...base, chapter: second }),
    );
    expect(pageCacheKey({ ...base, chapter: first })).not.toBe(
      pageCacheKey({ ...base, chapter: first, images: [image] }),
    );
  });

  it("genera ids de página únicos cuando una imagen comparte offset", () => {
    const pages = paginateChapter(
      chapter(["Antes de la figura.", "Después de la figura."]),
      [image],
      measure,
      200,
      "book-a",
    );
    const ids = pages.map((page) => page.id);

    expect(new Set(ids).size).toBe(ids.length);
    expect(pages.some((page) => page.blocks.some((block) => block.kind === "image"))).toBe(true);
  });

  it("guarda y limpia páginas por libro", () => {
    const pages: BookPage[] = [{ id: "p1", blocks: [], startOffset: 0 }];
    setCachedPages("a:key", pages);
    setCachedPages("b:key", pages);
    expect(getCachedPages("a:key")).toBe(pages);

    clearPageCache("a");

    expect(getCachedPages("a:key")).toBeUndefined();
    expect(getCachedPages("b:key")).toBe(pages);
  });
});
