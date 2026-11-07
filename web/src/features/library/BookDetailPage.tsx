import * as Dialog from "@radix-ui/react-dialog";
import { AlertTriangle, ArrowLeft, Download, Headphones, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { apiUrl, errorMessage } from "../../api/client";
import { useBook, useDeleteBook } from "../../api/queries";
import { Button } from "../../components/Button";
import { PageHeader } from "../../components/PageHeader";
import { ProgressBar } from "../../components/ProgressBar";
import { StatusChip } from "../../components/StatusChip";
import { formatDate, formatDuration, formatPercent, formatRate } from "../../lib/format";

export function BookDetailPage() {
  const { id } = useParams<{ id: string }>();
  const bookQuery = useBook(id);
  const deleteBook = useDeleteBook();
  const navigate = useNavigate();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const book = bookQuery.data;

  if (bookQuery.isLoading) {
    return (
      <div className="page page--narrow">
        <div className="page-loading">
          <div className="skeleton skeleton--title" />
          <div className="skeleton skeleton--card" />
        </div>
      </div>
    );
  }

  if (bookQuery.isError || !book) {
    return (
      <div className="page page--narrow">
        <div className="alert" role="alert">
          <AlertTriangle size={18} />
          <div>
            <strong>No se pudo abrir el libro.</strong>
            <p>{errorMessage(bookQuery.error)}</p>
            <Link className="link-button" to="/">
              Volver a la biblioteca
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const deleteError = deleteBook.isError ? errorMessage(deleteBook.error) : null;

  return (
    <div className="page page--narrow">
      <PageHeader
        eyebrow="Libro"
        title={book.title}
        subtitle={`${book.author} · ${book.language.toUpperCase()}`}
        actions={
          <Link className="button button--ghost" to="/">
            <ArrowLeft size={17} />
            Biblioteca
          </Link>
        }
      />

      <section className="panel">
        <div className="panel-body">
          <div className="detail-grid">
            <div className="book-cover">
              {book.cover_url ? (
                <img src={apiUrl(book.cover_url)} alt={`Portada de ${book.title}`} />
              ) : (
                <div className="cover-placeholder" aria-hidden="true">
                  {book.title.slice(0, 2).toUpperCase()}
                </div>
              )}
            </div>
            <div className="detail-meta">
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                <StatusChip status={book.status} />
                <span className="mono muted">Actualizado {formatDate(book.updated_at)}</span>
              </div>
              <p className="page-subtitle" style={{ marginTop: 0 }}>
                {book.status === "ready"
                  ? "El audio está listo. En la próxima fase vas a poder leer y escuchar sincronizados."
                  : "El libro está en tu biblioteca local. Prepará la voz para generar el audiolibro."}
              </p>

              {book.progress > 0 ? (
                <div className="book-progress" style={{ maxWidth: 360 }}>
                  <ProgressBar value={book.progress} label="Progreso de escucha" />
                  <span className="mono muted">{formatPercent(book.progress)} escuchado</span>
                </div>
              ) : null}

              <div className="detail-facts">
                <div className="fact">
                  <strong>{book.chapter_count}</strong>
                  <span>Capítulos</span>
                </div>
                <div className="fact">
                  <strong>{formatDuration(book.duration_ms)}</strong>
                  <span>Duración</span>
                </div>
                <div className="fact">
                  <strong>{formatRate(book.rate)}</strong>
                  <span>Velocidad</span>
                </div>
                <div className="fact">
                  <strong>{book.engine === "azure" ? "Azure" : "Edge"}</strong>
                  <span>Motor</span>
                </div>
              </div>

              <div className="continue-actions" style={{ marginTop: "var(--space-5)" }}>
                <Link className="button button--primary" to={`/books/${book.id}/studio`}>
                  <Headphones size={17} />
                  {book.status === "ready" ? "Abrir estudio" : "Preparar audiolibro"}
                </Link>
                {book.status === "ready" ? (
                  <a className="button" href={apiUrl(`/books/${book.id}/m4b`)} download>
                    <Download size={17} />
                    Descargar M4B
                  </a>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </section>

      {book.last_job ? (
        <section className="panel" style={{ marginTop: "var(--space-5)" }}>
          <div className="panel-body">
            <p className="eyebrow">Último trabajo</p>
            <div className="summary-list" style={{ marginTop: "var(--space-3)" }}>
              <div className="summary-row">
                <span>Estado</span>
                <strong>{book.last_job.status}</strong>
              </div>
              <div className="summary-row">
                <span>Progreso</span>
                <strong>
                  {book.last_job.completed_segments} / {book.last_job.total_segments} segmentos
                </strong>
              </div>
              <div className="summary-row">
                <span>Iniciado</span>
                <strong>{formatDate(book.last_job.started_at)}</strong>
              </div>
            </div>
          </div>
        </section>
      ) : null}

      <section style={{ marginTop: "var(--space-6)" }}>
        <Dialog.Root open={confirmOpen} onOpenChange={setConfirmOpen}>
          <Dialog.Trigger asChild>
            <Button variant="danger">
              <Trash2 size={16} />
              Eliminar libro
            </Button>
          </Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Overlay className="dialog-overlay" />
            <Dialog.Content className="dialog-content">
              <Dialog.Title asChild>
                <h2>¿Eliminar “{book.title}”?</h2>
              </Dialog.Title>
              <Dialog.Description asChild>
                <p>
                  Se borran el EPUB, el audio, los timings y el estado de lectura. Esta acción no se
                  puede deshacer.
                </p>
              </Dialog.Description>
              {deleteError ? (
                <div className="alert" role="alert" style={{ marginTop: "var(--space-4)" }}>
                  <AlertTriangle size={18} />
                  <span>{deleteError}</span>
                </div>
              ) : null}
              <div className="dialog-actions">
                <Dialog.Close asChild>
                  <Button variant="ghost">Cancelar</Button>
                </Dialog.Close>
                <Button
                  variant="danger"
                  loading={deleteBook.isPending}
                  onClick={() => {
                    deleteBook.mutate(book.id, {
                      onSuccess: () => navigate("/"),
                    });
                  }}
                >
                  Eliminar definitivamente
                </Button>
              </div>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      </section>
    </div>
  );
}
