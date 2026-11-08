# Contribuir a Vibebook

Gracias por querer mejorar Vibebook. El proyecto se distribuye bajo
**AGPL-3.0-only**; al enviar un cambio aceptás que se publique bajo esa licencia.

## Antes de empezar

- Buscá un issue existente o abrí uno para cambios grandes.
- No commitees ni pushees directamente a `main`.
- Creá una rama desde `main` con prefijo `feat/`, `fix/`, `docs/`, `chore/` o
  `refactor/`.
- Si la rama ya tiene un PR abierto, seguí en esa rama y actualizá el PR.

## Entorno

Requisitos:

- Python 3.12 y `uv`.
- Node 22 y `npm`.
- ffmpeg/ffprobe (o `static-ffmpeg` mediante `uv sync`).
- Para escritorio: Rust, Visual Studio Build Tools con C++ y WebView2.

```powershell
uv sync
cd web
npm ci
cd ..
```

## Tests

Antes de abrir o actualizar un PR:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv build

cd web
npm run lint
npm run typecheck
npm run test
npm run build
npm run e2e
```

Si tocaste escritorio:

```powershell
cargo fmt --manifest-path src-tauri/Cargo.toml -- --check
cargo check --manifest-path src-tauri/Cargo.toml
```

Los tests E2E usan Playwright; instalá el browser con
`npx playwright install chromium`.

## Estilo

- Python: ruff y mypy; líneas de 100 caracteres.
- TypeScript/React: Biome, componentes funcionales y hooks.
- Rust: `cargo fmt` y `cargo clippy` cuando aplique.
- Mensajes de commit convencionales: `feat:`, `fix:`, `docs:`, `test:`, `ci:`,
  `chore:`.
- Evitá comentarios que repitan lo que hace el código.

## EPUB y seguridad

- No subas EPUBs con DRM ni libros de los que no tengas derechos.
- Los tests usan `tests/fixtures/` y el motor `Fake`; no requieren red.
- Si tocás el lector original, mantené el sandbox, la CSP y la sanitización.
- No agregues telemetría, autenticación multiusuario ni llamadas a servicios no
  documentados sin discusión previa.

## Pull requests

El PR debe explicar:

- qué cambia y por qué;
- archivos afectados;
- pruebas ejecutadas;
- riesgos y limitaciones;
- breaking changes.

No abras PRs vacíos. Si un cambio es grande, dividilo en commits atómicos.
