import * as Dialog from "@radix-ui/react-dialog";
import { Bookmark as BookmarkIcon, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";

import { errorMessage } from "../../api/client";
import { useBookmarks, useCreateBookmark, useDeleteBookmark } from "../../api/queries";
import type { Bookmark, ManifestChapter } from "../../api/types";
import { Button } from "../../components/Button";
import { formatTime } from "../../lib/format";

interface ReaderBookmarksDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  bookId: string;
  chapters: ManifestChapter[];
  currentChapter: number;
  currentTimeMs: number;
  onSelect: (bookmark: Bookmark) => void;
}

export function ReaderBookmarksDialog({
  open,
  onOpenChange,
  bookId,
  chapters,
  currentChapter,
  currentTimeMs,
  onSelect,
}: ReaderBookmarksDialogProps) {
  const [note, setNote] = useState("");
  const bookmarks = useBookmarks(bookId);
  const create = useCreateBookmark(bookId);
  const remove = useDeleteBookmark(bookId);
  const items = bookmarks.data?.items ?? [];
  const chapterTitle =
    chapters.find((chapter) => chapter.index === currentChapter)?.title ?? "Sin capítulo";

  useEffect(() => {
    if (open) {
      setNote("");
    }
  }, [open]);

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content
          className="dialog-content reader-bookmarks-dialog"
          aria-describedby={undefined}
        >
          <div className="reader-search-head">
            <div>
              <p className="eyebrow">Lector</p>
              <Dialog.Title asChild>
                <h2>Marcadores</h2>
              </Dialog.Title>
            </div>
            <Dialog.Close asChild>
              <button type="button" className="icon-button" aria-label="Cerrar marcadores">
                <X size={18} />
              </button>
            </Dialog.Close>
          </div>

          <div className="bookmark-create">
            <p className="hint">
              Agregar en {formatTime(currentTimeMs)} · {chapterTitle}
            </p>
            <div className="bookmark-form">
              <input
                className="input"
                value={note}
                maxLength={500}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Nota opcional"
                aria-label="Nota del marcador"
              />
              <Button
                variant="primary"
                onClick={() => {
                  create.mutate(
                    {
                      chapter_index: currentChapter,
                      position_ms: Math.round(currentTimeMs),
                      note: note.trim() || null,
                    },
                    { onSuccess: () => setNote("") },
                  );
                }}
                loading={create.isPending}
              >
                <BookmarkIcon size={16} />
                Guardar
              </Button>
            </div>
            {create.isError ? (
              <div className="alert" role="alert">
                <span>{errorMessage(create.error)}</span>
              </div>
            ) : null}
          </div>

          {bookmarks.isLoading ? (
            <p className="hint" role="status">
              Cargando marcadores…
            </p>
          ) : bookmarks.isError ? (
            <div className="alert" role="alert">
              <span>{errorMessage(bookmarks.error)}</span>
            </div>
          ) : items.length === 0 ? (
            <p className="hint">Todavía no hay marcadores en este libro.</p>
          ) : (
            <ul className="bookmark-list" aria-label="Marcadores del libro">
              {items.map((bookmark) => (
                <li className="bookmark-item" key={bookmark.id}>
                  <button
                    type="button"
                    className="bookmark-open"
                    onClick={() => {
                      onSelect(bookmark);
                      onOpenChange(false);
                    }}
                  >
                    <span className="search-result-meta">
                      Cap. {bookmark.chapter_index} · {formatTime(bookmark.position_ms)}
                    </span>
                    <span className="bookmark-note">{bookmark.note || "Sin nota"}</span>
                  </button>
                  <button
                    type="button"
                    className="icon-button"
                    onClick={() => remove.mutate(bookmark.id)}
                    aria-label={`Eliminar marcador de ${formatTime(bookmark.position_ms)}`}
                    title="Eliminar marcador"
                  >
                    <Trash2 size={16} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
