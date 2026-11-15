import { BookOpen, Info, Trash2 } from "lucide-react";
import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";

import type { Book } from "../api/types";

interface BookActionMenuProps {
  book: Book;
  x: number;
  y: number;
  onClose: () => void;
  onDelete?: (book: Book) => void;
}

const MENU_WIDTH = 208;
const MENU_HEIGHT = 172;

export function BookActionMenu({ book, x, y, onClose, onDelete }: BookActionMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);
  const firstItemRef = useRef<HTMLAnchorElement>(null);
  const left = Math.max(8, Math.min(x, window.innerWidth - MENU_WIDTH - 8));
  const top = Math.max(8, Math.min(y, window.innerHeight - MENU_HEIGHT - 8));

  useEffect(() => {
    firstItemRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    const closeWithoutFocus = () => onClose();
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("resize", closeWithoutFocus);
    window.addEventListener("scroll", closeWithoutFocus, true);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("resize", closeWithoutFocus);
      window.removeEventListener("scroll", closeWithoutFocus, true);
    };
  }, [onClose]);

  return createPortal(
    <>
      <div
        className="book-action-backdrop"
        aria-hidden="true"
        onClick={onClose}
        onContextMenu={(event) => {
          event.preventDefault();
          onClose();
        }}
      />
      <div
        ref={menuRef}
        className="book-action-menu"
        role="menu"
        aria-label={`Acciones para ${book.title}`}
        style={{ left, top }}
      >
        <Link
          ref={firstItemRef}
          className="book-action-menu-item"
          role="menuitem"
          to={`/books/${book.id}/read`}
          onClick={onClose}
        >
          <BookOpen size={16} aria-hidden="true" />
          Leer
        </Link>
        <Link
          className="book-action-menu-item"
          role="menuitem"
          to={`/books/${book.id}`}
          onClick={onClose}
        >
          <Info size={16} aria-hidden="true" />
          Ver detalles
        </Link>
        {onDelete ? (
          <>
            <hr className="book-action-menu-separator" />
            <button
              type="button"
              className="book-action-menu-item is-danger"
              role="menuitem"
              onClick={() => {
                onClose();
                onDelete(book);
              }}
            >
              <Trash2 size={16} aria-hidden="true" />
              Eliminar libro
            </button>
          </>
        ) : null}
      </div>
    </>,
    document.body,
  );
}
