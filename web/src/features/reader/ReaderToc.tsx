import type { ManifestChapter } from "../../api/types";
import { formatDuration } from "../../lib/format";

interface ReaderTocProps {
  chapters: ManifestChapter[];
  currentIndex: number;
  onSelect: (index: number) => void;
}

export function ReaderToc({ chapters, currentIndex, onSelect }: ReaderTocProps) {
  return (
    <nav className="reader-toc" aria-label="Índice del libro">
      <p className="eyebrow">Índice</p>
      <ol className="reader-toc-list">
        {chapters.map((chapter) => (
          <li key={chapter.index}>
            <button
              type="button"
              className={`reader-toc-item${chapter.index === currentIndex ? " is-active" : ""}`}
              onClick={() => onSelect(chapter.index)}
              aria-current={chapter.index === currentIndex ? "page" : undefined}
            >
              <span className="reader-toc-number">{String(chapter.index).padStart(2, "0")}</span>
              <span className="reader-toc-title">{chapter.title}</span>
              <span className="reader-toc-duration">{formatDuration(chapter.duration_ms)}</span>
            </button>
          </li>
        ))}
      </ol>
    </nav>
  );
}
