import {
  Binding,
  type BookRect,
  computeLayout,
  type Book as FlipBookApi,
  Layout,
  type Orientation,
} from "@openpageflip/core";
import { FlipBook, Page } from "@openpageflip/react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import {
  Fragment,
  memo,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import type { ManifestChapter, ManifestImage } from "../../../api/types";
import { useMediaUrl } from "../../../hooks/useMediaUrl";
import type { AlignedSegment } from "../alignment";
import { chapterDisplayTitle } from "../chapterTitle";
import {
  blockWords,
  buildChapterHighlight,
  type ChapterHighlight,
  type ParagraphHighlight,
  wordsText,
} from "./highlight";
import { formatPageLabel } from "./navigation";
import { clearPageCache, getCachedPages, pageCacheKey, setCachedPages } from "./pageCache";
import {
  type BookPage,
  type PageBlock,
  pageIndexForOffset,
  paginateChapter,
  type TextBlock,
} from "./paginator";
import "@openpageflip/core/styles.css";

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
  alignments?: Map<string, AlignedSegment>;
  activeSegmentId?: string | null;
  activeWordIndex?: number | null;
  follow?: boolean;
  karaoke?: boolean;
  initialCharOffset?: number;
  hasNextChapter?: boolean;
  hasPreviousChapter?: boolean;
  onNextChapter?: () => void;
  onPreviousChapter?: () => void;
  onPageChange?: (state: BookPageState) => void;
  onBookmark?: (state: BookPageState) => void;
  onToggleKaraoke?: () => void;
  onManualTurn?: () => void;
}

const BASE_WIDTH = 600;
const BASE_HEIGHT = 820;
const MIN_PAGE_WIDTH = 300;
const MAX_PAGE_WIDTH = 620;
const EMPTY_ALIGNMENTS = new Map<string, AlignedSegment>();
const BOOK_EASE = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

