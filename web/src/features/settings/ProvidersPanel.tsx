import { AlertTriangle, Check, ExternalLink, KeyRound, Trash2 } from "lucide-react";
import { useState } from "react";

import { errorMessage } from "../../api/client";
import {
  useDeleteProvider,
  useProviders,
  useSaveProvider,
  useTestProvider,
} from "../../api/queries";
import type { ProviderStatus } from "../../api/types";
import { Button } from "../../components/Button";

export function ProvidersPanel() {
  const query = useProviders();

  return (
    <section className="panel" style={{ marginTop: "var(--space-5)" }}>
      <div className="panel-head">
        <div>
          <p className="eyebrow">Voces</p>
          <h2>Proveedores en la nube</h2>
        </div>
        <span className="mono muted">Claves locales</span>
      </div>
      <div className="panel-body settings-section">
        <p className="hint">
          Las claves se guardan en este equipo y nunca se devuelven a la interfaz. También podés
          definirlas con variables de entorno. Después de guardar, elegí el motor en Studio.
        </p>
        {query.isLoading ? <p className="hint">Cargando proveedores…</p> : null}
        {query.isError ? (
          <div className="alert" role="alert">
            <AlertTriangle size={18} />
            <span>{errorMessage(query.error)}</span>
          </div>
        ) : null}
        <div className="provider-grid">
          {(query.data?.items ?? []).map((provider) => (
            <ProviderCard key={provider.id} provider={provider} />
          ))}
        </div>
      </div>
    </section>
  );
}

function ProviderCard({ provider }: { provider: ProviderStatus }) {
  const [apiKey, setApiKey] = useState("");
  const [region, setRegion] = useState(provider.region ?? "");
  const [message, setMessage] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [credits, setCredits] = useState<string | null>(null);
  const save = useSaveProvider();
  const remove = useDeleteProvider();
  const test = useTestProvider();
  const error = save.isError
    ? errorMessage(save.error)
    : remove.isError
      ? errorMessage(remove.error)
      : test.isError
        ? errorMessage(test.error)
        : null;
  const inputId = `provider-${provider.id}-key`;
  const regionId = `provider-${provider.id}-region`;

  const submit = () => {
    setMessage(null);
    setWarning(null);
    save.mutate(
      { providerId: provider.id, apiKey: apiKey.trim(), region: region.trim() || undefined },
      {
        onSuccess: (updated) => {
          setApiKey("");
          setMessage(
            updated.configured
              ? "Clave guardada. El motor ya está disponible en Studio."
              : "Clave guardada.",
          );
        },
      },
    );
  };

  const runTest = () => {
    setMessage(null);
    setWarning(null);
    setCredits(null);
    test.mutate(provider.id, {
      onSuccess: (result) => {
        setMessage(result.message);
        setWarning(result.warning ?? null);
        if (result.credits_limit != null) {
          const used = result.credits_used ?? 0;
          setCredits(
            `Saldo: ${(result.credits_limit - used).toLocaleString("es")} de ` +
              `${result.credits_limit.toLocaleString("es")} créditos.`,
          );
        }
      },
    });
  };

  const clear = () => {
    setMessage(null);
    setWarning(null);
    setCredits(null);
    remove.mutate(provider.id, {
      onSuccess: () => setMessage("Clave eliminada."),
    });
  };

  return (
    <article
      className={`provider-card${provider.configured ? " is-configured" : ""}`}
      aria-label={provider.label}
    >
      <div className="provider-head">
        <div>
          <h3>{provider.label}</h3>
          <p className="hint">{provider.description}</p>
        </div>
        <span className={`provider-status${provider.configured ? " is-on" : ""}`}>
          {provider.configured ? <Check size={13} /> : <KeyRound size={13} />}
          {provider.configured ? "Conectado" : "Sin configurar"}
        </span>
      </div>

      {provider.configured ? (
        <p className="provider-hint mono">
          {provider.hint}
          {provider.source === "env" ? " · variable de entorno" : " · guardada en este equipo"}
          {provider.region ? ` · ${provider.region}` : ""}
        </p>
      ) : null}

      <div className="provider-form">
        <label className="label" htmlFor={inputId}>
          {provider.configured ? "Reemplazar clave" : "Clave de API"}
        </label>
        <input
          id={inputId}
          className="input"
          type="password"
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
          placeholder={provider.configured ? "Pegar una clave nueva" : "Pegar clave"}
          autoComplete="off"
          spellCheck={false}
        />
        {provider.requires_region ? (
          <>
            <label className="label" htmlFor={regionId}>
              Región
            </label>
            <input
              id={regionId}
              className="input"
              value={region}
              onChange={(event) => setRegion(event.target.value)}
              placeholder="eastus"
              autoComplete="off"
            />
          </>
        ) : null}
        <div className="provider-actions">
          <Button
            variant="primary"
            onClick={submit}
            loading={save.isPending}
            disabled={apiKey.trim().length < 8 || (provider.requires_region && !region.trim())}
          >
            Guardar clave
          </Button>
          <Button
            variant="ghost"
            onClick={runTest}
            loading={test.isPending}
            disabled={!provider.configured}
          >
            Probar
          </Button>
          {provider.configured && provider.source !== "env" ? (
            <Button variant="ghost" onClick={clear} loading={remove.isPending}>
              <Trash2 size={15} />
              Quitar
            </Button>
          ) : null}
        </div>
      </div>

      <div className="provider-links">
        <a href={provider.key_url} target="_blank" rel="noreferrer">
          Obtener clave <ExternalLink size={12} />
        </a>
        <a href={provider.docs_url} target="_blank" rel="noreferrer">
          Documentación <ExternalLink size={12} />
        </a>
      </div>

      {message ? (
        <p className="provider-message" role="status">
          {message}
        </p>
      ) : null}
      {credits ? <p className="provider-message mono">{credits}</p> : null}
      {warning ? <p className="provider-warning">{warning}</p> : null}
      {error ? (
        <div className="alert" role="alert">
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      ) : null}
    </article>
  );
}
