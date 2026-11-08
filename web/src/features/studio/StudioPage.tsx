import { useMutation } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, AudioLines, ShieldCheck } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api, apiUrl, errorMessage } from "../../api/client";
import {
  useBook,
  useCancelJob,
  useEngines,
  useJob,
  useJobEvents,
  useResumeJob,
  useSettings,
  useStartConversion,
  useVoices,
} from "../../api/queries";
import type { Job } from "../../api/types";
import { Button } from "../../components/Button";
import { PageHeader } from "../../components/PageHeader";
import { StatusChip } from "../../components/StatusChip";
import { formatDuration, formatRate } from "../../lib/format";
import { defaultVoiceForEngine, voiceLabel } from "../../lib/voices";
import { ProgressPanel } from "./ProgressPanel";
import { StepCard } from "./StepCard";
import { VoicePicker } from "./VoicePicker";

const ACTIVE = new Set(["queued", "running", "cancelling"]);
const RESUMABLE = new Set(["cancelled", "interrupted", "failed"]);
const SAMPLE = "Hola. Así va a sonar tu próximo audiolibro en Vibebook.";

export function StudioPage() {
  const { id } = useParams<{ id: string }>();
  const bookQuery = useBook(id);
  const enginesQuery = useEngines();
  const voicesQuery = useVoices();
  const settingsQuery = useSettings();

  const [voice, setVoice] = useState("es-MX-JorgeNeural");
  const [engine, setEngine] = useState("edge");
  const [style, setStyle] = useState("neutral");
  const [rate, setRate] = useState("-10%");
  const [force, setForce] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [previewing, setPreviewing] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const initialized = useRef(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const book = bookQuery.data;
  const engines = enginesQuery.data?.items ?? [];
  const voices = voicesQuery.data ?? [];
  const settings = settingsQuery.data;
  const jobQuery = useJob(jobId);
  const job = jobQuery.data ?? null;
  const start = useStartConversion(id ?? "");
  const cancel = useCancelJob(id ?? "");
  const resume = useResumeJob(id ?? "");
  useJobEvents(jobId, id ?? "");

  const selectedVoice = voices.find((item) => item.id === voice);
  const selectedEngine = engines.find((item) => item.id === engine);
  const previewMutation = useMutation({
    mutationFn: (voiceId: string) =>
      api.previewVoice({ voice: voiceId, engine, style, rate, text: SAMPLE }),
    onMutate: (voiceId) => {
      setPreviewing(voiceId);
      setPreviewError(null);
    },
    onSuccess: (preview) => {
      audioRef.current?.pause();
      const audio = new Audio(apiUrl(preview.url));
      audioRef.current = audio;
      void audio.play().catch(() => {
        setPreviewError("El navegador bloqueó la reproducción de la muestra.");
      });
    },
    onError: (error) => setPreviewError(errorMessage(error)),
    onSettled: () => setPreviewing(null),
  });

  useEffect(() => {
    if (initialized.current || !book) {
      return;
    }
    const defaults = settings;
    setVoice(book.voice ?? defaults?.default_voice ?? "es-MX-JorgeNeural");
    setRate(book.rate ?? defaults?.default_rate ?? "-10%");
    setEngine(book.engine ?? defaults?.default_engine ?? "edge");
    initialized.current = true;
  }, [book, settings]);

  useEffect(() => {
    if (jobId || !book?.last_job) {
      return;
    }
    if (!ACTIVE.has(book.last_job.status) && !RESUMABLE.has(book.last_job.status)) {
      return;
    }
    setJobId(book.last_job.id);
  }, [book, jobId]);

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
    };
  }, []);

  if (bookQuery.isLoading) {
    return (
      <div className="page page--narrow">
        <div className="page-loading">
          <div className="skeleton skeleton--title" />
          <div className="skeleton" />
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

  const activeJob = job !== null && ACTIVE.has(job.status);
  const locked = activeJob;
  const rateValue = Number.parseInt(rate.replace(/[+%]/g, ""), 10) || 0;
  const voiceInfo = selectedVoice ? voiceLabel(selectedVoice) : null;

  const changeEngine = (nextEngine: string) => {
    setEngine(nextEngine);
    const spec = engines.find((item) => item.id === nextEngine);
    const current = voices.find((item) => item.id === voice);
    if (current && nextEngine !== "fake" && !current.engines.includes(nextEngine)) {
      const fallback = defaultVoiceForEngine(nextEngine, voices);
      if (fallback) {
        setVoice(fallback);
      }
    }
    if (!spec?.supports_styles) {
      setStyle("neutral");
    }
  };

  const changeVoice = (voiceId: string) => {
    setVoice(voiceId);
    const selected = voices.find((item) => item.id === voiceId);
    if (selected && engine !== "fake" && !selected.engines.includes(engine)) {
      const fallbackEngine = selected.engines[0] ?? "edge";
      setEngine(fallbackEngine);
      const fallbackSpec = engines.find((item) => item.id === fallbackEngine);
      if (!fallbackSpec?.supports_styles) {
        setStyle("neutral");
      }
    }
    if (selected && style !== "neutral" && !selected.styles.includes(style)) {
      setStyle("neutral");
    }
  };

  const startConversion = () => {
    start.mutate(
      { voice, engine, style, rate, force },
      {
        onSuccess: (result) => setJobId(result.job_id),
      },
    );
  };

  const cancelConversion = () => {
    if (job) {
      cancel.mutate(job.id);
    }
  };

  const resumeConversion = () => {
    if (job) {
      resume.mutate(job.id, {
        onSuccess: (result) => setJobId(result.job_id),
      });
    }
  };

  const showProgress = Boolean(jobId);
  const visibleEngines = engines.filter(
    (item) => item.implemented && (!item.test_only || item.available),
  );

  return (
    <div className="page">
      <PageHeader
        eyebrow="Estudio"
        title={book.title}
        subtitle={`${book.author} · ${book.chapter_count} capítulos · ${formatDuration(book.duration_ms)}`}
        actions={
          <>
            <Link className="button button--ghost" to={`/books/${book.id}`}>
              <ArrowLeft size={17} />
              Volver
            </Link>
            <StatusChip status={book.status} />
          </>
        }
      />

      {enginesQuery.isError || voicesQuery.isError ? (
        <div className="alert" role="alert" style={{ marginBottom: "var(--space-5)" }}>
          <AlertTriangle size={18} />
          <span>
            {errorMessage(enginesQuery.error ?? voicesQuery.error ?? new Error("Error de carga"))}
          </span>
        </div>
      ) : null}

      {previewError ? (
        <div className="alert" role="alert" style={{ marginBottom: "var(--space-5)" }}>
          <AlertTriangle size={18} />
          <span>{previewError}</span>
        </div>
      ) : null}

      <div className="studio-layout">
        <div className="step-list">
          <StepCard
            number={1}
            title="Libro"
            description="Texto limpio, capítulos y duración estimada."
            active={!locked}
            status={<StatusChip status={book.status} />}
          >
            <div className="summary-facts">
              <div className="fact">
                <strong>{book.chapter_count}</strong>
                <span>Capítulos</span>
              </div>
              <div className="fact">
                <strong>{formatDuration(book.duration_ms)}</strong>
                <span>Audio</span>
              </div>
              <div className="fact">
                <strong>{book.language.toUpperCase()}</strong>
                <span>Idioma</span>
              </div>
            </div>
          </StepCard>

          <StepCard
            number={2}
            title="Voz"
            description="Elegí el timbre y la velocidad. Podés escuchar una muestra."
            active={!locked}
            status={voiceInfo ? <span className="mono muted">{voiceInfo.name}</span> : null}
          >
            <VoicePicker
              voices={voices}
              selected={voice}
              engine={engine}
              previewing={previewing}
              onSelect={changeVoice}
              onPreview={(voiceId) => previewMutation.mutate(voiceId)}
            />

            <div className="rate-row">
              <div className="rate-head">
                <label className="label" htmlFor="rate">
                  Velocidad
                </label>
                <span className="rate-value">{formatRate(rate)}</span>
              </div>
              <input
                id="rate"
                className="range"
                type="range"
                min={-50}
                max={50}
                step={5}
                value={rateValue}
                disabled={locked}
                onChange={(event) => {
                  const value = Number(event.target.value);
                  setRate(`${value >= 0 ? "+" : ""}${value}%`);
                }}
              />
              <p className="hint">Una velocidad más lenta ayuda a seguir la lectura.</p>
            </div>

            {selectedEngine?.supports_styles && selectedVoice?.styles.length ? (
              <div className="field" style={{ marginTop: "var(--space-3)" }}>
                <label className="label" htmlFor="style">
                  Estilo
                </label>
                <select
                  id="style"
                  className="select"
                  value={style}
                  disabled={locked}
                  onChange={(event) => setStyle(event.target.value)}
                >
                  <option value="neutral">Neutral</option>
                  {selectedVoice.styles.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </div>
            ) : null}
          </StepCard>

          <StepCard
            number={3}
            title="Salida"
            description="El audio queda en tu biblioteca local."
            active={!locked}
            status={
              <span className="mono muted">
                <ShieldCheck size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                Local
              </span>
            }
          >
            <div className="form-grid">
              <div className="field">
                <span className="label">Carpeta</span>
                <p className="mono muted">{settings?.library_dir ?? "Biblioteca local"}</p>
              </div>
              <div className="field">
                <label className="label" htmlFor="engine">
                  Motor
                </label>
                <select
                  id="engine"
                  className="select"
                  value={engine}
                  disabled={locked || engines.length === 0}
                  onChange={(event) => changeEngine(event.target.value)}
                >
                  {visibleEngines.map((item) => (
                    <option key={item.id} value={item.id} disabled={!item.available}>
                      {item.label}
                      {item.legacy ? " · legado" : ""}
                      {!item.available
                        ? item.transport === "local"
                          ? " (no instalado)"
                          : " (sin configurar)"
                        : ""}
                    </option>
                  ))}
                </select>
                <p className="hint">
                  {selectedEngine?.description ??
                    "Edge es el camino rápido. Azure requiere credenciales y tiene cuota mensual."}
                </p>
              </div>
              <details className="advanced">
                <summary>Opciones avanzadas</summary>
                <label className="label" htmlFor="force">
                  <input
                    id="force"
                    type="checkbox"
                    checked={force}
                    disabled={locked}
                    onChange={(event) => setForce(event.target.checked)}
                  />{" "}
                  Re-sintetizar aunque exista caché
                </label>
              </details>
            </div>
          </StepCard>
        </div>

        <aside className="studio-summary panel" aria-label="Paso 4, convertir">
          <div className="panel-body">
            {showProgress ? (
              <ProgressPanel
                bookId={book.id}
                job={job}
                cancelling={cancel.isPending}
                resuming={resume.isPending}
                onCancel={cancelConversion}
                onResume={resumeConversion}
              />
            ) : (
              <>
                <p className="eyebrow">Paso 04</p>
                <h2 style={{ marginTop: "var(--space-1)", fontSize: "var(--step-5)" }}>
                  Convertir
                </h2>
                <p className="hint" style={{ marginTop: "var(--space-2)" }}>
                  Revisá el resumen y empezá. Podés cancelar sin perder los segmentos ya hechos.
                </p>

                <div className="summary-list" style={{ marginTop: "var(--space-5)" }}>
                  <div className="summary-row">
                    <span>Voz</span>
                    <strong>{voiceInfo?.name ?? voice}</strong>
                  </div>
                  <div className="summary-row">
                    <span>Velocidad</span>
                    <strong>{formatRate(rate)}</strong>
                  </div>
                  <div className="summary-row">
                    <span>Motor</span>
                    <strong>{selectedEngine?.label ?? engine}</strong>
                  </div>
                  <div className="summary-row">
                    <span>Capítulos</span>
                    <strong>{book.chapter_count}</strong>
                  </div>
                </div>

                {start.isError ? (
                  <div className="alert" role="alert" style={{ marginTop: "var(--space-4)" }}>
                    <AlertTriangle size={18} />
                    <span>{errorMessage(start.error)}</span>
                  </div>
                ) : null}

                <div className="studio-actions">
                  <Button
                    variant="primary"
                    wide
                    onClick={startConversion}
                    loading={start.isPending}
                    disabled={!selectedVoice}
                  >
                    <AudioLines size={17} />
                    {book.status === "ready" ? "Reconvertir" : "Convertir audiolibro"}
                  </Button>
                  <p className="hint">
                    El tiempo depende de la red y de la longitud del libro. La caché se conserva.
                  </p>
                </div>
              </>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

export function isJobActive(job: Job | null): boolean {
  return job !== null && ACTIVE.has(job.status);
}
