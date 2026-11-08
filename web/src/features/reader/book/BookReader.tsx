import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import { apiUrl } from "../../../api/client";
import type { ManifestChapter, ManifestImage } from "../../../api/types";
import { chapterDisplayTitle } from "../chapterTitle";
import { type BookPage, type PageBlock, pageIndexForOffset, paginateChapter } from "./paginator";

export interface BookPageState {
  pageIndex: number;
  pageCount: number;
  charOffset: number;
}

interface BookReaderProps {
  bookId: string;
  chapter: ManifestChapter;
  images?: ManifestImage[];
  album?: boolean;
  font: string;
  size: number;
  initialCharOffset?: number;
  onPageChange?: (state: BookPageState) => void;
  onBookmark?: (state: BookPageState) => void;
}

const pageCache = new Map<string, BookPage[]>();
const MAX_CACHE = 6;

function cacheKey(
  chapter: ManifestChapter,
  width: number,
  height: number,
  font: string,
  size: number,
  album: boolean,
) {
  return `${chapter.index}:${Math.round(width)}:${Math.round(height)}:${font}:${size}:${album ? "album" : "book"}`;
}

function imageDisplaySize(
  image: ManifestImage,
  contentWidth: number,
  pageHeight: number,
  album: boolean,
): { width: number; height: number } {
  const naturalWidth = image.width && image.width > 0 ? image.width : contentWidth;
  const naturalHeight = image.height && image.height > 0 ? image.height : contentWidth * 0.6;
  let width = Math.min(naturalWidth, contentWidth);
  let height = naturalWidth > 0 ? width * (naturalHeight / naturalWidth) : contentWidth * 0.6;
  const maxHeight = pageHeight * (album ? 0.78 : 0.62);
  if (height > maxHeight) {
    height = maxHeight;
    width = naturalHeight > 0 ? height * (naturalWidth / naturalHeight) : contentWidth;
  }
  return { width, height };
}

