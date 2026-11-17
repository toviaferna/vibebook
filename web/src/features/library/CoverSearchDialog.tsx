import * as Dialog from "@radix-ui/react-dialog";
import { AlertTriangle, Image, Search, X } from "lucide-react";
import { useEffect, useState } from "react";

import { apiUrl, errorMessage } from "../../api/client";
import { useApplyBookCover, useSearchBookCovers } from "../../api/queries";
import type { Book } from "../../api/types";
import { Button } from "../../components/Button";

interface CoverSearchDialogProps {
  book: Book | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CoverSearchDialog({ book, open, onOpenChange }: CoverSearchDialogProps) {
  const [query, setQuery] = useState("");
  const search = useSearchBookCovers();
  const apply = useApplyBookCover(book?.id ?? "");
  const results = search.data?.items ?? [];
  const resetSearch = search.reset;
  const resetApply = apply.reset;
  const runSearch = search.mutate;

  useEffect(() => {
    if (!open || !book) {
      return;
    }
    setQuery("");
    resetApply();
    runSearch({ bookId: book.id, query: "" });
  }, [book, open, resetApply, runSearch]);

  useEffect(() => {
    if (!open) {
      resetSearch();
    }
  }, [open, resetSearch]);

  if (!book) {
    return null;
  }

  const searchError = search.isError ? errorMessage(search.error) : null;
  const applyError = apply.isError ? errorMessage(apply.error) : null;

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content cover-search" aria-describedby={undefined}>
          <div className="cover-search-head">
            <div>
              <p className="eyebrow">Portada</p>
              <Dialog.Title asChild>
                <h2>Buscar una portada</h2>
              </Dialog.Title>
            </div>
            <Dialog.Close asChild>
              <button type="button" className="icon-button" aria-label="Cerrar búsqueda de portada">
                <X size={18} />
              </button>
            </Dialog.Close>
          </div>

          <p className="hint">
            Buscamos por título y autor en Open Library y Google Books. Revisá la edición antes de
            elegir: una portada parecida no siempre es la misma obra.
          </p>

          <form
            className="cover-search-form"
            onSubmit={(event) => {
              event.preventDefault();
              runSearch({ bookId: book.id, query });
            }}
          >
            <label className="sr-only" htmlFor="cover-search-query">
              Título, autor o ISBN
            </label>
            <input
              id="cover-search-query"
              className="input"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Título, autor o ISBN"
            />
            <Button type="submit" loading={search.isPending}>
              <Search size={16} />
              Buscar
            </Button>
          </form>

          {searchError ? (
            <div className="alert" role="alert">
              <AlertTriangle size={18} />
              <span>{searchError}</span>
            </div>
          ) : null}
          {applyError ? (
            <div className="alert" role="alert">
              <AlertTriangle size={18} />
              <span>{applyError}</span>
            </div>
          ) : null}

          {search.isPending ? (
            <div className="cover-results" role="status" aria-label="Buscando portadas">
              {[0, 1, 2].map((index) => (
                <div className="cover-result cover-result--skeleton" key={index}>
                  <span className="skeleton" />
                </div>
              ))}
            </div>
          ) : results.length > 0 ? (
            <section className="cover-results" aria-label="Portadas encontradas">
              {results.map((candidate) => (
                <button
                  type="button"
                  className="cover-result"
                  key={`${candidate.source}-${candidate.cover_url}`}
                  disabled={apply.isPending}
                  onClick={() => {
                    apply.mutate(candidate.cover_url, {
                      onSuccess: () => onOpenChange(false),
                    });
                  }}
                >
                  <img
                    src={apiUrl(candidate.preview_url)}
                    alt={`Portada de ${candidate.title}`}
                    loading="lazy"
                    decoding="async"
                  />
                  <span className="cover-result-meta">
                    <strong>{candidate.title}</strong>
                    <span>{candidate.author}</span>
                    <span className="mono">
                      {candidate.source}
                      {candidate.year ? ` · ${candidate.year}` : ""}
                    </span>
                  </span>
                </button>
              ))}
            </section>
          ) : search.isSuccess ? (
            <div className="cover-search-empty">
              <Image size={24} aria-hidden="true" />
              <strong>No encontramos una coincidencia clara.</strong>
              <span>Probá con el título completo, el autor o el ISBN de tu edición.</span>
            </div>
          ) : null}

          <div className="dialog-actions">
            <Dialog.Close asChild>
              <Button variant="ghost">Cerrar</Button>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
