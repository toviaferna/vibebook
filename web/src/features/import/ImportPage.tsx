import { AlertTriangle, FileText, Upload } from "lucide-react";
import { type DragEvent, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { apiUrl, errorMessage } from "../../api/client";
import { useImportBook } from "../../api/queries";
import type { Book } from "../../api/types";
import { Button } from "../../components/Button";
import { PageHeader } from "../../components/PageHeader";
import { formatDuration } from "../../lib/format";

const MAX_BYTES = 200 * 1024 * 1024;

export function ImportPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [imported, setImported] = useState<Book | null>(null);
  const mutation = useImportBook();

  const chooseFile = () => inputRef.current?.click();

  const handleFile = (file: File | undefined) => {
    setLocalError(null);
    if (!file) {
      return;
    }
    if (!file.name.toLowerCase().endsWith(".epub")) {
      setLocalError("El archivo debe tener extensión .epub.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setLocalError("El EPUB supera el límite de 200 MB.");
      return;
    }
    mutation.mutate(file, {
      onSuccess: (book) => setImported(book),
    });
  };

  const onDrop = (event: DragEvent<HTMLFieldSetElement>) => {
    event.preventDefault();
    setDragging(false);
    handleFile(event.dataTransfer.files[0]);
  };

  const error = localError ?? (mutation.isError ? errorMessage(mutation.error) : null);

  return (
    <div className="page page--narrow">
      <PageHeader
        eyebrow="Importar"
        title="Traé un libro al taller"
        subtitle="El EPUB se copia a tu biblioteca local. Después elegís la voz y la velocidad."
      />

      {!imported ? (
        <fieldset
          className={`dropzone${dragging ? " is-dragging" : ""}`}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <legend className="sr-only">Zona para importar un EPUB</legend>
          <input
            ref={inputRef}
            type="file"
            accept=".epub,application/epub+zip"
            onChange={(event) => handleFile(event.target.files?.[0])}
            aria-label="Seleccionar EPUB"
          />
          <div className="empty-mark" aria-hidden="true">
            <Upload size={28} strokeWidth={1.5} />
          </div>
          <h2>Arrastrá el EPUB acá</h2>
          <p>o elegí un archivo desde tu computadora. Máximo 200 MB, sin DRM.</p>
          <Button variant="primary" onClick={chooseFile} loading={mutation.isPending}>
            {mutation.isPending ? "Importando…" : "Elegir EPUB"}
          </Button>
          <p className="hint">
            El libro queda en la biblioteca local; no se sube a ningún servicio.
          </p>
        </fieldset>
      ) : (
        <section className="panel" aria-label="Libro importado">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Importado</p>
              <h2>{imported.title}</h2>
              <p className="muted">{imported.author}</p>
            </div>
            <span className="status-chip status-chip--imported">Importado</span>
          </div>
          <div className="panel-body">
            <div className="import-summary">
              <div className="book-cover">
                {imported.cover_url ? (
                  <img src={apiUrl(imported.cover_url)} alt={`Portada de ${imported.title}`} />
                ) : (
                  <div className="cover-placeholder" aria-hidden="true">
                    <FileText size={28} />
                  </div>
                )}
              </div>
              <div>
                <p className="page-subtitle">
                  El texto está listo. El siguiente paso es elegir cómo va a sonar.
                </p>
                <div className="summary-facts">
                  <div className="fact">
                    <strong>{imported.chapter_count}</strong>
                    <span>Capítulos</span>
                  </div>
                  <div className="fact">
                    <strong>{formatDuration(imported.duration_ms)}</strong>
                    <span>Audio estimado</span>
                  </div>
                  <div className="fact">
                    <strong>{imported.language.toUpperCase()}</strong>
                    <span>Idioma</span>
                  </div>
                </div>
                <div className="continue-actions" style={{ marginTop: "var(--space-5)" }}>
                  <Link className="button button--primary" to={`/books/${imported.id}/studio`}>
                    Preparar audiolibro
                  </Link>
                  <Link className="button button--ghost" to="/">
                    Volver a la biblioteca
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {error ? (
        <div className="alert" role="alert" style={{ marginTop: "var(--space-5)" }}>
          <AlertTriangle size={18} />
          <div>
            <strong>No se pudo importar el libro.</strong>
            <p>{error}</p>
            <button className="link-button" type="button" onClick={() => setLocalError(null)}>
              Intentar de nuevo
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
