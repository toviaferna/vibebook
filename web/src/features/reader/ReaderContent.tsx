import { forwardRef, type MouseEvent, useMemo } from "react";

import { apiUrl } from "../../api/client";
import type {
  ChapterTiming,
  ManifestChapter,
  ManifestImage,
  ManifestSegment,
} from "../../api/types";
import type { AlignedSegment } from "./alignment";
import { chapterDisplayTitle } from "./chapterTitle";

interface ReaderContentProps {
  chapter: ManifestChapter;
  timing: ChapterTiming | null;
  alignments: Map<string, AlignedSegment>;
  activeSegmentId: string | null;
  activeWordIndex: number | null;
  onSeek: (ms: number) => void;
  bookId?: string;
  images?: ManifestImage[];
}

function groupParagraphs(segments: ManifestSegment[]): ManifestSegment[][] {
  const groups = new Map<number, ManifestSegment[]>();
  for (const segment of segments) {
    const group = groups.get(segment.paragraph_index) ?? [];
    group.push(segment);
    groups.set(segment.paragraph_index, group);
  }
  return [...groups.values()];
}

export const ReaderContent = forwardRef<HTMLElement, ReaderContentProps>(function ReaderContent(
  { chapter, timing, alignments, activeSegmentId, activeWordIndex, onSeek, bookId, images = [] },
  ref,
) {
  const paragraphs = useMemo(() => groupParagraphs(chapter.segments), [chapter.segments]);
  const chapterImages = useMemo(
    () => images.filter((image) => image.chapter_index === chapter.index),
    [chapter.index, images],
  );
  const timingById = useMemo(
    () => new Map((timing?.segments ?? []).map((segment) => [segment.id, segment])),
    [timing],
  );
  const renderedImages = new Set<string>();

  const renderFigure = (image: ManifestImage) => {
    if (renderedImages.has(image.id)) {
      return null;
    }
    renderedImages.add(image.id);
    return (
      <figure className="reader-figure" key={image.id}>
        {bookId ? (
          <img
            src={apiUrl(`/books/${bookId}/images/${image.id}`)}
            alt={image.alt}
            loading="lazy"
            decoding="async"
          />
        ) : null}
        {image.caption ? <figcaption>{image.caption}</figcaption> : null}
      </figure>
    );
  };

  const handleSegmentSeek = (segment: ManifestSegment, event: MouseEvent) => {
    if (window.getSelection()?.toString()) {
      return;
    }
    const wordTarget = (event.target as HTMLElement).closest<HTMLElement>("[data-word-start]");
    const target = wordTarget
      ? Number(wordTarget.dataset.wordStart)
      : timingById.get(segment.id)?.start_ms;
    if (target !== undefined) {
      event.stopPropagation();
      onSeek(target);
    }
  };

  return (
    <article className="reader-article" lang="es" ref={ref}>
      <header className="reader-chapter-head">
        <p className="eyebrow">Capítulo {String(chapter.index).padStart(2, "0")}</p>
        <h1>{chapterDisplayTitle(chapter)}</h1>
      </header>

      {chapterImages
        .filter((image) => image.paragraph_index === 0 && image.position === "before")
        .map(renderFigure)}

      {paragraphs.map((paragraph) => {
        const paragraphIndex = paragraph[0]?.paragraph_index ?? 0;
        return (
          <div key={paragraph[0]?.id ?? "empty"}>
            {chapterImages
              .filter(
                (image) => image.paragraph_index === paragraphIndex && image.position === "before",
              )
              .map(renderFigure)}
            <p className="reader-paragraph">
              {paragraph.map((segment, segmentIndex) => {
                const aligned = alignments.get(segment.id);
                const isActive = segment.id === activeSegmentId;
                return (
                  <span key={segment.id}>
                    {/* Click-to-seek is an enhancement; keyboard users use the player controls. */}
                    {/* biome-ignore lint/a11y/noStaticElementInteractions: text click seeks audio */}
                    {/* biome-ignore lint/a11y/useKeyWithClickEvents: player controls cover keyboard */}
                    <span
                      className={`reader-segment${isActive ? " is-active" : ""}`}
                      data-segment-id={segment.id}
                      aria-current={isActive ? "true" : undefined}
                      onClick={(event) => handleSegmentSeek(segment, event)}
                    >
                      {aligned && aligned.words.length > 0
                        ? aligned.words.map((word, wordIndex) => (
                            <span
                              key={`${segment.id}-${word.startMs}`}
                              className={`reader-word${
                                isActive && wordIndex === activeWordIndex ? " is-active" : ""
                              }`}
                              data-word-index={wordIndex}
                              data-word-start={word.startMs}
                            >
                              {word.text}
                              {wordIndex < aligned.words.length - 1 ? " " : ""}
                            </span>
                          ))
                        : segment.text}
                    </span>
                    {segmentIndex < paragraph.length - 1 ? " " : null}
                  </span>
                );
              })}
            </p>
            {chapterImages
              .filter(
                (image) => image.paragraph_index === paragraphIndex && image.position !== "before",
              )
              .map(renderFigure)}
          </div>
        );
      })}

      {chapterImages.map(renderFigure)}
    </article>
  );
});
