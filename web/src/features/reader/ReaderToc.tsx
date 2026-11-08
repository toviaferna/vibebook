import type { ManifestChapter, TocNode } from "../../api/types";
import { formatDuration } from "../../lib/format";
import { chapterDisplayTitle } from "./chapterTitle";

interface ReaderTocProps {
  chapters: ManifestChapter[];
  toc?: TocNode[];
  currentIndex: number;
  onSelect: (index: number) => void;
}

function ChapterItem({
  chapter,
  currentIndex,
  onSelect,
}: {
  chapter: ManifestChapter;
  currentIndex: number;
  onSelect: (index: number) => void;
}) {
  return (
    <li>
      <button
        type="button"
        className={`reader-toc-item${chapter.index === currentIndex ? " is-active" : ""}`}
        onClick={() => onSelect(chapter.index)}
        aria-current={chapter.index === currentIndex ? "page" : undefined}
      >
        <span className="reader-toc-number">{String(chapter.index).padStart(2, "0")}</span>
        <span className="reader-toc-title">{chapterDisplayTitle(chapter)}</span>
        <span className="reader-toc-duration">{formatDuration(chapter.duration_ms)}</span>
      </button>
    </li>
  );
}

function TocItems({
  nodes,
  chapters,
  currentIndex,
  onSelect,
}: {
  nodes: TocNode[];
  chapters: Map<number, ManifestChapter>;
  currentIndex: number;
  onSelect: (index: number) => void;
}) {
  return (
    <>
      {nodes.map((node) => {
        const key = `${node.kind}-${node.chapter_index ?? "part"}-${node.title}`;
        if (node.children.length > 0) {
          return (
            <li className="reader-toc-group" key={key}>
              <p className="reader-toc-part">{node.title}</p>
              <ol className="reader-toc-list reader-toc-list--nested">
                <TocItems
                  nodes={node.children}
                  chapters={chapters}
                  currentIndex={currentIndex}
                  onSelect={onSelect}
                />
              </ol>
            </li>
          );
        }
        const chapter = node.chapter_index === null ? undefined : chapters.get(node.chapter_index);
        if (!chapter) {
          return null;
        }
        return (
          <ChapterItem
            key={key}
            chapter={chapter}
            currentIndex={currentIndex}
            onSelect={onSelect}
          />
        );
      })}
    </>
  );
}

export function ReaderToc({ chapters, toc, currentIndex, onSelect }: ReaderTocProps) {
  const chaptersById = new Map(chapters.map((chapter) => [chapter.index, chapter]));
  const nodes = toc && toc.length > 0 ? toc : null;

  return (
    <nav className="reader-toc" aria-label="Índice del libro">
      <p className="eyebrow">Índice</p>
      <ol className="reader-toc-list">
        {nodes ? (
          <TocItems
            nodes={nodes}
            chapters={chaptersById}
            currentIndex={currentIndex}
            onSelect={onSelect}
          />
        ) : (
          chapters.map((chapter) => (
            <ChapterItem
              key={chapter.index}
              chapter={chapter}
              currentIndex={currentIndex}
              onSelect={onSelect}
            />
          ))
        )}
      </ol>
    </nav>
  );
}
