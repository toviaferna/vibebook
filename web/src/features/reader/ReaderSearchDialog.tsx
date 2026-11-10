import * as Dialog from "@radix-ui/react-dialog";
import { Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { errorMessage } from "../../api/client";
import { useBookSearch } from "../../api/queries";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { formatTime } from "../../lib/format";

interface ReaderSearchDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  bookId: string;
  onSelect: (chapterIndex: number, positionMs: number, charOffset: number) => void;
}

export function ReaderSearchDialog({
  open,
  onOpenChange,
  bookId,
  onSelect,
}: ReaderSearchDialogProps) {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const debouncedQuery = useDebouncedValue(query, 250);
  const search = useBookSearch(bookId, debouncedQuery);
  const results = search.data?.items ?? [];
  const tooShort = query.trim().length < 2;

  useEffect(() => {
    if (open) {
      setQuery("");
    }
  }, [open]);

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content
          className="dialog-content reader-search-dialog"
          aria-describedby={undefined}
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            inputRef.current?.focus();
          }}
        >
          <div className="reader-search-head">
            <div>
              <p className="eyebrow">Lector</p>
              <Dialog.Title asChild>
                <h2>Buscar en el libro</h2>
              </Dialog.Title>
            </div>
            <Dialog.Close asChild>
              <button type="button" className="icon-button" aria-label="Cerrar búsqueda">
                <X size={18} />
              </button>
            </Dialog.Close>
          </div>

          <div className="reader-search-box">
            <Search size={17} aria-hidden="true" />
            <input
              ref={inputRef}
              className="input"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Palabra o frase"
              aria-label="Texto a buscar"
            />
          </div>

          {tooShort ? (
            <p className="hint">Escribí al menos 2 letras para buscar.</p>
          ) : search.isFetching ? (
            <p className="hint" role="status">
              Buscando…
            </p>
          ) : search.isError ? (
            <div className="alert" role="alert">
              <span>{errorMessage(search.error)}</span>
            </div>
          ) : results.length === 0 ? (
            <p className="hint">No encontramos esa frase en este libro.</p>
          ) : (
            <ul className="search-results" aria-label="Resultados de búsqueda">
              {results.map((result) => (
                <li key={`${result.segment_id}-${result.offset}`}>
                  <button
                    type="button"
                    className="search-result"
                    onClick={() => {
                      onSelect(result.chapter_index, result.position_ms, result.char_offset);
                      onOpenChange(false);
                    }}
                  >
                    <span className="search-result-meta">
                      Cap. {result.chapter_index} · {result.chapter_title}
                      <span className="mono muted">{formatTime(result.position_ms)}</span>
                    </span>
                    <span className="search-result-excerpt">{result.excerpt}</span>
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
