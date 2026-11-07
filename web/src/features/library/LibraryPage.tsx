import { AlertTriangle, Plus, RefreshCw, Search } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { errorMessage } from "../../api/client";
import { useBooks, useRescan } from "../../api/queries";
import type { Book } from "../../api/types";
import { BookCard } from "../../components/BookCard";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { IconButton } from "../../components/IconButton";
import { PageHeader } from "../../components/PageHeader";
import { LibrarySkeleton } from "../../components/Skeleton";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { formatDuration, formatPercent, pluralize } from "../../lib/format";

const SORT_OPTIONS = [
  { value: "recent", label: "Recientes" },
  { value: "title", label: "Título" },
  { value: "duration", label: "Duración" },
  { value: "progress", label: "Progreso" },
];

export function LibraryPage() {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("recent");
  const debouncedQuery = useDebouncedValue(query);
  const books = useBooks({ q: debouncedQuery, sort });
  const rescan = useRescan();
  const items = books.data?.items ?? [];
  const continueBook = items.find((book) => book.progress > 0 && book.status === "ready");

  return (
    <div className="page">
      <PageHeader
        eyebrow="Biblioteca"
        title="Tu taller de escucha"
        subtitle="Convierte EPUB en audiolibros y retoma la lectura donde la dejaste."
        actions={
          <>
            <IconButton
              label="Volver a escanear la biblioteca"
              onClick={() => rescan.mutate()}
              disabled={rescan.isPending}
            >
              <RefreshCw size={18} className={rescan.isPending ? "spin" : undefined} />
            </IconButton>
            <Link className="button button--primary" to="/import">
              <Plus size={18} aria-hidden="true" />
              Importar EPUB
            </Link>
          </>
        }
      />

      {continueBook ? <ContinueListening book={continueBook} /> : null}

      <div className="library-toolbar">
        <div className="search-box">
          <Search size={17} aria-hidden="true" />
          <input
            className="input"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar por título o autor"
            aria-label="Buscar libros"
          />
        </div>
        <div className="toolbar-actions">
          <label className="sr-only" htmlFor="sort-books">
            Ordenar biblioteca
          </label>
          <select
            id="sort-books"
            className="select"
            value={sort}
            onChange={(event) => setSort(event.target.value)}
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <span className="mono muted">
            {books.data?.total ?? 0} {pluralize(books.data?.total ?? 0, "libro", "libros")}
          </span>
        </div>
      </div>

      {books.isLoading ? <LibrarySkeleton /> : null}

      {books.isError ? (
        <div className="alert" role="alert">
          <AlertTriangle size={18} />
          <div>
            <strong>No se pudo cargar la biblioteca.</strong>
            <p>{errorMessage(books.error)}</p>
            <button className="link-button" type="button" onClick={() => books.refetch()}>
              Reintentar
            </button>
          </div>
        </div>
      ) : null}

      {!books.isLoading && !books.isError && items.length === 0 ? (
        <EmptyState
          title={query ? "No encontramos ese libro" : "Tu biblioteca está vacía"}
          description={
            query
              ? "Probá con otro título, autor o limpiá la búsqueda."
              : "Arrastrá un EPUB o elegí un archivo para empezar. La conversión se puede pausar y retomar."
          }
          action={
            query ? (
              <Button onClick={() => setQuery("")}>Limpiar búsqueda</Button>
            ) : (
              <Link className="button button--primary" to="/import">
                Elegir EPUB
              </Link>
            )
          }
        />
      ) : null}

      {items.length > 0 ? (
        <div className="book-grid">
          {items.map((book) => (
            <BookCard book={book} key={book.id} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ContinueListening({ book }: { book: Book }) {
  return (
    <section className="continue-strip" aria-label="Continuar escuchando">
      <div>
        <p className="eyebrow">Continuar</p>
        <h2>{book.title}</h2>
        <p>
          {formatPercent(book.progress)} escuchado · {formatDuration(book.duration_ms)}
        </p>
      </div>
      <div className="continue-actions">
        <Link className="button button--primary" to={`/books/${book.id}/read`}>
          Continuar leyendo
        </Link>
        <Link className="button button--ghost" to={`/books/${book.id}/studio`}>
          Ver estudio
        </Link>
      </div>
    </section>
  );
}
