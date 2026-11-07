import { forwardRef, type MouseEvent, useMemo } from "react";

import type { ChapterTiming, ManifestChapter, ManifestSegment } from "../../api/types";
import type { AlignedSegment } from "./alignment";

interface ReaderContentProps {
  chapter: ManifestChapter;
  timing: ChapterTiming | null;
  alignments: Map<string, AlignedSegment>;
  activeSegmentId: string | null;
  activeWordIndex: number | null;
  onSeek: (ms: number) => void;
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
  { chapter, timing, alignments, activeSegmentId, activeWordIndex, onSeek },
  ref,
) {
  const paragraphs = useMemo(() => groupParagraphs(chapter.segments), [chapter.segments]);
  const timingById = useMemo(
    () => new Map((timing?.segments ?? []).map((segment) => [segment.id, segment])),
    [timing],
  );

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
        <h1>{chapter.title}</h1>
      </header>

      {paragraphs.map((paragraph) => (
        <p className="reader-paragraph" key={paragraph[0]?.id ?? "empty"}>
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
      ))}
    </article>
  );
});
