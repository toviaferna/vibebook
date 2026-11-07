# Desarrollo

## Entorno

El proyecto usa `uv`; no hay que activar ningún venv.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

`uv` instala Python 3.12 y las dependencias del proyecto y de desarrollo.
`pythonpath = ["src"]` permite ejecutar pytest sin instalar el paquete a mano,
aunque `uv sync` ya lo instala en editable.

## Comandos

```bash
uv run vibebook --help
uv run vibebook --version
uv run vibebook voices --locale es-MX
uv run vibebook convert libro.epub --voice es-MX-JorgeNeural --rate -10%
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy src
uv build
```

También:

```bash
make sync
make test
make lint
make format
make typecheck
make check
make build
make web-install
make web-check
make sidecar
```

La UI vive en `web/`: React, TypeScript y Vite. `npm run dev` usa el proxy
`/api` hacia `127.0.0.1:8765`; `vibebook studio` sirve `web/dist` cuando existe.

### Escritorio

La app Tauri vive en `src-tauri/`. Requiere Rust estable, Visual Studio Build
Tools con el workload C++ y WebView2.

```powershell
npm ci
npm ci --prefix web
uv sync
make sidecar
npm run desktop:dev
npm run desktop:check
npm run desktop:build
```

`make sidecar` construye `web/dist` y `dist/vibebook-sidecar.exe`. Tauri lo copia
como recurso y lo lanza al abrir la ventana. El detalle está en
[desktop.md](desktop.md).

## E2E

Los tests end-to-end usan Playwright, levantan el backend con motor fake y Vite,
y cubren importar → convertir → leer → recargar, además de axe.

```powershell
cd web
npx playwright install chromium
npm run e2e
npm run e2e:ui
```

También se pueden correr desde la raíz con `npm run e2e`. Los fixtures viven en
`tests/fixtures/` y se regeneran con
`uv run python scripts/make-e2e-fixtures.py`.

## ffmpeg

`audiol.tools.find_binary()` resuelve, en orden:

1. `FFMPEG_BINARY` / `FFPROBE_BINARY`.
2. `PATH`.
3. `.tools/bin` del repositorio.
4. `static-ffmpeg` (descarga la primera vez).

No hace falta activar un venv ni exportar rutas a mano.

## Azure

```bash
export AZURE_SPEECH_KEY="..."
export AZURE_SPEECH_REGION="eastus"
uv run vibebook convert libro.epub \
  --engine azure \
  --voice es-MX-JorgeNeural \
  --style cheerful
```

La cuota gratuita F0 de Azure Speech es 0,5 M de caracteres al mes.

## CI

`.github/workflows/ci.yml` ejecuta:

- `uv sync --frozen`
- `ruff check`
- `ruff format --check`
- `mypy src`
- `pytest`
- `uv build`
- `npm run lint`, `typecheck`, `test`, `build`
- En Windows: PyInstaller del sidecar, `cargo fmt --check` y `cargo check`.
- En Linux: Playwright E2E con motor fake y axe.

## Estructura

```text
src/audiol/
  ingest/epub.py    lectura de EPUB
  clean.py          limpieza de texto
  chunk.py          segmentación
  tts/              proveedores Edge, Azure y fake
  convert.py        orquestador y caché
  assemble.py       ffmpeg y M4B
  cli.py            comandos vibebook/audiol
  tools.py          descubrimiento de binarios
  studio/           biblioteca, API, jobs y servidor local
web/                UI React/Vite (biblioteca, estudio, lector, ajustes)
src-tauri/          shell Tauri y lifecycle del sidecar
packaging/          PyInstaller, iconos y avisos de terceros
tests/              tests unitarios e integración con ffmpeg
tests/studio/       tests de API, jobs, lector y CLI
docs/               arquitectura, desarrollo, roadmap y archivo histórico
scripts/            herramientas de muestras y bake-off
```

## Convenciones

- Cada cambio debe pasar `uv run pytest`.
- Los tests unitarios no usan red; Edge/Azure se prueban con dobles o manualmente.
- Los tests de ffmpeg usan `find_binary` y se saltan si no hay binario disponible.
- Antes de un PR: `make check`.
