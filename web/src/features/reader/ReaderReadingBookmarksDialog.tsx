import * as Dialog from "@radix-ui/react-dialog";
import { Bookmark as BookmarkIcon, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";

import { errorMessage } from "../../api/client";
import {
  useCreateReadingBookmark,
  useDeleteReadingBookmark,
  useReadingBookmarks,
} from "../../api/queries";
import type { ManifestChapter, ReadingBookmark } from "../../api/types";
import { Button } from "../../components/Button";
import type { BookPageState } from "./book/BookReader";

interface ReaderReadingBookmarksDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  bookId: string;
  chapters: ManifestChapter[];
  currentChapter: number;
  page: BookPageState;
  onSelect: (bookmark: ReadingBookmark) => void;
}

export function ReaderReadingBookmarksDialog({
  open,
  onOpenChange,
  bookId,
  chapters,
  currentChapter,
  page,
  onSelect,
}: ReaderReadingBookmarksDialogProps) {
  const [note, setNote] = useState("");
  const bookmarks = useReadingBookmarks(bookId);
  const create = useCreateReadingBookmark(bookId);
  const remove = useDeleteReadingBookmark(bookId);
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
              <p className="eyebrow">Libro</p>
              <Dialog.Title asChild>
                <h2>Marcadores de lectura</h2>
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
              Guardar en página {page.pageIndex + 1} · {chapterTitle}
            </p>
            <div className="bookmark-form">
              <input
                className="input"
                value={note}
                maxLength={500}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Nota opcional"
                aria-label="Nota del marcador de lectura"
              />
              <Button
                variant="primary"
                onClick={() => {
                  create.mutate(
                    {
                      chapter_index: currentChapter,
                      char_offset: page.charOffset,
                      page_index: page.pageIndex,
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
            <p className="hint">Todavía no hay marcadores de lectura.</p>
          ) : (
            <ul className="bookmark-list" aria-label="Marcadores de lectura del libro">
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
                      Cap. {bookmark.chapter_index} · Página {bookmark.page_index + 1}
                    </span>
                    <span className="bookmark-note">{bookmark.note || "Sin nota"}</span>
                  </button>
                  <button
                    type="button"
                    className="icon-button"
                    onClick={() => remove.mutate(bookmark.id)}
                    aria-label={`Eliminar marcador de la página ${bookmark.page_index + 1}`}
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
