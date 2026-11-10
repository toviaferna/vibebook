import * as Dialog from "@radix-ui/react-dialog";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  Download,
  Headphones,
  RefreshCw,
  Trash2,
  Undo2,
  Waves,
} from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { errorMessage } from "../../api/client";
import {
  useAmbienceRenderJob,
  useAnalyzeBookAmbience,
  useBook,
  useBookAmbience,
  useDeleteBook,
  useGenerateAmbienceAssets,
  useRepairSegments,
  useResegmentBackups,
  useResegmentPlan,
  useRestoreResegment,
  useStartAmbienceRender,
} from "../../api/queries";
import { Button } from "../../components/Button";
import { PageHeader } from "../../components/PageHeader";
import { ProgressBar } from "../../components/ProgressBar";
import { StatusChip } from "../../components/StatusChip";
import { useMediaUrl } from "../../hooks/useMediaUrl";
import { formatDate, formatDuration, formatPercent, formatRate } from "../../lib/format";

export function BookDetailPage() {
  const { id } = useParams<{ id: string }>();
  const bookQuery = useBook(id);
  const deleteBook = useDeleteBook();
  const ambienceQuery = useBookAmbience(id);
  const analyzeAmbience = useAnalyzeBookAmbience(id ?? "");
  const generateBeds = useGenerateAmbienceAssets();
  const navigate = useNavigate();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [ambienceJobId, setAmbienceJobId] = useState<string | null>(null);
  const ambienceJob = useAmbienceRenderJob(ambienceJobId);
  const startAmbienceRender = useStartAmbienceRender(id ?? "");
  const resegmentQuery = useResegmentPlan(id);
  const resegmentBackups = useResegmentBackups(id);
  const repairSegments = useRepairSegments(id ?? "");
  const restoreResegment = useRestoreResegment(id ?? "");
  const [repairMessage, setRepairMessage] = useState<string | null>(null);
  const book = bookQuery.data;
  const cover = useMediaUrl(id, "cover", book?.cover_url);
  const m4bUrl = useMediaUrl(
    id,
    "m4b",
    book?.status === "ready" ? `/api/books/${id}/m4b` : undefined,
  );
  const ambientUrl = useMediaUrl(
    id,
    "ambience",
    ambienceJob.data?.status === "completed" ? `/api/books/${id}/ambience/audio` : undefined,
  );

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
  const resegmentPlan = resegmentQuery.data;
  const backups = resegmentBackups.data ?? [];
  const repairError = repairSegments.isError
    ? errorMessage(repairSegments.error)
    : restoreResegment.isError
      ? errorMessage(restoreResegment.error)
      : null;
  const runRepair = () => {
    setRepairMessage(null);
    repairSegments.mutate(false, {
      onSuccess: (result) => {
        if (!result.changed) {
          setRepairMessage("La segmentación ya estaba al día.");
          return;
        }
        const rebuilt = result.rebuilt_chapters?.length ?? 0;
        setRepairMessage(
          result.backup_id
            ? `Reparación lista: ${result.synthesized_segments ?? 0} segmentos nuevos, ` +
                `${result.reused_segments ?? 0} reutilizados y ${rebuilt} capítulos reensamblados. ` +
                "La copia de seguridad quedó guardada."
            : "Texto actualizado. El próximo audio usará la segmentación corregida.",
        );
      },
    });
  };
  const runRestore = () => {
    setRepairMessage(null);
    restoreResegment.mutate(backups[0]?.id ?? null, {
      onSuccess: (result) => {
        setRepairMessage(
          `Restaurada la copia ${result.backup_id} (${result.restored.length} archivos).`,
        );
      },
    });
  };

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
              {cover ? (
                <img src={cover} alt={`Portada de ${book.title}`} />
              ) : (
                <div className="cover-placeholder cover-placeholder--detail" aria-hidden="true">
                  <span className="cover-placeholder-mark">
                    VB · {book.title.slice(0, 2).toUpperCase()}
                  </span>
                  <strong>{book.title}</strong>
                  <span className="cover-placeholder-author">{book.author}</span>
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
                  ? "El audio está listo. Podés leer y escuchar el libro con el texto sincronizado."
                  : "El libro ya está en tu biblioteca. Podés leerlo ahora; el audiolibro es opcional."}
              </p>

              {book.progress > 0 ? (
                <div className="book-progress" style={{ maxWidth: 360 }}>
                  <ProgressBar value={book.progress} label="Progreso de escucha" />
                  <span className="mono muted">{formatPercent(book.progress)} escuchado</span>
                </div>
              ) : null}
              {book.reading_progress > 0 ? (
                <div className="book-progress" style={{ maxWidth: 360 }}>
                  <ProgressBar value={book.reading_progress} label="Progreso de lectura" />
                  <span className="mono muted">{formatPercent(book.reading_progress)} leído</span>
                </div>
              ) : null}

              <div className="detail-facts">
                <div className="fact">
                  <strong>{book.chapter_count}</strong>
                  <span>Capítulos</span>
                </div>
                <div className="fact">
                  <strong>
                    {book.status === "ready" ? formatDuration(book.duration_ms) : "—"}
                  </strong>
                  <span>Duración</span>
                </div>
                <div className="fact">
                  <strong>{book.status === "ready" ? formatRate(book.rate) : "—"}</strong>
                  <span>Velocidad</span>
                </div>
                <div className="fact">
                  <strong>
                    {book.status === "ready"
                      ? book.engine === "azure"
                        ? "Azure"
                        : "Edge"
                      : "Sin audio"}
                  </strong>
                  <span>Motor</span>
                </div>
              </div>

              <div className="continue-actions" style={{ marginTop: "var(--space-5)" }}>
                <Link className="button button--primary" to={`/books/${book.id}/read`}>
                  <BookOpen size={17} />
                  {book.status === "ready" ? "Leer y escuchar" : "Leer"}
                </Link>
                {book.status !== "ready" ? (
                  <Link className="button" to={`/books/${book.id}/studio`}>
                    <Headphones size={17} />
                    Convertir a audiolibro
                  </Link>
                ) : (
                  <Link className="button" to={`/books/${book.id}/studio`}>
                    <Headphones size={17} />
                    Abrir estudio
                  </Link>
                )}
                {book.status === "ready" && m4bUrl ? (
                  <a className="button button--ghost" href={m4bUrl} download>
                    <Download size={17} />
                    Descargar M4B
                  </a>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="colophon" aria-label="Colofón del libro">
        <div className="colophon-copy">
          <p className="eyebrow">Colofón</p>
          <p>
            Edición local · {book.chapter_count} capítulos ·{" "}
            {book.status === "ready"
              ? `${book.engine === "azure" ? "Azure" : "Edge"} · ${book.voice ?? "voz local"} · ${formatRate(book.rate)}`
              : "sin audio · lectura directa del EPUB"}
          </p>
        </div>
        <span className="colophon-mark" aria-hidden="true">
          VB
          <small>{book.id.slice(-3).toUpperCase()}</small>
        </span>
      </section>

      <section className="panel ambience-panel">
        <div className="panel-head">
          <div>
            <p className="eyebrow">Ambientación</p>
            <h2>Sonido del libro</h2>
          </div>
          <span className="mono muted">
            {ambienceQuery.data?.plan.chapters.length
              ? `${ambienceQuery.data.plan.chapters.length} ${
                  ambienceQuery.data.plan.chapters.length === 1 ? "capítulo" : "capítulos"
                } con plan`
              : "Sin plan"}
          </span>
        </div>
        <div className="panel-body ambience-body">
          <p className="hint">
            Camas y efectos locales, sin cuentas ni APIs pagas. Generá las camas procedurales,
            analizá el texto y después activá el ambiente desde el lector.
          </p>
          <div className="ambience-actions">
            <Button onClick={() => generateBeds.mutate(undefined)} loading={generateBeds.isPending}>
              <Waves size={16} />
              Generar camas
            </Button>
            <Button
              variant="primary"
              onClick={() => analyzeAmbience.mutate()}
              loading={analyzeAmbience.isPending}
              disabled={generateBeds.isPending}
            >
              Analizar capítulos
            </Button>
            <Button
              onClick={() =>
                startAmbienceRender.mutate(undefined, {
                  onSuccess: (result) => setAmbienceJobId(result.job_id),
                })
              }
              loading={startAmbienceRender.isPending}
              disabled={!ambienceQuery.data?.plan.chapters.length}
            >
              Exportar ambientado
            </Button>
            {ambienceJob.data?.status === "completed" && ambientUrl ? (
              <a className="button button--ghost" href={ambientUrl} download>
                Descargar M4B ambientado
              </a>
            ) : null}
          </div>
          {ambienceJob.data ? (
            <p className="hint">
              Render: {ambienceJob.data.status}
              {ambienceJob.data.status === "running" && ambienceJob.data.chapter_title
                ? ` · ${ambienceJob.data.chapter_title}`
                : null}
            </p>
          ) : null}
          {ambienceJob.data?.status === "failed" ? (
            <div className="alert" role="alert">
              <AlertTriangle size={18} />
              <span>{ambienceJob.data.error ?? "No se pudo exportar el ambiente."}</span>
            </div>
          ) : null}
          {generateBeds.isSuccess ? (
            <p className="hint">Camas listas en la biblioteca de sonidos.</p>
          ) : null}
          {analyzeAmbience.isError ? (
            <div className="alert" role="alert">
              <AlertTriangle size={18} />
              <span>{errorMessage(analyzeAmbience.error)}</span>
            </div>
          ) : null}
          {ambienceQuery.data?.plan.chapters.length ? (
            <ul className="ambience-chapters">
              {ambienceQuery.data.plan.chapters.slice(0, 4).map((chapter) => (
                <li key={chapter.chapter_index}>
                  <span className="mono">Capítulo {chapter.chapter_index}</span>
                  <span>{chapter.bed?.reason ?? "sin cama"}</span>
                  <span className="mono muted">
                    {chapter.effects.length} {chapter.effects.length === 1 ? "efecto" : "efectos"}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="hint">Todavía no hay un plan de ambiente para este libro.</p>
          )}
        </div>
      </section>

      <section className="panel maintenance-panel" aria-label="Mantenimiento del texto">
        <div className="panel-head">
          <div>
            <p className="eyebrow">Mantenimiento</p>
            <h2>Segmentación del audio</h2>
          </div>
          {resegmentPlan ? (
            <span className="mono muted">
              v{resegmentPlan.current_version ?? "?"} → v{resegmentPlan.target_version}
            </span>
          ) : null}
        </div>
        <div className="panel-body">
          {resegmentQuery.isLoading ? <p className="hint">Revisando el texto del EPUB…</p> : null}
          {resegmentQuery.isError ? (
            <div className="alert" role="alert">
              <AlertTriangle size={18} />
              <span>{errorMessage(resegmentQuery.error)}</span>
            </div>
          ) : null}
          {resegmentPlan && !resegmentPlan.can_repair ? (
            <p className="hint">
              {resegmentPlan.reason === "source_missing"
                ? "Falta el EPUB fuente, así que no se puede volver a segmentar."
                : "El libro no está listo para repararse ahora mismo."}
            </p>
          ) : null}
          {resegmentPlan?.can_repair ? (
            <>
              <p className="hint">
                {resegmentPlan.needs_repair
                  ? `${resegmentPlan.changed_segments} ${
                      resegmentPlan.changed_segments === 1 ? "segmento" : "segmentos"
                    } con texto viejo en ${resegmentPlan.changed_chapters.length} ${
                      resegmentPlan.changed_chapters.length === 1 ? "capítulo" : "capítulos"
                    }. Solo se regenera el audio afectado; el resto se reutiliza.`
                  : "El texto usa la segmentación actual. No hay palabras cortadas pendientes."}
              </p>
              <div className="continue-actions">
                {resegmentPlan.needs_repair ? (
                  <Button onClick={runRepair} loading={repairSegments.isPending}>
                    <RefreshCw size={16} />
                    {book.status === "ready" ? "Reparar segmentación" : "Actualizar texto"}
                  </Button>
                ) : null}
                {backups.length > 0 ? (
                  <Button variant="ghost" onClick={runRestore} loading={restoreResegment.isPending}>
                    <Undo2 size={16} />
                    Restaurar última copia
                  </Button>
                ) : null}
              </div>
              {backups.length > 0 ? (
                <p className="hint">
                  Última copia:{" "}
                  {backups[0].created_at ? formatDate(backups[0].created_at) : "sin fecha"}
                  {backups[0].changed_chapters.length
                    ? ` · capítulos ${backups[0].changed_chapters.join(", ")}`
                    : ""}
                </p>
              ) : null}
            </>
          ) : null}
          {repairMessage ? (
            <p className="hint" role="status">
              {repairMessage}
            </p>
          ) : null}
          {repairError ? (
            <div className="alert" role="alert">
              <AlertTriangle size={18} />
              <span>{repairError}</span>
            </div>
          ) : null}
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
