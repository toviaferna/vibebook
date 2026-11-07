export function formatDuration(ms: number | null | undefined): string {
  if (!ms || ms <= 0) {
    return "—";
  }
  const totalSeconds = Math.round(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (hours > 0) {
    return `${hours} h ${minutes} min`;
  }
  if (totalSeconds < 60) {
    return `${totalSeconds} s`;
  }
  return `${minutes} min`;
}

export function formatTime(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

export function formatPercent(value: number): string {
  return `${Math.round(Math.min(1, Math.max(0, value)) * 100)}%`;
}

export function formatRate(rate: string | null | undefined): string {
  if (!rate) {
    return "—";
  }
  return rate.replace("+", "");
}

export function formatStatus(status: string): string {
  const labels: Record<string, string> = {
    imported: "Importado",
    converting: "Convirtiendo",
    ready: "Listo",
    error: "Error",
    interrupted: "Interrumpido",
    missing: "Sin archivos",
    queued: "En cola",
    running: "En curso",
    cancelling: "Cancelando",
    completed: "Completado",
    failed: "Falló",
    cancelled: "Cancelado",
  };
  return labels[status] ?? status;
}

export function formatStage(stage: string): string {
  const labels: Record<string, string> = {
    preparing: "Preparando",
    synthesizing: "Sintetizando",
    assembling: "Ensamblando",
    finalizing: "Creando el M4B",
    done: "Listo",
    cancelled: "Cancelado",
    error: "Error",
  };
  return labels[stage] ?? stage;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) {
    return "—";
  }
  try {
    return new Intl.DateTimeFormat("es", {
      day: "numeric",
      month: "short",
      year: "numeric",
    }).format(new Date(iso));
  } catch {
    return "—";
  }
}

export function formatEta(job: {
  started_at: string | null;
  completed_segments: number;
  total_segments: number;
}): string | null {
  if (!job.started_at || job.completed_segments <= 0) {
    return null;
  }
  const elapsed = Date.now() - new Date(job.started_at).getTime();
  if (elapsed <= 0) {
    return null;
  }
  const remaining = job.total_segments - job.completed_segments;
  if (remaining <= 0) {
    return null;
  }
  const perSegment = elapsed / job.completed_segments;
  const seconds = Math.max(1, Math.round((perSegment * remaining) / 1000));
  if (seconds < 60) {
    return `Quedan ~${seconds} s`;
  }
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `Quedan ~${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  return `Quedan ~${hours} h ${minutes % 60} min`;
}

export function pluralize(count: number, singular: string, plural: string): string {
  return count === 1 ? singular : plural;
}