function BookText({
  block,
  paragraph,
  karaoke,
  activeSegmentId,
  activeWordIndex,
}: {
  block: TextBlock;
  paragraph: ParagraphHighlight | undefined;
  karaoke: boolean;
  activeSegmentId: string | null;
  activeWordIndex: number | null;
}) {
  if (!karaoke || !paragraph || !activeSegmentId) {
    return <>{block.text}</>;
  }
  const words = blockWords(block, paragraph).filter((word) => word.segmentId === activeSegmentId);
  if (words.length === 0) {
    return <>{block.text}</>;
  }
  const from = Math.max(0, words[0].start - block.startOffset);
  const to = Math.min(block.text.length, words[words.length - 1].end - block.startOffset);
  const inner = block.text.slice(from, to);
  if (!inner || wordsText(words) !== inner) {
    return <>{block.text}</>;
  }
  return (
    <>
      {block.text.slice(0, from)}
      {words.map((word, index) => {
        const wordActive = word.wordIndex === activeWordIndex;
        return (
          <Fragment key={`${word.segmentId}-${word.wordIndex ?? "x"}-${word.start}`}>
            <span
              className={`book-word is-segment-active${wordActive ? " is-active" : ""}`}
              data-segment-id={word.segmentId}
              data-word-index={word.wordIndex ?? undefined}
            >
              {word.text}
            </span>
            {index < words.length - 1 ? " " : ""}
          </Fragment>
        );
      })}
      {block.text.slice(to)}
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

function pageEndOffset(page: BookPage): number {
  let end = page.startOffset;
  for (const block of page.blocks) {
    if (block.kind === "text") {
      end = Math.max(end, block.startOffset + block.text.length);
    }
  }
  return end;
}

export function bookLayout(width: number, height: number) {
  return computeLayout(width, height, {
    size: "stretch",
    width: BASE_WIDTH,
    height: BASE_HEIGHT,
    minWidth: MIN_PAGE_WIDTH,
    maxWidth: MAX_PAGE_WIDTH,
    layout: Layout.auto,
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
  karaoke,
  activeSegmentId,
  activeWordIndex,
}: {
  bookId: string;
  chapterTitle: string;
  page: BookPage;
  pageNumber: number;
  album: boolean;
  pageHeight: number;
  highlight: ChapterHighlight;
  karaoke: boolean;
  activeSegmentId: string | null;
  activeWordIndex: number | null;
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
              <BookText
                block={block}
                paragraph={highlight.paragraphs.get(block.paragraphIndex)}
                karaoke={karaoke}
                activeSegmentId={activeSegmentId}
                activeWordIndex={activeWordIndex}
              />
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
  alignments = EMPTY_ALIGNMENTS,
  activeSegmentId = null,
  activeWordIndex = null,
  follow = false,
  karaoke = false,
  initialCharOffset = 0,
  hasNextChapter = false,
  hasPreviousChapter = false,
  onNextChapter,
  onPreviousChapter,
  onPageChange,
  onBookmark,
  onToggleKaraoke,
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
  const [bookState, setBookState] = useState("read");
  const chapterTitle = chapterDisplayTitle(chapter);
  const spread = orientation === "landscape";
  const singleLayout = pages.length === 1;
  const renderedSpread = spread && !singleLayout;
  const highlight = useMemo(
    () => buildChapterHighlight(chapter, alignments),
    [alignments, chapter],
  );
  const hasKaraoke = alignments.size > 0;
  const activeRange = activeSegmentId ? highlight.segmentRanges.get(activeSegmentId) : undefined;
  const activeWordOffsets = activeSegmentId
    ? highlight.segmentWordOffsets.get(activeSegmentId)
    : undefined;
  const activeOffset =
    activeWordIndex !== null && activeWordIndex >= 0 && activeWordOffsets
      ? (activeWordOffsets[activeWordIndex] ?? activeRange?.start)
      : activeRange?.start;
  const rawActivePage = activeOffset === undefined ? null : pageIndexForOffset(pages, activeOffset);
  const activePage =
    rawActivePage === null
      ? null
      : Math.min(
          spread && rawActivePage % 2 === 1 ? rawActivePage - 1 : rawActivePage,
          lastPageIndex(pages.length, spread),
        );
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
      const rect = bookLayout(width, height);
      const isSpread = rect.orientation === "landscape";
      const bookRect = rect.rect;
      const key = pageCacheKey({
        bookId,
        chapter,
        images,
        width: bookRect.pageWidth,
        height: bookRect.height,
        font,
        size,
        album,
      });
      let nextPages = getCachedPages(key);
      if (!nextPages) {
        const measureElement = document.createElement("div");
        measureElement.className = "book-page book-page--measure";
        measureElement.style.width = `${bookRect.pageWidth}px`;
        measureElement.style.height = "auto";
        element.appendChild(measureElement);
        const styles = getComputedStyle(measureElement);
        const contentWidth =
          bookRect.pageWidth -
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
                  Math.max(80, bookRect.height - 64),
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
        nextPages = paginateChapter(chapter, images, measure, bookRect.height, bookId);
        measureElement.remove();
        setCachedPages(key, nextPages);
      }
      const anchor = hasPaginatedRef.current ? currentOffsetRef.current : initialOffsetRef.current;
      const target = pageIndexForOffset(nextPages, anchor);
      const max = lastPageIndex(nextPages.length, isSpread);
      setOrientation(isSpread ? "landscape" : "portrait");
      setPageHeight(bookRect.height);
      setBookRect(bookRect);
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

  useEffect(() => {
    if (!follow || activeOffset == null || pages.length === 0) {
      return;
    }
    if (bookState === "flipping" || bookState === "user_fold") {
      return;
    }
    if (programmaticTurnRef.current) {
      return;
    }
    const book = bookRef.current;
    if (!book) {
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
  }, [activeOffset, bookState, follow, pageIndex, pages, spread]);

  const handleFlip = useCallback(
    (event: { page: number }) => {
      const automatic = programmaticTurnRef.current;
      programmaticTurnRef.current = false;
      setPageIndex(event.page);
      const current = bookRef.current;
      if (current) {
        setOrientation(current.orientation);
      }
      if (!automatic) {
        onManualTurn?.();
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
              <div className="book-clip">
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
                  easing={BOOK_EASE}
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
                  onChangeState={(event) => setBookState(event.state)}
                  onFlip={handleFlip}
                  onFlipProgress={handleProgress}
                >
                  {pages.map((page, index) => {
                    const pageHasActiveSegment =
                      activeRange !== undefined &&
                      activeRange.end > page.startOffset &&
                      activeRange.start < pageEndOffset(page);
                    const pageActiveSegmentId = pageHasActiveSegment ? activeSegmentId : null;
                    return (
                      <Page className="book-leaf" density="soft" key={page.id ?? index}>
                        <BookPageView
                          bookId={bookId}
                          chapterTitle={chapterTitle}
                          page={page}
                          pageNumber={index + 1}
                          album={album}
                          pageHeight={pageHeight}
                          highlight={highlight}
                          karaoke={karaoke && hasKaraoke}
                          activeSegmentId={pageActiveSegmentId}
                          activeWordIndex={
                            pageActiveSegmentId && activePage === index ? activeWordIndex : null
                          }
                        />
                      </Page>
                    );
                  })}
                </FlipBook>
              </div>
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
        {onToggleKaraoke ? (
          <button
            type="button"
            className={`button button--ghost book-karaoke${karaoke ? " is-active" : ""}`}
            aria-pressed={karaoke}
            onClick={onToggleKaraoke}
            disabled={!hasKaraoke}
            title={
              hasKaraoke
                ? "Resaltar la palabra que suena"
                : "Este capítulo no tiene tiempos por palabra"
            }
          >
            <span className="book-karaoke-dot" aria-hidden="true" />
            Karaoke
          </button>
        ) : null}
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
