import { AlertTriangle, Check, Save } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { errorMessage } from "../../api/client";
import {
  useAddPlugin,
  useDeletePlugin,
  useEngines,
  usePlugins,
  useSettings,
  useTestPlugin,
  useUpdateSettings,
  useVoices,
} from "../../api/queries";
import type { Settings } from "../../api/types";
import { Button } from "../../components/Button";
import { Field } from "../../components/Field";
import { PageHeader } from "../../components/PageHeader";
import { useThemeMode } from "../../components/ThemeProvider";
import { formatRate } from "../../lib/format";
import type { ReaderPalette, ThemeMode } from "../../lib/theme";
import { defaultVoiceForEngine, voiceLabel } from "../../lib/voices";

const RATES = ["-20%", "-15%", "-10%", "-5%", "+0%", "+5%"];

export function SettingsPage() {
  const settingsQuery = useSettings();
  const { setMode } = useThemeMode();
  const enginesQuery = useEngines();
  const voicesQuery = useVoices();
  const pluginsQuery = usePlugins();
  const update = useUpdateSettings();
  const addPlugin = useAddPlugin();
  const deletePlugin = useDeletePlugin();
  const testPlugin = useTestPlugin();
  const [form, setForm] = useState<Partial<Settings>>({});
  const [pluginUrl, setPluginUrl] = useState("");
  const [pluginToken, setPluginToken] = useState("");
  const [pluginMessage, setPluginMessage] = useState<string | null>(null);
  const [pluginError, setPluginError] = useState<string | null>(null);
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current || !settingsQuery.data) {
      return;
    }
    setForm(settingsQuery.data);
    initialized.current = true;
  }, [settingsQuery.data]);

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
  const engines = enginesQuery.data?.items ?? [];
  const voices = voicesQuery.data ?? [];
  const plugins = pluginsQuery.data?.items ?? [];
  const selectableEngines = engines.filter(
    (engine) => engine.implemented && engine.available && !engine.test_only,
  );
  const desiredEngine = form.default_engine ?? settings.default_engine;
  const currentEngine: string =
    desiredEngine && selectableEngines.some((engine) => engine.id === desiredEngine)
      ? desiredEngine
      : (selectableEngines[0]?.id ?? "edge");
  const selectedEngine = selectableEngines.find((engine) => engine.id === currentEngine);
  const voiceOptions = voices.filter((voice) => voice.engines.includes(currentEngine));
  const currentVoice = form.default_voice ?? settings.default_voice;
  const selectedVoice = voiceOptions.some((voice) => voice.id === currentVoice)
    ? currentVoice
    : (voiceOptions[0]?.id ?? currentVoice);
  const set = <K extends keyof Settings>(key: K, value: Settings[K]) => {
    update.reset();
    setForm((current) => ({ ...current, [key]: value }));
  };
  const changeEngine = (engine: string) => {
    const keepVoice = voices.some(
      (voice) => voice.id === currentVoice && voice.engines.includes(engine),
    );
    const fallback = defaultVoiceForEngine(engine, voices);
    setForm((current) => ({
      ...current,
      default_engine: engine,
      ...(keepVoice ? {} : fallback ? { default_voice: fallback } : {}),
    }));
  };
  const error = update.isError ? errorMessage(update.error) : null;
  const add = () => {
    setPluginError(null);
    setPluginMessage(null);
    addPlugin.mutate(
      { url: pluginUrl.trim(), token: pluginToken.trim() || null },
      {
        onSuccess: () => {
          setPluginUrl("");
          setPluginToken("");
          setPluginMessage("Plugin agregado.");
        },
        onError: (mutationError) => setPluginError(errorMessage(mutationError)),
      },
    );
  };
  const test = (pluginId: string, pluginName: string) => {
    setPluginError(null);
    setPluginMessage(null);
    testPlugin.mutate(pluginId, {
      onSuccess: (result) =>
        setPluginMessage(`${pluginName}: ${result.message} (${result.latency_ms} ms)`),
      onError: (mutationError) => setPluginError(errorMessage(mutationError)),
    });
  };
  const remove = (pluginId: string) => {
    setPluginError(null);
    setPluginMessage(null);
    deletePlugin.mutate(pluginId, {
      onSuccess: () => setPluginMessage("Plugin eliminado."),
      onError: (mutationError) => setPluginError(errorMessage(mutationError)),
    });
  };
  const save = () => {
    update.mutate({
      default_engine: currentEngine,
      default_voice: selectedVoice,
      default_rate: form.default_rate ?? settings.default_rate,
      theme_mode: form.theme_mode ?? settings.theme_mode,
      reader_palette: form.reader_palette ?? settings.reader_palette,
      reader_font: form.reader_font ?? settings.reader_font,
      reader_size: form.reader_size ?? settings.reader_size,
      auto_scroll: form.auto_scroll ?? settings.auto_scroll,
      skip_seconds: form.skip_seconds ?? settings.skip_seconds,
    });
  };
  const changeThemeMode = (mode: ThemeMode) => {
    set("theme_mode", mode);
    setMode(mode);
  };

  return (
    <div className="page page--narrow">
      <PageHeader
        eyebrow="Ajustes"
        title="Preferencias"
        subtitle="Valores por defecto para convertir, leer y escuchar."
        actions={
          <Button variant="primary" onClick={save} loading={update.isPending}>
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
            <Field
              label="Motor"
              htmlFor="default-engine"
              hint={
                selectedEngine?.description ??
                "Piper y eSpeak NG funcionan sin conexión. Edge suele ser la opción más rápida, pero es un servicio externo; Azure requiere credenciales y cuota mensual."
              }
            >
              <select
                id="default-engine"
                className="select"
                value={currentEngine}
                disabled={selectableEngines.length === 0}
                onChange={(event) => changeEngine(event.target.value)}
              >
                {selectableEngines.map((engine) => (
                  <option key={engine.id} value={engine.id}>
                    {engine.label}
                    {engine.legacy ? " · legado" : ""}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Voz" htmlFor="default-voice">
              <select
                id="default-voice"
                className="select"
                value={selectedVoice}
                onChange={(event) => set("default_voice", event.target.value)}
              >
                {voiceOptions.map((voice) => (
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
              <p className="eyebrow">Apariencia</p>
              <h2>Apariencia</h2>
            </div>
          </div>
          <div className="panel-body settings-section">
            <Field label="Tema de la app">
              <div className="theme-options" role="radiogroup" aria-label="Tema de la app">
                {[
                  { value: "system", label: "Sistema" },
                  { value: "light", label: "Claro" },
                  { value: "dark", label: "Oscuro" },
                ].map((theme) => (
                  <label
                    key={theme.value}
                    className={`theme-option${
                      (form.theme_mode ?? settings.theme_mode) === theme.value ? " is-selected" : ""
                    }`}
                  >
                    <input
                      type="radio"
                      name="theme-mode"
                      value={theme.value}
                      checked={(form.theme_mode ?? settings.theme_mode) === theme.value}
                      onChange={() => changeThemeMode(theme.value as ThemeMode)}
                    />
                    <span className="theme-swatch" data-theme-swatch={theme.value} />
                    {theme.label}
                  </label>
                ))}
              </div>
            </Field>

            <Field
              label="Paleta del lector"
              hint="Cambia solo la página de lectura; el resto de la app conserva su tema."
            >
              <div className="theme-options" role="radiogroup" aria-label="Paleta del lector">
                {[
                  { value: "paper", label: "Papel" },
                  { value: "sepia", label: "Sepia" },
                  { value: "night", label: "Noche" },
                ].map((palette) => (
                  <label
                    key={palette.value}
                    className={`theme-option${
                      (form.reader_palette ?? settings.reader_palette) === palette.value
                        ? " is-selected"
                        : ""
                    }`}
                  >
                    <input
                      type="radio"
                      name="reader-palette"
                      value={palette.value}
                      checked={(form.reader_palette ?? settings.reader_palette) === palette.value}
                      onChange={() => set("reader_palette", palette.value as ReaderPalette)}
                    />
                    <span className="theme-swatch" data-theme-swatch={palette.value} />
                    {palette.label}
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

      <section className="panel" style={{ marginTop: "var(--space-5)" }}>
        <div className="panel-head">
          <div>
            <p className="eyebrow">Motores</p>
            <h2>Plugins VEP</h2>
          </div>
        </div>
        <div className="panel-body settings-section">
          <p className="hint">
            Conectá un motor HTTP/JSON que cumpla <code>vep/1</code>. Vibebook muestra licencia y
            fuente antes de usarlo; el token nunca se devuelve a la interfaz.
          </p>
          <div className="plugin-form">
            <Field label="URL del plugin" htmlFor="plugin-url">
              <input
                id="plugin-url"
                className="input"
                value={pluginUrl}
                onChange={(event) => setPluginUrl(event.target.value)}
                placeholder="http://127.0.0.1:9001"
              />
            </Field>
            <Field
              label="Token opcional"
              htmlFor="plugin-token"
              hint="Se guarda en secrets.json y no se vuelve a mostrar."
            >
              <input
                id="plugin-token"
                className="input"
                type="password"
                value={pluginToken}
                onChange={(event) => setPluginToken(event.target.value)}
                autoComplete="off"
              />
            </Field>
            <Button
              variant="primary"
              onClick={add}
              loading={addPlugin.isPending}
              disabled={!pluginUrl.trim()}
            >
              Agregar plugin
            </Button>
          </div>

          {pluginsQuery.isLoading ? (
            <p className="hint" role="status">
              Cargando plugins…
            </p>
          ) : plugins.length === 0 ? (
            <p className="hint">Todavía no hay plugins registrados.</p>
          ) : (
            <ul className="plugin-list" aria-label="Plugins registrados">
              {plugins.map((plugin) => (
                <li className="plugin-item" key={plugin.id}>
                  <div>
                    <strong>{plugin.name}</strong>{" "}
                    <span className="mono muted">v{plugin.version}</span>
                    <p className="hint">{plugin.url}</p>
                    <p className="hint">
                      {plugin.license} · {plugin.source || "sin fuente"} · {plugin.voice_count}{" "}
                      voces
                      {plugin.has_token ? " · token guardado" : ""}
                    </p>
                  </div>
                  <div className="plugin-actions">
                    <Button
                      variant="ghost"
                      onClick={() => test(plugin.id, plugin.name)}
                      loading={testPlugin.isPending && testPlugin.variables === plugin.id}
                    >
                      Probar
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => remove(plugin.id)}
                      loading={deletePlugin.isPending && deletePlugin.variables === plugin.id}
                    >
                      Eliminar
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {pluginMessage ? (
            <p className="hint" role="status">
              {pluginMessage}
            </p>
          ) : null}
          {pluginError || pluginsQuery.isError ? (
            <div className="alert" role="alert">
              <AlertTriangle size={18} />
              <span>
                {pluginError ??
                  (pluginsQuery.isError ? errorMessage(pluginsQuery.error) : "Error de plugins")}
              </span>
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}
