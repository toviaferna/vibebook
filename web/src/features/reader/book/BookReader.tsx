import { ChevronLeft, ChevronRight } from "lucide-react";
import { type TouchEvent, useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import type { ManifestChapter, ManifestImage } from "../../../api/types";
import { useMediaUrl } from "../../../hooks/useMediaUrl";
import { chapterDisplayTitle } from "../chapterTitle";
import { formatPageLabel, resolvePageMove } from "./navigation";
import { clearPageCache, getCachedPages, pageCacheKey, setCachedPages } from "./pageCache";
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
  hasNextChapter?: boolean;
  hasPreviousChapter?: boolean;
  onNextChapter?: () => void;
  onPreviousChapter?: () => void;
  onPageChange?: (state: BookPageState) => void;
  onBookmark?: (state: BookPageState) => void;
}

const TURN_MS = 220;

export function lastPageIndex(pageCount: number, spread: boolean): number {
  if (pageCount === 0) {
    return 0;
  }
  if (!spread) {
    return pageCount - 1;
  }
  return pageCount % 2 === 0 ? pageCount - 2 : pageCount - 1;
}

function ReaderImage({
  bookId,
  image,
  maxHeight,
}: {
  bookId: string;
  image: ManifestImage;
  maxHeight?: number;
}) {
  const src = useMediaUrl(bookId, "images", `/api/books/${bookId}/images/${image.id}`);
  if (!src) {
    return null;
  }
  return (
    <img
      src={src}
      alt={image.alt}
      loading="lazy"
      decoding="async"
      style={{ maxHeight: maxHeight ? `${maxHeight}px` : undefined }}
    />
  );
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

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function BookReader({
  bookId,
  chapter,
  images = [],
  album = false,
  font,
  size,
  initialCharOffset = 0,
  hasNextChapter = false,
  hasPreviousChapter = false,
  onNextChapter,
  onPreviousChapter,
  onPageChange,
  onBookmark,
}: BookReaderProps) {
  const spreadRef = useRef<HTMLDivElement>(null);
  const initialOffsetRef = useRef(initialCharOffset);
  const lastInitialOffsetRef = useRef(initialCharOffset);
  const currentOffsetRef = useRef(initialCharOffset);
  const hasPaginatedRef = useRef(false);
  const turnTimer = useRef<number | null>(null);
  const chapterTimer = useRef<number | null>(null);
  const chapterLock = useRef(false);
  const touchStart = useRef<{ x: number; y: number; time: number } | null>(null);
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
      const key = pageCacheKey({
        bookId,
        chapter,
        images,
        width: pageWidth,
        height,
        font,
        size,
        album,
      });
      let nextPages = getCachedPages(key);
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
          const footer = document.createElement("footer");
          footer.className = "book-page-number";
          footer.textContent = "00";
          measureElement.replaceChildren(
            ...blocks.map((block) => {
              if (block.kind === "image") {
                const figure = document.createElement("figure");
                figure.className = "book-figure";
                const placeholder = document.createElement("div");
                placeholder.className = "book-figure-placeholder";
                const size = imageDisplaySize(
                  block.image,
                  contentWidth,
                  Math.max(80, height - 40),
                  album,
                );
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
            footer,
          );
          return measureElement.scrollHeight;
        };
        nextPages = paginateChapter(chapter, images, measure, height, bookId);
        measureElement.remove();
        setCachedPages(key, nextPages);
      }
      const anchor = hasPaginatedRef.current ? currentOffsetRef.current : initialOffsetRef.current;
      setSpread(isSpread);
      setPageHeight(height);
      setPages(nextPages);
      const target = pageIndexForOffset(nextPages, anchor);
      const aligned = isSpread ? Math.floor(target / 2) * 2 : target;
      const max = isSpread ? Math.max(0, nextPages.length - 2) : nextPages.length - 1;
      setPageIndex(Math.max(0, Math.min(aligned, max)));
      hasPaginatedRef.current = true;
    };

    paginate();
    let cancelled = false;
    if (typeof document !== "undefined" && document.fonts?.ready) {
      void document.fonts.ready.then(() => {
        if (!cancelled) {
          paginate();
        }
      });
    }
    const observer =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(() => paginate());
    observer?.observe(element);
    return () => {
      cancelled = true;
      observer?.disconnect();
    };
  }, [album, bookId, chapter, font, images, size]);

  useEffect(() => {
    clearPageCache(bookId);
  }, [bookId]);

  useEffect(() => {
    if (pages.length === 0) {
      return;
    }
    const max = spread ? Math.max(0, pages.length - 2) : pages.length - 1;
    setPageIndex((current) => Math.min(current, max));
  }, [pages, spread]);

  useEffect(() => {
    const page = pages[pageIndex];
    if (page) {
      currentOffsetRef.current = page.startOffset;
    }
  }, [pageIndex, pages]);

  useEffect(() => {
    if (initialCharOffset === lastInitialOffsetRef.current) {
      return;
    }
    lastInitialOffsetRef.current = initialCharOffset;
    initialOffsetRef.current = initialCharOffset;
    if (pages.length === 0) {
      return;
    }
    const currentPage = pages[pageIndex];
    if (currentPage && initialCharOffset === currentPage.startOffset) {
      return;
    }
    const target = pageIndexForOffset(pages, initialCharOffset);
    const aligned = spread ? Math.floor(target / 2) * 2 : target;
    const max = spread ? Math.max(0, pages.length - 2) : pages.length - 1;
    setPageIndex(Math.max(0, Math.min(aligned, max)));
  }, [initialCharOffset, pageIndex, pages, spread]);

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
      const move = resolvePageMove({
        pageIndex,
        pageCount: pages.length,
        spread,
        direction,
        hasNextChapter,
        hasPreviousChapter,
      });
      if (move.kind === "page") {
        setPageIndex(move.index);
        if (prefersReducedMotion()) {
          setTurn(null);
          return;
        }
        if (turnTimer.current !== null) {
          window.clearTimeout(turnTimer.current);
        }
        setTurn({ direction, id: Date.now() });
        turnTimer.current = window.setTimeout(() => {
          setTurn(null);
          turnTimer.current = null;
        }, TURN_MS);
        return;
      }
      if (move.kind !== "chapter" || chapterLock.current) {
        return;
      }
      chapterLock.current = true;
      if (move.direction === "next") {
        onNextChapter?.();
      } else {
        onPreviousChapter?.();
      }
      if (chapterTimer.current !== null) {
        window.clearTimeout(chapterTimer.current);
      }
      chapterTimer.current = window.setTimeout(() => {
        chapterLock.current = false;
        chapterTimer.current = null;
      }, 600);
    },
    [
      hasNextChapter,
      hasPreviousChapter,
      onNextChapter,
      onPreviousChapter,
      pageIndex,
      pages.length,
      spread,
    ],
  );

  useEffect(
    () => () => {
      if (turnTimer.current !== null) {
        window.clearTimeout(turnTimer.current);
      }
      if (chapterTimer.current !== null) {
        window.clearTimeout(chapterTimer.current);
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
      if (document.querySelector('[role="dialog"]')) {
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

  const onTouchStart = (event: TouchEvent<HTMLDivElement>) => {
    if (event.touches.length !== 1) {
      return;
    }
    touchStart.current = {
      x: event.touches[0].clientX,
      y: event.touches[0].clientY,
      time: Date.now(),
    };
  };

  const onTouchEnd = (event: TouchEvent<HTMLDivElement>) => {
    const start = touchStart.current;
    touchStart.current = null;
    if (!start || event.changedTouches.length !== 1) {
      return;
    }
    if (Date.now() - start.time > 700) {
      return;
    }
    const dx = event.changedTouches[0].clientX - start.x;
    const dy = event.changedTouches[0].clientY - start.y;
    if (Math.abs(dx) < 48 || Math.abs(dx) < Math.abs(dy) * 1.4) {
      return;
    }
    if (typeof window.getSelection === "function" && window.getSelection()?.toString()) {
      return;
    }
    if (dx < 0) {
      next();
    } else {
      previous();
    }
  };

  const visible = spread
    ? pages.slice(pageIndex, pageIndex + 2)
    : pages.slice(pageIndex, pageIndex + 1);
  const atFirst = pageIndex === 0;
  const lastPage = lastPageIndex(pages.length, spread);
  const atLast = pages.length === 0 || pageIndex >= lastPage;
  const canPrevious = pages.length > 0 && (!atFirst || hasPreviousChapter);
  const canNext = pages.length > 0 && (!atLast || hasNextChapter);
  const label = formatPageLabel(pageIndex, pages.length, spread);

  return (
    <section
      className={`book-reader${album ? " book-reader--album" : ""}`}
      aria-label={`Lectura de ${chapterDisplayTitle(chapter)}`}
    >
      <header className="book-chapter-head">
        <p className="eyebrow">Capítulo {String(chapter.index).padStart(2, "0")}</p>
        <h1>{chapterDisplayTitle(chapter)}</h1>
      </header>

      <div
        className={`book-spread${spread ? "" : " book-spread--single"}`}
        ref={spreadRef}
        data-turn={turn?.direction}
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
        onTouchCancel={() => {
          touchStart.current = null;
        }}
      >
        <button
          type="button"
          className="book-ribbon"
          style={{ height: `${52 + (pages.length ? (pageIndex + 1) / pages.length : 0) * 44}px` }}
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
            key={page.id ?? `${chapter.index}-${page.startOffset}`}
            aria-label={`Página ${pageIndex + visible.indexOf(page) + 1}`}
          >
            <div className="book-page-body">
              {page.blocks.map((block) =>
                block.kind === "image" ? (
                  <figure className="book-figure" key={block.image.id}>
                    <ReaderImage
                      bookId={bookId}
                      image={block.image}
                      maxHeight={pageHeight ? pageHeight * (album ? 0.78 : 0.62) : undefined}
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
      </div>

      <nav className="book-nav" aria-label="Navegación de páginas">
        <button
          type="button"
          className="button button--ghost"
          onClick={previous}
          disabled={!canPrevious}
          aria-label={atFirst && hasPreviousChapter ? "Capítulo anterior" : "Página anterior"}
        >
          <ChevronLeft size={17} />
          {atFirst && hasPreviousChapter ? "Capítulo anterior" : "Anterior"}
        </button>
        <span className="mono muted" aria-live="polite">
          {label}
        </span>
        <button
          type="button"
          className="button button--ghost"
          onClick={next}
          disabled={!canNext}
          aria-label={atLast && hasNextChapter ? "Siguiente capítulo" : "Página siguiente"}
        >
          {atLast && hasNextChapter ? "Siguiente capítulo" : "Siguiente"}
          <ChevronRight size={17} />
        </button>
      </nav>
      {atLast && !hasNextChapter ? (
        <p className="book-end" role="status">
          Fin del libro
        </p>
      ) : null}
    </section>
  );
}
