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

  return (
    <Link className="book-card" to={`/books/${book.id}`} aria-label={`Abrir ${book.title}`}>
      <div className="book-cover">
        {book.cover_url ? (
          <img src={apiUrl(book.cover_url)} alt={`Portada de ${book.title}`} loading="lazy" />
        ) : (
          <div className="cover-placeholder" aria-hidden="true">
            {initials || "VB"}
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
        {book.progress > 0 ? (
          <div className="book-progress">
            <ProgressBar value={book.progress} label={`Progreso de ${book.title}`} />
            <span className="mono muted">{formatPercent(book.progress)} escuchado</span>
          </div>
        ) : null}
      </div>
    </Link>
  );
}
