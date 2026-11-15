import {
  AlertTriangle,
  Download,
  Music2,
  RefreshCw,
  Save,
  Trash2,
  Upload,
  Waves,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { errorMessage } from "../../api/client";
import {
  useAmbienceAssets,
  useAmbienceRenderJob,
  useAnalyzeBookAmbience,
  useBookAmbience,
  useDeleteAmbienceAsset,
  useGenerateAmbienceAssets,
  useReaderManifest,
  useStartAmbienceRender,
  useUpdateBookAmbience,
  useUploadAmbienceAsset,
} from "../../api/queries";
import type {
  AmbienceBed,
  AmbiencePlanUpdate,
  Book,
  BookAmbience,
  SoundAsset,
} from "../../api/types";
import { Button } from "../../components/Button";
import { useMediaUrl } from "../../hooks/useMediaUrl";
import { formatDuration, formatStatus } from "../../lib/format";

interface AmbiencePanelProps {
  book: Book;
}

export function AmbiencePanel({ book }: AmbiencePanelProps) {
  const ambienceQuery = useBookAmbience(book.id);
  const manifestQuery = useReaderManifest(book.id);
  const assetsQuery = useAmbienceAssets({ limit: 200 });
  const analyze = useAnalyzeBookAmbience(book.id);
  const generate = useGenerateAmbienceAssets();
  const update = useUpdateBookAmbience(book.id);
  const upload = useUploadAmbienceAsset();
  const removeAsset = useDeleteAmbienceAsset();
  const startRender = useStartAmbienceRender(book.id);
  const [jobId, setJobId] = useState<string | null>(null);
  const job = useAmbienceRenderJob(jobId);
  const ambientUrl = useMediaUrl(
    book.id,
    "ambience",
    job.data?.status === "completed" ? `/api/books/${book.id}/ambience/audio` : undefined,
  );

  const [draft, setDraft] = useState<AmbiencePlanUpdate | null>(null);
  const [dirty, setDirty] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!ambienceQuery.data || dirty) {
      return;
    }
    setDraft(cloneAmbience(ambienceQuery.data));
  }, [ambienceQuery.data, dirty]);

  const current = draft ?? (ambienceQuery.data ? cloneAmbience(ambienceQuery.data) : null);
  const assets = assetsQuery.data?.items ?? [];
  const bedAssets = assets.filter((asset) => asset.kind === "ambience" || asset.kind === "music");
  const assetById = new Map(assets.map((asset) => [asset.id, asset]));
  const chapters = (manifestQuery.data?.chapters ?? []).filter(
    (chapter) => chapter.segments.length > 0,
  );
  const planned = new Map(
    (current?.plan.chapters ?? []).map((chapter) => [chapter.chapter_index, chapter]),
  );
  const hasCues = (current?.plan.chapters ?? []).some(
    (chapter) => chapter.bed !== null || chapter.effects.length > 0,
  );

  const patch = (next: AmbiencePlanUpdate) => {
    setDraft(next);
    setDirty(true);
    setMessage(null);
  };

  const setBed = (chapterIndex: number, assetId: string) => {
    if (!current) {
      return;
    }
    const asset = bedAssets.find((item) => item.id === assetId);
    const existing = planned.get(chapterIndex);
    const nextChapters = current.plan.chapters.filter(
      (chapter) => chapter.chapter_index !== chapterIndex,
    );
    if (asset) {
      nextChapters.push({
        chapter_index: chapterIndex,
        bed: bedFor(asset, existing?.bed ?? null),
        effects: existing?.effects ?? [],
      });
    } else if (existing && existing.effects.length > 0) {
      nextChapters.push({ ...existing, bed: null });
    }
    nextChapters.sort((left, right) => left.chapter_index - right.chapter_index);
    patch({ ...current, plan: { ...current.plan, chapters: nextChapters } });
  };

  const setGain = (chapterIndex: number, gainDb: number) => {
    if (!current) {
      return;
    }
    const chaptersNext = current.plan.chapters.map((chapter) =>
      chapter.chapter_index === chapterIndex && chapter.bed
        ? { ...chapter, bed: { ...chapter.bed, gain_db: gainDb } }
        : chapter,
    );
    patch({ ...current, plan: { ...current.plan, chapters: chaptersNext } });
  };

  const removeEffect = (chapterIndex: number, effectIndex: number) => {
    if (!current) {
      return;
    }
    const chaptersNext = current.plan.chapters.map((chapter) =>
      chapter.chapter_index === chapterIndex
        ? {
            ...chapter,
            effects: chapter.effects.filter((_, index) => index !== effectIndex),
          }
        : chapter,
    );
    patch({ ...current, plan: { ...current.plan, chapters: chaptersNext } });
  };

  const setSettings = (values: Partial<BookAmbience["settings"]>) => {
    if (!current) {
      return;
    }
    patch({ ...current, settings: { ...current.settings, ...values } });
  };

  const save = () => {
    if (!current) {
      return;
    }
    update.mutate(current, {
      onSuccess: () => {
        setDirty(false);
        setMessage("Plan de ambiente guardado.");
      },
    });
  };

  const analyzePlan = () => {
    setMessage(null);
    analyze.mutate(undefined, {
      onSuccess: () => {
        setDirty(false);
        setMessage("Plan analizado a partir del texto.");
      },
    });
  };

  const generateBeds = () => {
    setMessage(null);
    generate.mutate(undefined, {
      onSuccess: () => setMessage("Camas base generadas."),
    });
  };

  const exportAudio = () => {
    setMessage(null);
    startRender.mutate(undefined, {
      onSuccess: (result) => setJobId(result.job_id),
    });
  };

  return (
    <section className="panel ambience-panel" aria-label="Sonido del libro">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Ambientación</p>
          <h2>Sonido del libro</h2>
        </div>
        <span className="mono muted">
          {(current?.plan.chapters.length ?? 0) === 1
            ? "1 capítulo con plan"
            : `${current?.plan.chapters.length ?? 0} capítulos con plan`}
        </span>
      </div>
      <div className="panel-body ambience-body">
        <p className="hint">
          Elegí una cama o música por capítulo. En el lector, activá <Waves size={14} />{" "}
          <strong>Waves</strong> para escucharlo y ajustar la mezcla de ambiente y efectos.
        </p>

        <div className="ambience-actions">
          <Button onClick={generateBeds} loading={generate.isPending}>
            <Music2 size={16} />
            Generar camas
          </Button>
          <Button onClick={analyzePlan} loading={analyze.isPending}>
            <RefreshCw size={16} />
            Analizar capítulos
          </Button>
          <Button variant="primary" onClick={save} loading={update.isPending} disabled={!dirty}>
            <Save size={16} />
            Guardar plan
          </Button>
          <Button onClick={exportAudio} loading={startRender.isPending} disabled={!hasCues}>
            <Download size={16} />
            Exportar ambientado
          </Button>
          {job.data ? (
            <span className="mono muted">Exportación: {formatStatus(job.data.status)}</span>
          ) : null}
          {ambientUrl ? (
            <a className="button button--ghost" href={ambientUrl} download>
              Descargar M4B ambientado
            </a>
          ) : null}
        </div>

        {message ? (
          <p className="hint" role="status">
            {message}
          </p>
        ) : null}
        {ambienceQuery.isLoading || manifestQuery.isLoading ? (
          <p className="hint">Cargando el plan de ambiente…</p>
        ) : null}
        {ambienceQuery.isError ? (
          <div className="alert" role="alert">
            <AlertTriangle size={18} />
            <span>{errorMessage(ambienceQuery.error)}</span>
          </div>
        ) : null}
        {analyze.isError ? (
          <div className="alert" role="alert">
            <AlertTriangle size={18} />
            <span>{errorMessage(analyze.error)}</span>
          </div>
        ) : null}
        {generate.isError ? (
          <div className="alert" role="alert">
            <AlertTriangle size={18} />
            <span>{errorMessage(generate.error)}</span>
          </div>
        ) : null}
        {update.isError ? (
          <div className="alert" role="alert">
            <AlertTriangle size={18} />
            <span>{errorMessage(update.error)}</span>
          </div>
        ) : null}
        {job.data?.status === "failed" ? (
          <div className="alert" role="alert">
            <AlertTriangle size={18} />
            <span>{job.data.error ?? "No se pudo exportar el ambiente."}</span>
          </div>
        ) : null}

        {bedAssets.length === 0 ? (
          <p className="hint">
            Todavía no hay sonidos. Generá las camas base o importá tu propia música.
          </p>
        ) : null}

        <div className="ambience-chapter-list">
          {chapters.map((chapter) => {
            const entry = planned.get(chapter.index);
            const bed = entry?.bed ?? null;
            return (
              <div className="ambience-chapter" key={chapter.index}>
                <div className="ambience-chapter-head">
                  <span className="mono">Capítulo {chapter.index}</span>
                  <strong>{chapter.title}</strong>
                  <span className="mono muted">{chapter.segments.length} segmentos</span>
                </div>
                <div className="ambience-chapter-controls">
                  <label>
                    <span className="sr-only">Cama del capítulo {chapter.index}</span>
                    <select
                      className="select"
                      value={bed?.asset_id ?? ""}
                      onChange={(event) => setBed(chapter.index, event.target.value)}
                    >
                      <option value="">Sin cama</option>
                      <optgroup label="Ambiente">
                        {bedAssets
                          .filter((asset) => asset.kind === "ambience")
                          .map((asset) => (
                            <option key={asset.id} value={asset.id}>
                              {asset.prompt} · {formatDuration(asset.duration_ms)}
                            </option>
                          ))}
                      </optgroup>
                      <optgroup label="Música">
                        {bedAssets
                          .filter((asset) => asset.kind === "music")
                          .map((asset) => (
                            <option key={asset.id} value={asset.id}>
                              {asset.prompt} · {formatDuration(asset.duration_ms)}
                            </option>
                          ))}
                      </optgroup>
                    </select>
                  </label>
                  {bed ? (
                    <label className="ambience-gain">
                      <span>{Math.round(bed.gain_db)} dB</span>
                      <input
                        className="range"
                        type="range"
                        min={-40}
                        max={0}
                        step={1}
                        value={bed.gain_db}
                        onChange={(event) => setGain(chapter.index, Number(event.target.value))}
                      />
                    </label>
                  ) : null}
                </div>
                {entry && entry.effects.length > 0 ? (
                  <ul
                    className="ambience-effects"
                    aria-label={`Efectos del capítulo ${chapter.index}`}
                  >
                    {entry.effects.map((effect, index) => (
                      <li
                        key={`${effect.asset_id}-${effect.anchor.segment_id}-${effect.anchor.offset_ms}`}
                      >
                        <span>{assetLabel(assetById.get(effect.asset_id), effect.asset_id)}</span>
                        <button
                          type="button"
                          className="icon-button"
                          aria-label="Quitar efecto"
                          onClick={() => removeEffect(chapter.index, index)}
                        >
                          <Trash2 size={13} />
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            );
          })}
        </div>

        <details className="advanced ambience-mix">
          <summary>Mezcla global</summary>
          <div className="ambience-mix-grid">
            <label>
              <span>Volumen del plan · {Math.round(current?.settings.master_gain_db ?? 0)} dB</span>
              <input
                className="range"
                type="range"
                min={-60}
                max={0}
                step={1}
                value={current?.settings.master_gain_db ?? -18}
                onChange={(event) => setSettings({ master_gain_db: Number(event.target.value) })}
              />
            </label>
            <label>
              <span>Ducking de la voz · {Math.round(current?.settings.ducking_db ?? 0)} dB</span>
              <input
                className="range"
                type="range"
                min={-40}
                max={0}
                step={1}
                value={current?.settings.ducking_db ?? -12}
                onChange={(event) => setSettings({ ducking_db: Number(event.target.value) })}
              />
            </label>
          </div>
        </details>

        <details className="advanced ambience-library">
          <summary>Biblioteca de sonidos · {assets.length}</summary>
          <ImportForm
            upload={upload}
            onDone={(asset) => {
              setMessage(`Sonido importado: ${asset.prompt}.`);
            }}
          />
          <ul className="ambience-assets" aria-label="Sonidos disponibles">
            {assets.map((asset) => (
              <li key={asset.id}>
                <span>
                  <strong>{asset.prompt}</strong>{" "}
                  <span className="mono muted">
                    {asset.kind} · {formatDuration(asset.duration_ms)}
                  </span>
                </span>
                {asset.provider === "import" && asset.usage_count === 0 ? (
                  <button
                    type="button"
                    className="icon-button"
                    aria-label={`Eliminar ${asset.prompt}`}
                    onClick={() => {
                      if (window.confirm(`¿Eliminar ${asset.prompt}?`)) {
                        removeAsset.mutate(asset.id);
                      }
                    }}
                  >
                    <Trash2 size={14} />
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
          {removeAsset.isError ? (
            <div className="alert" role="alert">
              <AlertTriangle size={16} />
              <span>{errorMessage(removeAsset.error)}</span>
            </div>
          ) : null}
        </details>
      </div>
    </section>
  );
}

function ImportForm({
  upload,
  onDone,
}: {
  upload: ReturnType<typeof useUploadAmbienceAsset>;
  onDone: (asset: SoundAsset) => void;
}) {
  const formRef = useRef<HTMLFormElement>(null);
  const [title, setTitle] = useState("");
  const [license, setLicense] = useState("CC0-1.0");
  const [kind, setKind] = useState<"music" | "ambience">("music");

  return (
    <form
      ref={formRef}
      className="ambience-import"
      onSubmit={(event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const file = new FormData(form).get("file");
        if (!(file instanceof File) || file.size === 0) {
          return;
        }
        const payload = new FormData();
        payload.set("file", file);
        payload.set("prompt", title.trim() || file.name);
        payload.set("license", license.trim() || "CC0-1.0");
        payload.set("kind", kind);
        payload.set("loopable", "true");
        upload.mutate(payload, {
          onSuccess: (asset) => {
            formRef.current?.reset();
            setTitle("");
            onDone(asset);
          },
        });
      }}
    >
      <label>
        <span className="sr-only">Archivo de audio</span>
        <input className="input" type="file" name="file" accept="audio/*" required />
      </label>
      <label>
        <span className="sr-only">Título del sonido</span>
        <input
          className="input"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="Título del sonido"
        />
      </label>
      <label>
        <span className="sr-only">Licencia</span>
        <input
          className="input"
          value={license}
          onChange={(event) => setLicense(event.target.value)}
          placeholder="Licencia"
        />
      </label>
      <select
        className="select"
        value={kind}
        onChange={(event) => setKind(event.target.value as "music" | "ambience")}
        aria-label="Tipo de sonido"
      >
        <option value="music">Música</option>
        <option value="ambience">Ambiente</option>
      </select>
      <Button type="submit" loading={upload.isPending}>
        <Upload size={15} />
        Importar
      </Button>
      {upload.isError ? (
        <p className="hint" role="alert">
          {errorMessage(upload.error)}
        </p>
      ) : null}
    </form>
  );
}

function cloneAmbience(data: BookAmbience): AmbiencePlanUpdate {
  return {
    settings: { ...data.settings },
    plan: {
      version: data.plan.version,
      chapters: data.plan.chapters.map((chapter) => ({
        ...chapter,
        bed: chapter.bed ? { ...chapter.bed } : null,
        effects: chapter.effects.map((effect) => ({
          ...effect,
          anchor: { ...effect.anchor },
        })),
      })),
    },
  };
}

function bedFor(asset: SoundAsset, previous: AmbienceBed | null): AmbienceBed {
  return {
    asset_id: asset.id,
    kind: asset.kind === "music" ? "music" : "ambience",
    start_ms: previous?.start_ms ?? 0,
    end_ms: previous?.end_ms ?? null,
    loop: true,
    gain_db: previous?.gain_db ?? (asset.kind === "music" ? -28 : -24),
    fade_in_ms: previous?.fade_in_ms ?? 1_500,
    fade_out_ms: previous?.fade_out_ms ?? 2_000,
    confidence: previous?.confidence ?? 0.9,
    reason: previous?.reason ?? "Elegido a mano",
  };
}

function assetLabel(asset: SoundAsset | undefined, id: string): string {
  return asset ? asset.prompt : id;
}