export function BookReader({
  bookId,
  chapter,
  images = [],
  album = false,
  font,
  size,
  initialCharOffset = 0,
  onPageChange,
  onBookmark,
}: BookReaderProps) {
  const spreadRef = useRef<HTMLDivElement>(null);
  const initialOffsetRef = useRef(initialCharOffset);
  const turnTimer = useRef<number | null>(null);
  const [pages, setPages] = useState<BookPage[]>([]);
  const [pageIndex, setPageIndex] = useState(0);
  const [spread, setSpread] = useState(false);
  const [pageHeight, setPageHeight] = useState(0);
  const [turn, setTurn] = useState<{ direction: "next" | "prev"; id: number } | null>(null);

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
      const key = cacheKey(chapter, pageWidth, height, font, size, album);
      let nextPages = pageCache.get(key);
      if (!nextPages) {
        const measureElement = document.createElement("div");
        measureElement.className = "book-page book-page--measure";
        measureElement.style.width = `${pageWidth}px`;
        measureElement.style.height = `${height}px`;
        element.appendChild(measureElement);
        const styles = getComputedStyle(measureElement);
        const contentWidth =
          pageWidth -
          (Number.parseFloat(styles.paddingLeft) || 0) -
          (Number.parseFloat(styles.paddingRight) || 0);
        const measure = (blocks: PageBlock[]) => {
          measureElement.replaceChildren(
            ...blocks.map((block) => {
              if (block.kind === "image") {
                const figure = document.createElement("figure");
                figure.className = "book-figure";
                const placeholder = document.createElement("div");
                placeholder.className = "book-figure-placeholder";
                const size = imageDisplaySize(block.image, contentWidth, height, album);
                placeholder.style.width = `${size.width}px`;
                placeholder.style.height = `${size.height}px`;
                figure.appendChild(placeholder);
                if (block.image.caption) {
                  const caption = document.createElement("figcaption");
                  caption.textContent = block.image.caption;
                  figure.appendChild(caption);
                }
                return figure;
              }
              const paragraph = document.createElement("p");
              paragraph.textContent = block.text;
              return paragraph;
            }),
          );
          return measureElement.scrollHeight;
        };
        nextPages = paginateChapter(chapter, images, measure, height);
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
      setPageHeight(height);
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
  }, [album, chapter, font, images, size]);

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

  const changePage = useCallback(
    (direction: "next" | "prev") => {
      if (turn) {
        return;
      }
      const step = spread ? 2 : 1;
      const target =
        direction === "next"
          ? Math.min(pages.length - step, pageIndex + step)
          : Math.max(0, pageIndex - step);
      if (target === pageIndex) {
        return;
      }
      const reduce =
        typeof window.matchMedia === "function" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (reduce) {
        setPageIndex(target);
        return;
      }
      setTurn({ direction, id: Date.now() });
      turnTimer.current = window.setTimeout(() => {
        setPageIndex(target);
        setTurn(null);
        turnTimer.current = null;
      }, 380);
    },
    [pageIndex, pages.length, spread, turn],
  );

  useEffect(
    () => () => {
      if (turnTimer.current !== null) {
        window.clearTimeout(turnTimer.current);
      }
    },
    [],
  );

  const previous = useCallback(() => changePage("prev"), [changePage]);
  const next = useCallback(() => changePage("next"), [changePage]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.tagName === "SELECT" ||
          target.isContentEditable)
      ) {
        return;
      }
      if (event.key === "ArrowRight" || event.key === "PageDown") {
        event.preventDefault();
        next();
      } else if (event.key === "ArrowLeft" || event.key === "PageUp") {
        event.preventDefault();
        previous();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [next, previous]);

  const visible = spread
    ? pages.slice(pageIndex, pageIndex + 2)
    : pages.slice(pageIndex, pageIndex + 1);
  const pageLabel = pages.length > 0 ? `${pageIndex + 1} / ${pages.length}` : "—";
  const progress = pages.length > 0 ? Math.min(1, (pageIndex + 1) / pages.length) : 0;

  return (
    <section
      className={`book-reader${album ? " book-reader--album" : ""}`}
      aria-label={`Lectura de ${chapterDisplayTitle(chapter)}`}
    >
      <header className="book-chapter-head">
        <p className="eyebrow">Capítulo {String(chapter.index).padStart(2, "0")}</p>
        <h1>{chapterDisplayTitle(chapter)}</h1>
      </header>

      <div className={`book-spread${spread ? "" : " book-spread--single"}`} ref={spreadRef}>
        <button
          type="button"
          className="book-ribbon"
          style={{ height: `${52 + progress * 44}px` }}
          onClick={() =>
            onBookmark?.({
              pageIndex,
              pageCount: pages.length,
              charOffset: pages[pageIndex]?.startOffset ?? 0,
            })
          }
          aria-label="Guardar esta página"
          title="Guardar esta página"
        >
          <span className="sr-only">Guardar esta página</span>
        </button>
        {visible.map((page) => (
          <article
            className="book-page"
            key={`${chapter.index}-${page.startOffset}`}
            aria-label={`Página ${pageIndex + visible.indexOf(page) + 1}`}
          >
            <div className="book-page-body">
              {page.blocks.map((block) =>
                block.kind === "image" ? (
                  <figure className="book-figure" key={block.image.id}>
                    <img
                      src={apiUrl(`/books/${bookId}/images/${block.image.id}`)}
                      alt={block.image.alt}
                      loading="lazy"
                      decoding="async"
                      style={{
                        maxHeight: pageHeight
                          ? `${pageHeight * (album ? 0.78 : 0.62)}px`
                          : undefined,
                      }}
                    />
                    {block.image.caption ? <figcaption>{block.image.caption}</figcaption> : null}
                  </figure>
                ) : (
                  <p
                    key={`${block.paragraphIndex}-${block.startOffset}`}
                    className={block.continuation ? "is-continuation" : undefined}
                  >
                    {block.text}
                  </p>
                ),
              )}
            </div>
            <footer className="book-page-number">
              <span>{String(pageIndex + visible.indexOf(page) + 1).padStart(2, "0")}</span>
            </footer>
          </article>
        ))}
        {turn ? (
          <div
            className={`book-leaf book-leaf--${turn.direction}`}
            key={turn.id}
            aria-hidden="true"
          >
            <div className="book-leaf-face book-leaf-front" />
            <div className="book-leaf-face book-leaf-back" />
          </div>
        ) : null}
      </div>

      <nav className="book-nav" aria-label="Navegación de páginas">
        <button
          type="button"
          className="button button--ghost"
          onClick={previous}
          disabled={pageIndex === 0 || turn !== null}
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
          disabled={
            turn !== null || pages.length === 0 || pageIndex >= pages.length - (spread ? 2 : 1)
          }
          aria-label="Página siguiente"
        >
          Siguiente
          <ChevronRight size={17} />
        </button>
      </nav>
    </section>
  );
}
