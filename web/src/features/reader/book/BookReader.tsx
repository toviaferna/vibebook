import {
  Binding,
  type BookRect,
  computeLayout,
  type Book as FlipBookApi,
  Layout,
  type LayoutResult,
  type Orientation,
} from "@openpageflip/core";
import { FlipBook, Page } from "@openpageflip/react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { memo, useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import type { ManifestChapter, ManifestImage } from "../../../api/types";
import { useMediaUrl } from "../../../hooks/useMediaUrl";
import { chapterDisplayTitle } from "../chapterTitle";
import { formatPageLabel } from "./navigation";
import { clearPageCache, getCachedPages, pageCacheKey, setCachedPages } from "./pageCache";
import { type BookPage, type PageBlock, pageIndexForOffset, paginateChapter } from "./paginator";
import "@openpageflip/core/styles.css";

export interface BookPageState {
  pageIndex: number;
  pageCount: number;
  charOffset: number;
}

export interface BookHighlight {
  start: number;
  end: number;
  wordStart?: number;
  wordEnd?: number;
}

interface BookReaderProps {
  bookId: string;
  chapter: ManifestChapter;
  images?: ManifestImage[];
  album?: boolean;
  font: string;
  size: number;
  initialCharOffset?: number;
  activeOffset?: number | null;
  highlight?: BookHighlight | null;
  autoPageTurn?: boolean;
  hasNextChapter?: boolean;
  hasPreviousChapter?: boolean;
  onNextChapter?: () => void;
  onPreviousChapter?: () => void;
  onPageChange?: (state: BookPageState) => void;
  onBookmark?: (state: BookPageState) => void;
  onManualTurn?: () => void;
}

const BASE_WIDTH = 600;
const BASE_HEIGHT = 820;
const MIN_PAGE_WIDTH = 300;
const MAX_PAGE_WIDTH = 620;

function easePageTurn(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
}

function pageEndOffset(page: BookPage): number {
  let end = page.startOffset;
  for (const block of page.blocks) {
    if (block.kind === "text") {
      end = Math.max(end, block.startOffset + block.text.length);
    }
  }
  return end;
}

function HighlightedText({
  text,
  startOffset,
  highlight,
}: {
  text: string;
  startOffset: number;
  highlight: BookHighlight;
}) {
  const blockEnd = startOffset + text.length;
  if (highlight.end <= startOffset || highlight.start >= blockEnd) {
    return <>{text}</>;
  }
  const from = Math.max(0, highlight.start - startOffset);
  const to = Math.min(text.length, highlight.end - startOffset);
  const wordFrom =
    highlight.wordStart == null
      ? null
      : Math.max(from, Math.min(to, highlight.wordStart - startOffset));
  const wordTo =
    highlight.wordEnd == null
      ? null
      : Math.max(from, Math.min(to, highlight.wordEnd - startOffset));
  const hasWord = wordFrom != null && wordTo != null && wordTo > wordFrom;

  return (
    <>
      {text.slice(0, from)}
      <span className="book-highlight-segment">
        {hasWord ? (
          <>
            {text.slice(from, wordFrom)}
            <mark className="book-highlight-word">{text.slice(wordFrom, wordTo)}</mark>
            {text.slice(wordTo, to)}
          </>
        ) : (
          text.slice(from, to)
        )}
      </span>
      {text.slice(to)}
    </>
  );
}

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
  const maxHeight = pageHeight * (album ? 0.72 : 0.56);
  if (height > maxHeight) {
    height = maxHeight;
    width = naturalHeight > 0 ? height * (naturalWidth / naturalHeight) : contentWidth;
  }
  return { width, height };
}

function bookLayout(width: number, height: number, layout: Layout = Layout.auto): LayoutResult {
  return computeLayout(width, height, {
    size: "stretch",
    width: BASE_WIDTH,
    height: BASE_HEIGHT,
    minWidth: MIN_PAGE_WIDTH,
    maxWidth: MAX_PAGE_WIDTH,
    layout,
    binding: Binding.left,
  });
}

