import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Download,
  RotateCcw,
  Square,
  XCircle,
} from "lucide-react";
import { Link } from "react-router-dom";

import { apiUrl } from "../../api/client";
import type { Job } from "../../api/types";
import { Button } from "../../components/Button";
import { ProgressBar } from "../../components/ProgressBar";
import { StatusChip } from "../../components/StatusChip";
import { formatEta, formatPercent, formatStage } from "../../lib/format";

interface ProgressPanelProps {
  bookId: string;
  job: Job | null;
  cancelling: boolean;
  resuming: boolean;
  onCancel: () => void;
  onResume: () => void;
}

const ACTIVE = new Set(["queued", "running", "cancelling"]);
const RESUMABLE = new Set(["cancelled", "interrupted", "failed"]);

export function ProgressPanel({
  bookId,
  job,
  cancelling,
  resuming,
  onCancel,
  onResume,
}: ProgressPanelProps) {
  if (!job) {
    return (
      <div className="progress-panel" aria-live="polite">
        <p className="eyebrow">Conversión</p>
        <h2>Preparando el trabajo…</h2>
        <div className="skeleton" />
      </div>
    );
  }

  const percent = job.total_segments > 0 ? job.completed_segments / job.total_segments : 0;
  const eta = formatEta(job);
  const active = ACTIVE.has(job.status);

  return (
    <div className="progress-panel" aria-live="polite">
      <div className="progress-top">
        <div>
          <p className="eyebrow">Conversión</p>
          <h2>{formatStage(job.stage)}</h2>
        </div>
        <div style={{ display: "grid", justifyItems: "end", gap: "var(--space-2)" }}>
          <StatusChip status={job.status} />
          <span className="progress-percent">{formatPercent(percent)}</span>
        </div>
      </div>

      <ProgressBar value={percent} label="Progreso de conversión" />

      <div className="job-meta">
        <span>
          {job.completed_segments} de {job.total_segments} segmentos
        </span>
        {job.chapter_title ? <span>{job.chapter_title}</span> : null}
        {eta ? <span>{eta}</span> : null}
      </div>

      {job.current_text ? (
        <p className="job-text" lang="es">
          {job.current_text}
        </p>
      ) : null}

      {job.error ? (
        <div className="alert" role="alert">
          <AlertTriangle size={18} />
          <span>{job.error}</span>
        </div>
      ) : null}

      {job.status === "completed" ? (
        <div className="alert" style={{ borderColor: "var(--audio)", color: "var(--audio)" }}>
          <CheckCircle2 size={18} />
          <div>
            <strong>Conversión completa.</strong>
            <p>El M4B y los archivos del lector ya están listos.</p>
          </div>
        </div>
      ) : null}

      <div className="studio-actions">
        {active ? (
          <Button
            variant="danger"
            onClick={onCancel}
            loading={cancelling || job.status === "cancelling"}
          >
            <Square size={16} />
            Cancelar conversión
          </Button>
        ) : null}

        {RESUMABLE.has(job.status) ? (
          <Button variant="primary" onClick={onResume} loading={resuming}>
            <RotateCcw size={16} />
            Reanudar
          </Button>
        ) : null}

        {job.status === "completed" ? (
          <>
            <a className="button button--primary" href={apiUrl(`/books/${bookId}/m4b`)} download>
              <Download size={16} />
              Descargar M4B
            </a>
            <Link className="button button--primary" to={`/books/${bookId}/read`}>
              <BookOpen size={16} />
              Leer ahora
            </Link>
            <Link className="button button--ghost" to={`/books/${bookId}`}>
              <CheckCircle2 size={16} />
              Volver al libro
            </Link>
          </>
        ) : null}

        {job.status === "cancelled" || job.status === "interrupted" ? (
          <p className="hint">
            <XCircle size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
            Los segmentos ya generados se conservan.
          </p>
        ) : null}
      </div>
    </div>
  );
}
