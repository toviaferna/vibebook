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
import { useMediaUrl } from "../../hooks/useMediaUrl";
import { formatDuration, formatPercent, pluralize } from "../../lib/format";

const SORT_OPTIONS = [
  { value: "recent", label: "Recientes" },
  { value: "title", label: "Título" },
  { value: "duration", label: "Duración" },
  { value: "progress", label: "Progreso" },
];

type LibraryFilter = "all" | "reading" | "audio" | "no-audio";

const FILTER_OPTIONS: { value: LibraryFilter; label: string }[] = [
  { value: "all", label: "Todos" },
  { value: "reading", label: "Leyendo" },
  { value: "audio", label: "Con audio" },
  { value: "no-audio", label: "Sin audio" },
];

function matchesFilter(book: Book, filter: LibraryFilter): boolean {
  if (filter === "reading") {
    return book.reading_progress > 0;
  }
  if (filter === "audio") {
    return book.status === "ready";
  }
  if (filter === "no-audio") {
    return book.status !== "ready";
  }
  return true;
}

export function LibraryPage() {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("recent");
  const [filter, setFilter] = useState<LibraryFilter>("all");
  const debouncedQuery = useDebouncedValue(query);
  const books = useBooks({ q: debouncedQuery, sort });
  const rescan = useRescan();
  const items = books.data?.items ?? [];
  const filteredItems = items.filter((book) => matchesFilter(book, filter));
  const continueBook =
    items.find((book) => book.reading_progress > 0) ??
    items.find((book) => book.progress > 0 && book.status === "ready");
  const hasActiveFilter = filter !== "all" || query.length > 0;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Biblioteca"
        title="Tu taller de escucha"
        subtitle="Importá EPUB, leelos a tu ritmo y convertí a audiolibro solo cuando quieras."
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

      {continueBook && !hasActiveFilter ? <ContinueBook book={continueBook} /> : null}

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
            {filteredItems.length} {pluralize(filteredItems.length, "libro", "libros")}
          </span>
        </div>
      </div>

      <fieldset className="library-filters">
        <legend className="sr-only">Filtrar biblioteca</legend>
        {FILTER_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            className="library-filter"
            aria-pressed={filter === option.value}
            onClick={() => setFilter(option.value)}
          >
            {option.label}
            {option.value === "reading" && items.some((book) => book.reading_progress > 0)
              ? ` (${items.filter((book) => book.reading_progress > 0).length})`
              : null}
          </button>
        ))}
      </fieldset>

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
              : "Arrastrá un EPUB o elegí un archivo para empezar. No hace falta convertirlo para leerlo."
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

      {!books.isLoading && !books.isError && items.length > 0 && filteredItems.length === 0 ? (
        <EmptyState
          title="No hay libros con este filtro"
          description="Probá con otro filtro o volvé a ver toda la biblioteca."
          action={<Button onClick={() => setFilter("all")}>Ver todos</Button>}
        />
      ) : null}

      {filteredItems.length > 0 ? (
        <div className="book-grid">
          {filteredItems.map((book) => (
            <BookCard book={book} key={book.id} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ContinueBook({ book }: { book: Book }) {
  const reading = book.reading_progress > 0;
  const progress = reading ? book.reading_progress : book.progress;
  const cover = useMediaUrl(book.id, "cover", book.cover_url);
  const chapter =
    reading && book.last_read_chapter_index ? ` · Capítulo ${book.last_read_chapter_index}` : "";

  const initials = book.title
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();

  return (
    <section
      className="continue-strip"
      aria-label={reading ? "Continuar leyendo" : "Continuar escuchando"}
    >
      <div className="continue-cover" aria-hidden="true">
        {cover ? <img src={cover} alt="" /> : <span>{initials || "VB"}</span>}
      </div>
      <div className="continue-copy">
        <p className="eyebrow">Continuar</p>
        <h2>{book.title}</h2>
        <p>
          {formatPercent(progress)} {reading ? "leído" : "escuchado"}
          {chapter}
          {!reading && book.duration_ms ? ` · ${formatDuration(book.duration_ms)}` : null}
        </p>
      </div>
      <div className="continue-actions">
        <Link className="button button--primary" to={`/books/${book.id}/read`}>
          Continuar leyendo
        </Link>
        <Link className="button button--ghost" to={`/books/${book.id}`}>
          Ver detalle
        </Link>
      </div>
    </section>
  );
}
