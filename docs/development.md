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
uv run vibebook voices --locale es-MX
uv run vibebook convert libro.epub --voice es-MX-JorgeNeural --rate -6%
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy src
```

También:

```bash
make sync
make test
make lint
make format
make typecheck
make check
```

## ffmpeg

`audiol.tools.find_binary()` resuelve, en orden:

1. `FFMPEG_BINARY` / `FFPROBE_BINARY`.
2. `PATH`.
3. `.tools/bin` del repositorio.
4. `static-ffmpeg` (descarga la primera vez).

No hace falta `source scripts/env.sh`.

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
tests/              tests unitarios e integración con ffmpeg
docs/               arquitectura y desarrollo
scripts/            herramientas de muestras y bake-off
```

## Convenciones

- Cada cambio debe pasar `uv run pytest`.
- Los tests unitarios no usan red; Edge/Azure se prueban con dobles o manualmente.
- Los tests de ffmpeg usan `find_binary` y se saltan si no hay binario disponible.
- Antes de un PR: `make check`.