const BookPageView = memo(function BookPageView({
  bookId,
  chapterTitle,
  page,
  pageNumber,
  album,
  pageHeight,
  highlight,
}: {
  bookId: string;
  chapterTitle: string;
  page: BookPage;
  pageNumber: number;
  album: boolean;
  pageHeight: number;
  highlight: BookHighlight | null;
}) {
  return (
    <article className="book-page" aria-label={`Página ${pageNumber}`}>
      <div className="book-page-running-head" aria-hidden="true">
        <span>{chapterTitle}</span>
      </div>
      <div className="book-page-body">
        {page.blocks.map((block) =>
          block.kind === "image" ? (
            <figure className="book-figure" key={block.image.id}>
              <ReaderImage
                bookId={bookId}
                image={block.image}
                maxHeight={pageHeight ? pageHeight * (album ? 0.72 : 0.56) : undefined}
              />
              {block.image.caption ? <figcaption>{block.image.caption}</figcaption> : null}
            </figure>
          ) : (
            <p
              key={`${block.paragraphIndex}-${block.startOffset}`}
              className={block.continuation ? "is-continuation" : undefined}
            >
              {highlight ? (
                <HighlightedText
                  text={block.text}
                  startOffset={block.startOffset}
                  highlight={highlight}
                />
              ) : (
                block.text
              )}
            </p>
          ),
        )}
      </div>
      <footer className="book-page-number" aria-hidden="true">
        <span>{String(pageNumber).padStart(2, "0")}</span>
      </footer>
    </article>
  );
});

