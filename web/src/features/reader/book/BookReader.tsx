import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import type { ManifestChapter } from "../../../api/types";
import { chapterDisplayTitle } from "../chapterTitle";
import { type BookPage, pageIndexForOffset, paginateChapter } from "./paginator";

export interface BookPageState {
  pageIndex: number;
  pageCount: number;
  charOffset: number;
}

interface BookReaderProps {
  chapter: ManifestChapter;
  font: string;
  size: number;
  initialCharOffset?: number;
  onPageChange?: (state: BookPageState) => void;
}

const pageCache = new Map<string, BookPage[]>();
const MAX_CACHE = 6;

function cacheKey(
  chapter: ManifestChapter,
  width: number,
  height: number,
  font: string,
  size: number,
) {
  return `${chapter.index}:${Math.round(width)}:${Math.round(height)}:${font}:${size}`;
}

export function BookReader({
  chapter,
  font,
  size,
  initialCharOffset = 0,
  onPageChange,
}: BookReaderProps) {
  const spreadRef = useRef<HTMLDivElement>(null);
  const initialOffsetRef = useRef(initialCharOffset);
  const [pages, setPages] = useState<BookPage[]>([]);
  const [pageIndex, setPageIndex] = useState(0);
  const [spread, setSpread] = useState(false);

  useLayoutEffect(() => {
    const element = spreadRef.current;
    if (!element) {
      return;
    }

    const paginate = () => {
      const width = element.clientWidth;
      const height = element.clientHeight;
      if (width <= 0 || height <= 0) {
        return;
      }
      const isSpread = width >= 820;
      const gap = isSpread ? 24 : 0;
      const pageWidth = isSpread ? (width - gap) / 2 : width;
      const key = cacheKey(chapter, pageWidth, height, font, size);
      let nextPages = pageCache.get(key);
      if (!nextPages) {
        const measureElement = document.createElement("div");
        measureElement.className = "book-page book-page--measure";
        measureElement.style.width = `${pageWidth}px`;
        measureElement.style.height = `${height}px`;
        element.appendChild(measureElement);
        const measure = (blocks: BookPage["blocks"]) => {
          measureElement.replaceChildren(
            ...blocks.map((block) => {
              const paragraph = document.createElement("p");
              paragraph.textContent = block.text;
              return paragraph;
            }),
          );
          return measureElement.scrollHeight;
        };
        nextPages = paginateChapter(chapter, measure, height);
        measureElement.remove();
        pageCache.set(key, nextPages);
        if (pageCache.size > MAX_CACHE) {
          const first = pageCache.keys().next().value;
          if (first) {
            pageCache.delete(first);
          }
        }
      }
      setSpread(isSpread);
      setPages(nextPages);
      const target = pageIndexForOffset(nextPages, initialOffsetRef.current);
      const aligned = isSpread ? Math.floor(target / 2) * 2 : target;
      const max = isSpread ? Math.max(0, nextPages.length - 2) : nextPages.length - 1;
      setPageIndex(Math.max(0, Math.min(aligned, max)));
    };

    paginate();
    const observer =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(() => paginate());
    observer?.observe(element);
    return () => observer?.disconnect();
  }, [chapter, font, size]);

  useEffect(() => {
    if (pages.length === 0) {
      return;
    }
    const max = spread ? Math.max(0, pages.length - 2) : pages.length - 1;
    setPageIndex((current) => Math.min(current, max));
  }, [pages, spread]);

  useEffect(() => {
    const page = pages[pageIndex];
    if (!page || !onPageChange) {
      return;
    }
    onPageChange({
      pageIndex,
      pageCount: pages.length,
      charOffset: page.startOffset,
    });
  }, [onPageChange, pageIndex, pages]);

  const previous = useCallback(() => {
    setPageIndex((current) => Math.max(0, current - (spread ? 2 : 1)));
  }, [spread]);

  const next = useCallback(() => {
    setPageIndex((current) =>
      Math.min(pages.length - (spread ? 2 : 1), current + (spread ? 2 : 1)),
    );
  }, [pages.length, spread]);

  const visible = spread
    ? pages.slice(pageIndex, pageIndex + 2)
    : pages.slice(pageIndex, pageIndex + 1);
  const pageLabel = pages.length > 0 ? `${pageIndex + 1} / ${pages.length}` : "—";

  return (
    <section className="book-reader" aria-label={`Lectura de ${chapterDisplayTitle(chapter)}`}>
      <header className="book-chapter-head">
        <p className="eyebrow">Capítulo {String(chapter.index).padStart(2, "0")}</p>
        <h1>{chapterDisplayTitle(chapter)}</h1>
      </header>

      <div className={`book-spread${spread ? "" : " book-spread--single"}`} ref={spreadRef}>
        {visible.map((page) => (
          <article
            className="book-page"
            key={`${chapter.index}-${page.startOffset}`}
            aria-label={`Página ${pageIndex + visible.indexOf(page) + 1}`}
          >
            <div className="book-page-body">
              {page.blocks.map((block) => (
                <p
                  key={`${block.paragraphIndex}-${block.startOffset}`}
                  className={block.continuation ? "is-continuation" : undefined}
                >
                  {block.text}
                </p>
              ))}
            </div>
            <footer className="book-page-number">
              <span>{String(pageIndex + visible.indexOf(page) + 1).padStart(2, "0")}</span>
            </footer>
          </article>
        ))}
      </div>

      <nav className="book-nav" aria-label="Navegación de páginas">
        <button
          type="button"
          className="button button--ghost"
          onClick={previous}
          disabled={pageIndex === 0}
          aria-label="Página anterior"
        >
          <ChevronLeft size={17} />
          Anterior
        </button>
        <span className="mono muted" aria-live="polite">
          Página {pageLabel}
        </span>
        <button
          type="button"
          className="button button--ghost"
          onClick={next}
          disabled={pages.length === 0 || pageIndex >= pages.length - (spread ? 2 : 1)}
          aria-label="Página siguiente"
        >
          Siguiente
          <ChevronRight size={17} />
        </button>
      </nav>
    </section>
  );
}
