import { Link } from "react-router-dom";

import { apiUrl } from "../api/client";
import type { Book } from "../api/types";
import { formatDuration, formatPercent } from "../lib/format";
import { ProgressBar } from "./ProgressBar";
import { StatusChip } from "./StatusChip";

export function BookCard({ book }: { book: Book }) {
  const initials = book.title
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
  const reading = book.reading_progress > 0;
  const progress = reading ? book.reading_progress : book.progress;
  const progressLabel = reading ? "leído" : "escuchado";

  return (
    <Link className="book-card" to={`/books/${book.id}`}>
      <div className="book-cover">
        {book.cover_url ? (
          <img src={apiUrl(book.cover_url)} alt={`Portada de ${book.title}`} loading="lazy" />
        ) : (
          <div className="cover-placeholder" aria-hidden="true">
            <span className="cover-placeholder-mark">VB · {initials || "LIBRO"}</span>
            <strong>{book.title}</strong>
            <span className="cover-placeholder-author">{book.author}</span>
          </div>
        )}
      </div>
      <div className="book-meta">
        <div>
          <h2 className="book-title">{book.title}</h2>
          <p className="book-author">{book.author}</p>
        </div>
        <div className="book-bottom">
          <StatusChip status={book.status} />
          <span className="mono muted">{formatDuration(book.duration_ms)}</span>
        </div>
        {progress > 0 ? (
          <div className="book-progress">
            <ProgressBar value={progress} label={`Progreso de ${book.title}`} />
            <span className="mono muted">
              {formatPercent(progress)} {progressLabel}
            </span>
          </div>
        ) : null}
      </div>
    </Link>
  );
}
