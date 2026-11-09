import ePub, { type Book as EpubBook, type Location, type Rendition } from "epubjs";
import { useEffect, useRef, useState } from "react";

import { deleteBook, listBooks, type StoredBook, saveBook, updateBookCfi } from "./storage";

export function MobileReaderApp() {
  const [books, setBooks] = useState<StoredBook[]>([]);
  const [active, setActive] = useState<StoredBook | null>(null);
  const [opening, setOpening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const readerRef = useRef<HTMLDivElement>(null);
  const bookRef = useRef<EpubBook | null>(null);
  const renditionRef = useRef<Rendition | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void listBooks()
      .then(setBooks)
      .catch((reason: unknown) => setError(messageOf(reason)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    return () => {
      renditionRef.current?.destroy();
      bookRef.current?.destroy();
    };
  }, []);

  const importBook = async (file: File) => {
    setError(null);
    if (!file.name.toLowerCase().endsWith(".epub")) {
      setError("Elegí un archivo EPUB.");
      return;
    }
    try {
      const bytes = await file.arrayBuffer();
      const stored: StoredBook = {
        id: `${file.name}-${file.size}-${file.lastModified}`,
        title: file.name.replace(/\.epub$/i, ""),
        bytes,
        cfi: null,
        updatedAt: new Date().toISOString(),
      };
      await saveBook(stored);
      setBooks(await listBooks());
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  const openBook = async (stored: StoredBook) => {
    setError(null);
    setOpening(true);
    setActive(stored);
    try {
      await new Promise((resolve) => window.setTimeout(resolve, 0));
      if (!readerRef.current) {
        throw new Error("El lector no está listo.");
      }
      renditionRef.current?.destroy();
      bookRef.current?.destroy();
      const book = ePub(stored.bytes);
      const rendition = book.renderTo(readerRef.current, {
        width: "100%",
        height: "100%",
        flow: "paginated",
        spread: "none",
      });
      bookRef.current = book;
      renditionRef.current = rendition;
      rendition.on("relocated", (location: Location) => {
        const cfi = location.start.cfi;
        setActive((current) => (current ? { ...current, cfi } : current));
        void updateBookCfi(stored.id, cfi);
      });
      await rendition.display(stored.cfi ?? undefined);
      setBooks(await listBooks());
    } catch (reason) {
      setError(messageOf(reason));
      setActive(null);
    } finally {
      setOpening(false);
    }
  };

  const closeBook = () => {
    renditionRef.current?.destroy();
    bookRef.current?.destroy();
    renditionRef.current = null;
    bookRef.current = null;
    setActive(null);
  };

  const removeBook = async (book: StoredBook) => {
    await deleteBook(book.id);
    setBooks(await listBooks());
    if (active?.id === book.id) {
      closeBook();
    }
  };

  if (active) {
    return (
      <div className="mobile-reader">
        <header className="mobile-reader-head">
          <button type="button" className="mobile-icon" onClick={closeBook} aria-label="Volver">
            ←
          </button>
          <strong>{active.title}</strong>
          <div className="mobile-reader-nav">
            <button
              type="button"
              className="mobile-icon"
              onClick={() => void renditionRef.current?.prev()}
              aria-label="Página anterior"
            >
              ‹
            </button>
            <button
              type="button"
              className="mobile-icon"
              onClick={() => void renditionRef.current?.next()}
              aria-label="Página siguiente"
            >
              ›
            </button>
          </div>
        </header>
        {error ? (
          <p className="mobile-error" role="alert">
            {error}
          </p>
        ) : null}
        {opening ? <p className="mobile-status">Abriendo libro…</p> : null}
        <div className="mobile-reader-page" ref={readerRef} />
      </div>
    );
  }

  return (
    <div className="mobile-app">
      <header className="mobile-hero">
        <p className="mobile-kicker">Lector Android · modo local</p>
        <h1>Vibebook</h1>
        <p>Tus EPUB, en el bolsillo. Sin cuenta, sin nube y sin conversión.</p>
        <button type="button" className="mobile-primary" onClick={() => fileRef.current?.click()}>
          Importar EPUB
        </button>
        <input
          ref={fileRef}
          className="sr-only"
          type="file"
          accept=".epub,application/epub+zip"
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (file) void importBook(file);
          }}
        />
      </header>

      {error ? (
        <p className="mobile-error" role="alert">
          {error}
        </p>
      ) : null}

      <section className="mobile-shelf" aria-label="Biblioteca">
        <div className="mobile-shelf-head">
          <h2>Biblioteca</h2>
          <span>
            {books.length} {books.length === 1 ? "libro" : "libros"}
          </span>
        </div>
        {loading ? <p className="mobile-status">Cargando…</p> : null}
        {!loading && books.length === 0 ? (
          <div className="mobile-empty">
            <strong>Tu estante está vacío.</strong>
            <p>Importá un EPUB para leerlo sin convertir nada.</p>
          </div>
        ) : null}
        <ul className="mobile-books">
          {books.map((book) => (
            <li key={book.id}>
              <button type="button" className="mobile-book" onClick={() => void openBook(book)}>
                <span className="mobile-book-cover" aria-hidden="true">
                  {book.title.slice(0, 2).toUpperCase()}
                </span>
                <span className="mobile-book-copy">
                  <strong>{book.title}</strong>
                  <small>{book.cfi ? "Continuar" : "Leer"}</small>
                </span>
              </button>
              <button
                type="button"
                className="mobile-delete"
                onClick={() => void removeBook(book)}
                aria-label={`Eliminar ${book.title}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      </section>

      <p className="mobile-foot">
        Android lector-only: no convierte, no usa Python y no requiere internet.
      </p>
    </div>
  );
}

function messageOf(reason: unknown): string {
  return reason instanceof Error ? reason.message : "Algo salió mal.";
}