export function BookReader({
  bookId,
  chapter,
  images = [],
  album = false,
  font,
  size,
  initialCharOffset = 0,
  activeOffset = null,
  highlight = null,
  autoPageTurn = false,
  hasNextChapter = false,
  hasPreviousChapter = false,
  onNextChapter,
  onPreviousChapter,
  onPageChange,
  onBookmark,
  onManualTurn,
}: BookReaderProps) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const bookRef = useRef<FlipBookApi | null>(null);
  const bookSurfaceRef = useRef<HTMLDivElement>(null);
  const initialOffsetRef = useRef(initialCharOffset);
  const lastInitialOffsetRef = useRef(initialCharOffset);
  const currentOffsetRef = useRef(initialCharOffset);
  const hasPaginatedRef = useRef(false);
  const programmaticTurnRef = useRef(false);
  const reducedMotion = useReducedMotion();
  const [pages, setPages] = useState<BookPage[]>([]);
  const [pageIndex, setPageIndex] = useState(0);
  const [orientation, setOrientation] = useState<Orientation>("landscape");
  const [pageHeight, setPageHeight] = useState(0);
  const [bookRect, setBookRect] = useState<BookRect | null>(null);
  const chapterTitle = chapterDisplayTitle(chapter);
  const spread = orientation === "landscape";
  const singleLayout = pages.length === 1;
  const renderedSpread = spread && !singleLayout;
  const visibleBook = bookRect
    ? {
        left: renderedSpread ? bookRect.left : bookRect.left + bookRect.width / 2,
        top: bookRect.top,
        width: renderedSpread ? bookRect.width : bookRect.pageWidth,
        height: bookRect.height,
      }
    : null;

  useLayoutEffect(() => {
    const element = viewportRef.current;
    if (!element) {
      return;
    }

    const paginate = () => {
      const width = element.clientWidth;
      const height = element.clientHeight;
      if (width <= 0 || height <= 0) {
        return;
      }
      const autoLayout = bookLayout(width, height);
      const autoRect = autoLayout.rect;
      const isSpreadCandidate = autoLayout.orientation === "landscape";
      const key = pageCacheKey({
        bookId,
        chapter,
        images,
        width: autoRect.pageWidth,
        height: autoRect.height,
        font,
        size,
        album,
      });
      let nextPages = getCachedPages(key);
      if (!nextPages) {
        const measureElement = document.createElement("div");
        measureElement.className = "book-page book-page--measure";
        measureElement.style.width = `${autoRect.pageWidth}px`;
        measureElement.style.height = "auto";
        element.appendChild(measureElement);
        const styles = getComputedStyle(measureElement);
        const contentWidth =
          autoRect.pageWidth -
          (Number.parseFloat(styles.paddingLeft) || 0) -
          (Number.parseFloat(styles.paddingRight) || 0);
        const measure = (blocks: PageBlock[]) => {
          const runningHead = document.createElement("div");
          runningHead.className = "book-page-running-head";
          runningHead.textContent = chapterTitle;
          const footer = document.createElement("footer");
          footer.className = "book-page-number";
          footer.textContent = "00";
          const body = document.createElement("div");
          body.className = "book-page-body";
          body.append(
            ...blocks.map((block) => {
              if (block.kind === "image") {
                const figure = document.createElement("figure");
                figure.className = "book-figure";
                const placeholder = document.createElement("div");
                placeholder.className = "book-figure-placeholder";
                const imageSize = imageDisplaySize(
                  block.image,
                  contentWidth,
                  Math.max(80, autoRect.height - 64),
                  album,
                );
                placeholder.style.width = `${imageSize.width}px`;
                placeholder.style.height = `${imageSize.height}px`;
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
          measureElement.replaceChildren(runningHead, body, footer);
          return measureElement.scrollHeight;
        };
        nextPages = paginateChapter(chapter, images, measure, autoRect.height, bookId);
        measureElement.remove();
        setCachedPages(key, nextPages);
      }
      const single = nextPages.length === 1;
      const layout = single ? bookLayout(width, height, Layout.single) : autoLayout;
      const rect = layout.rect;
      const isSpread = !single && isSpreadCandidate;
      const anchor = hasPaginatedRef.current ? currentOffsetRef.current : initialOffsetRef.current;
      const target = pageIndexForOffset(nextPages, anchor);
      const max = lastPageIndex(nextPages.length, isSpread);
      setOrientation(isSpread ? "landscape" : "portrait");
      setPageHeight(rect.height);
      setBookRect(rect);
      setPages(nextPages);
      setPageIndex(Math.max(0, Math.min(target, max)));
      hasPaginatedRef.current = true;
    };

    let frame = 0;
    const schedule = () => {
      if (frame) {
        return;
      }
      frame = window.requestAnimationFrame(() => {
        frame = 0;
        paginate();
      });
    };

    paginate();
    let cancelled = false;
    if (typeof document !== "undefined" && document.fonts?.ready) {
      void document.fonts.ready.then(() => {
        if (!cancelled) {
          schedule();
        }
      });
    }
    const observer =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(() => schedule());
    observer?.observe(element);
    return () => {
      cancelled = true;
      if (frame) {
        window.cancelAnimationFrame(frame);
      }
      observer?.disconnect();
    };
  }, [album, bookId, chapter, chapterTitle, font, images, size]);

  useEffect(() => {
    clearPageCache(bookId);
  }, [bookId]);

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
    setPageIndex(Math.max(0, Math.min(target, lastPageIndex(pages.length, spread))));
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

  const handleFlip = useCallback(
    (event: { page: number }) => {
      if (!programmaticTurnRef.current) {
        onManualTurn?.();
      }
      setPageIndex(event.page);
      const current = bookRef.current;
      if (current) {
        setOrientation(current.orientation);
      }
    },
    [onManualTurn],
  );

  const handleProgress = useCallback((event: { progress: number }) => {
    bookSurfaceRef.current?.style.setProperty("--turn-progress", String(event.progress));
  }, []);

  const atFirst = pageIndex === 0;
  const atLast = pages.length === 0 || pageIndex >= lastPageIndex(pages.length, spread);
  const canPrevious = pages.length > 0 && (!atFirst || hasPreviousChapter);
  const canNext = pages.length > 0 && (!atLast || hasNextChapter);
  const label = formatPageLabel(pageIndex, pages.length, spread);

  useEffect(() => {
    if (!autoPageTurn || activeOffset == null || pages.length === 0) {
      return;
    }
    const book = bookRef.current;
    if (!book) {
      return;
    }
    if (programmaticTurnRef.current) {
      return;
    }
    const raw = pageIndexForOffset(pages, activeOffset);
    const aligned = spread ? Math.floor(raw / 2) * 2 : raw;
    const target = Math.max(0, Math.min(aligned, lastPageIndex(pages.length, spread)));
    if (target === pageIndex) {
      return;
    }
    programmaticTurnRef.current = true;
    void book.flipTo(target).finally(() => {
      programmaticTurnRef.current = false;
    });
  }, [activeOffset, autoPageTurn, pageIndex, pages, spread]);

  const previous = useCallback(() => {
    programmaticTurnRef.current = false;
    if (!atFirst) {
      void bookRef.current?.flipPrev();
      return;
    }
    if (hasPreviousChapter) {
      onPreviousChapter?.();
    }
  }, [atFirst, hasPreviousChapter, onPreviousChapter]);

  const next = useCallback(() => {
    programmaticTurnRef.current = false;
    if (!atLast) {
      void bookRef.current?.flipNext();
      return;
    }
    if (hasNextChapter) {
      onNextChapter?.();
    }
  }, [atLast, hasNextChapter, onNextChapter]);

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

  return (
    <section
      className={`book-reader${album ? " book-reader--album" : ""}`}
      aria-label={`Lectura de ${chapterTitle}`}
    >
      <h1 className="sr-only">{chapterTitle}</h1>
      <motion.div
        className="book-table"
        initial={reducedMotion ? false : { opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
      >
        <div
          className={`book-viewport${renderedSpread ? "" : " book-viewport--single"}`}
          ref={viewportRef}
        >
          <div className="book-surface" ref={bookSurfaceRef}>
            {visibleBook ? (
              <div
                className="book-backdrop"
                aria-hidden="true"
                style={{
                  left: `${visibleBook.left}px`,
                  top: `${visibleBook.top}px`,
                  width: `${visibleBook.width}px`,
                  height: `${visibleBook.height}px`,
                }}
              >
                <span className="book-ground" />
                <span className="book-back" />
              </div>
            ) : null}
            {pages.length > 0 ? (
              <FlipBook
                ref={bookRef}
                className="book-object"
                width={BASE_WIDTH}
                height={BASE_HEIGHT}
                size="stretch"
                minWidth={MIN_PAGE_WIDTH}
                maxWidth={MAX_PAGE_WIDTH}
                layout={singleLayout ? Layout.single : Layout.auto}
                binding={Binding.left}
                autoSize={false}
                cover={false}
                flipDuration={reducedMotion ? 0 : 520}
                easing={easePageTurn}
                shadows
                shadowOpacity={0.34}
                click="edges"
                drag
                swipe
                hover
                startPage={pageIndex}
                page={pageIndex}
                onInit={({ orientation: nextOrientation }) => setOrientation(nextOrientation)}
                onChangeOrientation={(event) => setOrientation(event.orientation)}
                onFlip={handleFlip}
                onFlipProgress={handleProgress}
              >
                {pages.map((page, index) => {
                  const pageHighlight =
                    highlight &&
                    highlight.end > page.startOffset &&
                    highlight.start < pageEndOffset(page)
                      ? highlight
                      : null;
                  return (
                    <Page className="book-leaf" density="soft" key={page.id ?? index}>
                      <BookPageView
                        bookId={bookId}
                        chapterTitle={chapterTitle}
                        page={page}
                        pageNumber={index + 1}
                        album={album}
                        pageHeight={pageHeight}
                        highlight={pageHighlight}
                      />
                    </Page>
                  );
                })}
              </FlipBook>
            ) : (
              <div className="book-page-loading" role="status" aria-label="Preparando páginas">
                <span className="skeleton skeleton--title" />
                <span className="skeleton" />
              </div>
            )}
            {visibleBook ? (
              <span
                className="book-spine"
                aria-hidden="true"
                style={{
                  left: renderedSpread
                    ? `${visibleBook.left + visibleBook.width / 2}px`
                    : `${visibleBook.left}px`,
                  top: `${visibleBook.top}px`,
                  height: `${visibleBook.height}px`,
                }}
              />
            ) : null}
            {visibleBook ? (
              <button
                type="button"
                className="book-ribbon"
                style={{
                  left: `${visibleBook.left + visibleBook.width - 24}px`,
                  top: `${visibleBook.top + 18}px`,
                  height: `${52 + (pages.length ? (pageIndex + 1) / pages.length : 0) * 44}px`,
                }}
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
            ) : null}
          </div>
        </div>
      </motion.div>

      <nav className="book-nav" aria-label="Navegación de páginas">
        <button
          type="button"
          className="button button--ghost"
          onClick={previous}
          disabled={!canPrevious}
          aria-label={atFirst && hasPreviousChapter ? "Capítulo anterior" : "Página anterior"}
        >
          <ChevronLeft size={17} />
          Anterior
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
          Siguiente
          <ChevronRight size={17} />
        </button>
      </nav>
      <p className="book-end" role={atLast && !hasNextChapter ? "status" : undefined}>
        {atLast && !hasNextChapter ? "Fin del libro" : "\u00A0"}
      </p>
    </section>
  );
}
