import { AlertTriangle, Check, Save } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { errorMessage } from "../../api/client";
import { useSettings, useUpdateSettings, useVoices } from "../../api/queries";
import type { Settings } from "../../api/types";
import { Button } from "../../components/Button";
import { Field } from "../../components/Field";
import { PageHeader } from "../../components/PageHeader";
import { formatRate } from "../../lib/format";
import { voiceLabel } from "../../lib/voices";

const RATES = ["-20%", "-15%", "-10%", "-5%", "+0%", "+5%"];

export function SettingsPage() {
  const settingsQuery = useSettings();
  const voicesQuery = useVoices();
  const update = useUpdateSettings();
  const [form, setForm] = useState<Partial<Settings>>({});
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current || !settingsQuery.data) {
      return;
    }
    setForm(settingsQuery.data);
    initialized.current = true;
  }, [settingsQuery.data]);

  useEffect(() => {
    if (form.reader_theme) {
      document.body.dataset.theme = form.reader_theme;
    }
  }, [form.reader_theme]);

  if (settingsQuery.isLoading || !settingsQuery.data) {
    return (
      <div className="page page--narrow">
        <div className="page-loading">
          <div className="skeleton skeleton--title" />
          <div className="skeleton skeleton--card" />
        </div>
      </div>
    );
  }

  const settings = settingsQuery.data;
  const voices = voicesQuery.data ?? [];
  const set = <K extends keyof Settings>(key: K, value: Settings[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };
  const error = update.isError ? errorMessage(update.error) : null;

  return (
    <div className="page page--narrow">
      <PageHeader
        eyebrow="Ajustes"
        title="Preferencias del taller"
        subtitle="Valores por defecto para convertir y para la futura lectura sincronizada."
        actions={
          <Button variant="primary" onClick={() => update.mutate(form)} loading={update.isPending}>
            {update.isSuccess ? <Check size={17} /> : <Save size={17} />}
            {update.isSuccess ? "Guardado" : "Guardar"}
          </Button>
        }
      />

      {error ? (
        <div className="alert" role="alert" style={{ marginBottom: "var(--space-5)" }}>
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="settings-grid">
        <section className="panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Conversión</p>
              <h2>Voz por defecto</h2>
            </div>
          </div>
          <div className="panel-body settings-section">
            <Field label="Voz" htmlFor="default-voice">
              <select
                id="default-voice"
                className="select"
                value={form.default_voice ?? settings.default_voice}
                onChange={(event) => set("default_voice", event.target.value)}
              >
                {voices.map((voice) => (
                  <option key={voice.id} value={voice.id}>
                    {voiceLabel(voice).name} · {voiceLabel(voice).detail}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Velocidad" htmlFor="default-rate">
              <select
                id="default-rate"
                className="select"
                value={form.default_rate ?? settings.default_rate}
                onChange={(event) => set("default_rate", event.target.value)}
              >
                {RATES.map((rate) => (
                  <option key={rate} value={rate}>
                    {formatRate(rate)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Biblioteca" hint="La ruta se cambia al arrancar Studio con --library.">
              <p className="mono muted">{settings.library_dir}</p>
            </Field>
            <div className="summary-row">
              <span>Azure</span>
              <strong>{settings.azure_configured ? "Configurado" : "Sin configurar"}</strong>
            </div>
          </div>
        </section>

        <section className="panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Lectura</p>
              <h2>Tu espacio</h2>
            </div>
          </div>
          <div className="panel-body settings-section">
            <Field label="Tema">
              <div className="theme-options" role="radiogroup" aria-label="Tema de lectura">
                {[
                  { value: "light", label: "Claro" },
                  { value: "sepia", label: "Sepia" },
                  { value: "night", label: "Noche" },
                ].map((theme) => (
                  <label
                    key={theme.value}
                    className={`theme-option${
                      (form.reader_theme ?? settings.reader_theme) === theme.value
                        ? " is-selected"
                        : ""
                    }`}
                  >
                    <input
                      type="radio"
                      name="reader-theme"
                      value={theme.value}
                      checked={(form.reader_theme ?? settings.reader_theme) === theme.value}
                      onChange={() => set("reader_theme", theme.value as Settings["reader_theme"])}
                    />
                    <span className="theme-swatch" data-theme-swatch={theme.value} />
                    {theme.label}
                  </label>
                ))}
              </div>
            </Field>

            <Field label="Tipografía" htmlFor="reader-font">
              <select
                id="reader-font"
                className="select"
                value={form.reader_font ?? settings.reader_font}
                onChange={(event) =>
                  set("reader_font", event.target.value as Settings["reader_font"])
                }
              >
                <option value="serif">Serif editorial</option>
                <option value="sans">Sans clara</option>
                <option value="hyperlegible">Hiperlegible</option>
              </select>
            </Field>

            <Field label={`Tamaño de texto · ${form.reader_size ?? settings.reader_size}px`}>
              <input
                className="range"
                type="range"
                min={14}
                max={28}
                step={1}
                value={form.reader_size ?? settings.reader_size}
                onChange={(event) => set("reader_size", Number(event.target.value))}
              />
            </Field>

            <label className="label" htmlFor="auto-scroll">
              <input
                id="auto-scroll"
                type="checkbox"
                checked={form.auto_scroll ?? settings.auto_scroll}
                onChange={(event) => set("auto_scroll", event.target.checked)}
              />{" "}
              Seguir el texto automáticamente
            </label>

            <Field label="Salto de audio" htmlFor="skip-seconds">
              <select
                id="skip-seconds"
                className="select"
                value={form.skip_seconds ?? settings.skip_seconds}
                onChange={(event) => set("skip_seconds", Number(event.target.value))}
              >
                {[10, 15, 20, 30].map((seconds) => (
                  <option key={seconds} value={seconds}>
                    {seconds} segundos
                  </option>
                ))}
              </select>
            </Field>
          </div>
        </section>
      </div>
    </div>
  );
}
