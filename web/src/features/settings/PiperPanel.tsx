import { AlertTriangle, ExternalLink, FolderOpen, Terminal } from "lucide-react";
import { useEffect, useState } from "react";

import { errorMessage } from "../../api/client";
import { usePiper, useSavePiper } from "../../api/queries";
import { Button } from "../../components/Button";

const PIPER_RELEASES = "https://github.com/rhasspy/piper/releases";

export function PiperPanel() {
  const query = usePiper();
  const save = useSavePiper();
  const [binary, setBinary] = useState("");
  const [voicesDir, setVoicesDir] = useState("");
  const [espeakData, setEspeakData] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!query.data) {
      return;
    }
    setBinary(query.data.binary ?? "");
    setVoicesDir(query.data.voices_dir ?? "");
    setEspeakData(query.data.espeak_data ?? "");
  }, [query.data]);

  const status = query.data;
  const error = save.isError ? errorMessage(save.error) : null;

  const submit = () => {
    setMessage(null);
    save.mutate(
      {
        binary: binary.trim() || null,
        voices_dir: voicesDir.trim() || null,
        espeak_data: espeakData.trim() || null,
      },
      {
        onSuccess: (updated) => {
          setMessage(
            updated.binary_configured
              ? "Piper configurado. El motor ya está disponible en Estudio."
              : "Rutas guardadas. Falta el binario de Piper para poder convertir.",
          );
        },
      },
    );
  };

  return (
    <section className="panel" style={{ marginTop: "var(--space-5)" }}>
      <div className="panel-head">
        <div>
          <p className="eyebrow">Voces</p>
          <h2>Piper neural (local)</h2>
        </div>
        <span className="mono muted">Sin cuenta</span>
      </div>
      <div className="panel-body settings-section">
        <p className="hint">
          Piper corre en CPU y no envía texto a la nube. Necesita el binario de Piper y una carpeta
          con voces <code>.onnx</code> + <code>.onnx.json</code>. Si venís de la app Flutter, podés
          reutilizar sus voces.
        </p>

        {query.isLoading ? <p className="hint">Leyendo la configuración de Piper…</p> : null}
        {query.isError ? (
          <div className="alert" role="alert">
            <AlertTriangle size={18} />
            <span>{errorMessage(query.error)}</span>
          </div>
        ) : null}

        <div className="settings-grid">
          <label className="field">
            <span className="label">Binario de Piper</span>
            <input
              className="input"
              value={binary}
              onChange={(event) => setBinary(event.target.value)}
              placeholder="C:\\ruta\\piper.exe o piper"
              aria-label="Binario de Piper"
            />
            <span className="hint">
              Ruta a <code>piper.exe</code> o el comando si está en el PATH.
            </span>
          </label>
          <label className="field">
            <span className="label">Carpeta de voces</span>
            <input
              className="input"
              value={voicesDir}
              onChange={(event) => setVoicesDir(event.target.value)}
              placeholder="C:\\ruta\\voces"
              aria-label="Carpeta de voces Piper"
            />
            <span className="hint">
              Se aceptan modelos planos o carpetas <code>vits-piper-*</code>.
            </span>
          </label>
        </div>

        <label className="field">
          <span className="label">espeak-ng-data (opcional)</span>
          <input
            className="input"
            value={espeakData}
            onChange={(event) => setEspeakData(event.target.value)}
            placeholder="C:\\ruta\\espeak-ng-data"
            aria-label="Datos de espeak-ng para Piper"
          />
        </label>

        <div className="continue-actions" style={{ marginTop: "var(--space-3)" }}>
          <Button onClick={submit} loading={save.isPending}>
            <Terminal size={16} />
            Guardar y detectar
          </Button>
          <Button variant="ghost" onClick={() => void query.refetch()}>
            <FolderOpen size={16} />
            Volver a leer
          </Button>
          <a className="link-button" href={PIPER_RELEASES} target="_blank" rel="noreferrer">
            Descargar Piper <ExternalLink size={14} />
          </a>
        </div>

        {error ? (
          <div className="alert" role="alert" style={{ marginTop: "var(--space-3)" }}>
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        ) : null}
        {message ? (
          <p className="hint" role="status">
            {message}
          </p>
        ) : null}

        {status ? (
          <>
            <div
              className={`alert${status.binary_configured ? "" : " alert--warning"}`}
              style={{ marginTop: "var(--space-3)" }}
              role="status"
            >
              {status.binary_configured ? (
                <>
                  <Terminal size={18} />
                  <span>
                    Binario detectado: <code className="mono">{status.binary}</code>
                  </span>
                </>
              ) : (
                <>
                  <AlertTriangle size={18} />
                  <span>
                    Falta el binario de Piper. Guardá la ruta o agregalo al PATH para habilitar el
                    motor.
                  </span>
                </>
              )}
            </div>

            {status.suggestions.length > 0 ? (
              <div style={{ marginTop: "var(--space-3)" }}>
                <p className="label">Carpetas detectadas</p>
                <div className="continue-actions">
                  {status.suggestions.map((suggestion) => (
                    <Button
                      key={suggestion.path}
                      variant="ghost"
                      onClick={() => setVoicesDir(suggestion.path)}
                    >
                      <FolderOpen size={16} />
                      {suggestion.label}
                    </Button>
                  ))}
                </div>
              </div>
            ) : null}

            <div style={{ marginTop: "var(--space-3)" }}>
              <p className="label">Voces detectadas · {status.voices.length}</p>
              {status.voices.length === 0 ? (
                <p className="hint">
                  No se detectaron voces en esa carpeta. Elegí la carpeta de la app anterior o
                  descargá una voz con <code>vibebook piper download</code>.
                </p>
              ) : (
                <ul className="plugin-list" aria-label="Voces Piper detectadas">
                  {status.voices.map((voice) => (
                    <li className="plugin-item" key={voice.id}>
                      <div>
                        <strong>{voice.name}</strong> <span className="mono muted">{voice.id}</span>
                        <p className="hint">
                          {voice.locale} · {voice.gender} · {voice.path}
                        </p>
                      </div>
                      <span className="mono muted">Disponible</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {status.errors.length > 0 ? (
              <div className="alert" role="alert" style={{ marginTop: "var(--space-3)" }}>
                <AlertTriangle size={18} />
                <span>{status.errors.join(" · ")}</span>
              </div>
            ) : null}
          </>
        ) : null}

        <p className="hint" style={{ marginTop: "var(--space-3)" }}>
          Piper es GPL-3.0 y se ejecuta como proceso separado. La app no descarga binarios
          automáticamente; las voces se pueden descargar con el comando{" "}
          <code>vibebook piper download</code>.
        </p>
      </div>
    </section>
  );
}
