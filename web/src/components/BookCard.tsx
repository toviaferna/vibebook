import { MoreHorizontal } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { Link } from "react-router-dom";

import type { Book } from "../api/types";
import { useMediaUrl } from "../hooks/useMediaUrl";
import { formatDuration, formatPercent } from "../lib/format";
import { BookActionMenu } from "./BookActionMenu";
import { ProgressBar } from "./ProgressBar";
import { StatusChip } from "./StatusChip";

export function BookCard({ book, onDelete }: { book: Book; onDelete?: (book: Book) => void }) {
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
  const cover = useMediaUrl(book.id, "cover", book.cover_url);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [menu, setMenu] = useState<{ x: number; y: number } | null>(null);

  const closeMenu = useCallback(() => {
    setMenu(null);
    requestAnimationFrame(() => triggerRef.current?.focus());
  }, []);

  const openMenu = useCallback((x: number, y: number) => {
    setMenu({ x, y });
  }, []);

  const openFromButton = () => {
    const rect = triggerRef.current?.getBoundingClientRect();
    if (rect) {
      openMenu(rect.right - 8, rect.bottom + 6);
    }
  };

  return (
    <div className="book-card-shell">
      <Link
        className="book-card"
        to={`/books/${book.id}`}
        onContextMenu={(event) => {
          event.preventDefault();
          openMenu(event.clientX, event.clientY);
        }}
      >
        <div className="book-cover">
          {cover ? (
            <img src={cover} alt={`Portada de ${book.title}`} loading="lazy" />
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
      <button
        ref={triggerRef}
        type="button"
        className="book-card-menu-trigger"
        aria-label={`Acciones para ${book.title}`}
        aria-haspopup="menu"
        aria-expanded={menu !== null}
        onClick={openFromButton}
        onContextMenu={(event) => {
          event.preventDefault();
          openMenu(event.clientX, event.clientY);
        }}
      >
        <MoreHorizontal size={17} aria-hidden="true" />
      </button>
      {menu ? (
        <BookActionMenu book={book} x={menu.x} y={menu.y} onClose={closeMenu} onDelete={onDelete} />
      ) : null}
    </div>
  );
}
