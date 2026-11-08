# Release

Vibebook se distribuye como app web local y como app de escritorio Windows.
La primera release pública recomendada es **v0.3.0**, que incluye ambas.

## Checklist previo

- [ ] Todos los PRs de la fase están mergeados en `main`.
- [ ] CI en verde: `test`, `web`, `desktop`, `e2e`.
- [ ] `LICENSE` AGPL-3.0-only presente y referenciado en README.
- [ ] `packaging/THIRD_PARTY_NOTICES.md` revisado.
- [ ] Versiones consistentes: `pyproject.toml`, `web/package.json`,
      `package.json`, `src-tauri/Cargo.toml`, `src-tauri/tauri.conf.json`.
- [ ] `uv run pytest`, `ruff`, `mypy`, `uv build`.
- [ ] `npm run lint`, `typecheck`, `test`, `build`, `e2e`.
- [ ] `npm audit` sin vulnerabilidades.
- [ ] `cargo fmt --check` y `cargo check`.
- [ ] `make sidecar` y `npm run desktop:build` locales.
- [ ] Instalar NSIS/MSI en una máquina limpia y probar importar → convertir →
      leer → karaoke.
- [ ] Probar el ZIP portable con `portable.flag` y una carpeta de solo lectura
      (debe fallar con un mensaje claro, no corromper datos).
- [ ] Verificar que cerrar la app no deja `vibebook-sidecar.exe`.
- [ ] Revisar SmartScreen y documentar que el binario no está firmado.
- [ ] Revisar accesibilidad con axe/Lighthouse y teclado.
- [ ] Revisar seguridad según `SECURITY.md`.

## Artefactos

El workflow `.github/workflows/release-desktop.yml` genera:

- `Vibebook-<versión>-windows-x64.zip` portable.
- `Vibebook_<versión>_x64-setup.exe` (NSIS).
- `Vibebook_<versión>_x64_en-US.msi` (MSI).
- `checksums.txt` con SHA-256.

El ZIP incluye `Vibebook.exe`, `sidecar/vibebook-sidecar.exe`,
`portable.flag`, `LEEME.md` y `THIRD_PARTY_NOTICES.md`.

## Rendimiento observado

Medición local (Windows 11, `dist/vibebook-sidecar.exe`, biblioteca temporal de
100 libros):

- sidecar onefile listo para health: ~4,4 s en el primer arranque (extrae el
  bundle a temporal);
- primer `GET /api/books?limit=100`: ~550 ms (incluye escaneo/DB);
- siguiente listado de 100 libros: ~18 ms;
- proceso Python del sidecar: ~13 MB de working set;
- bundle web: ~478 KB JS + ~349 KB lazy para Epub.js + ~46 KB CSS;
- instaladores NSIS/MSI: ~99 MB; ZIP portable: ~103 MB.

Lighthouse del lector: accesibilidad 1.0 y best practices 1.0. Axe E2E sin
violaciones serious/critical.

## Tag

Después de mergear y verificar `main`:

```powershell
git switch main
git pull --ff-only
git tag -a v0.3.0 -m "Vibebook v0.3.0"
git push origin v0.3.0
```

El tag dispara el workflow de release. Un `workflow_dispatch` manual genera los
artefactos sin publicar el GitHub Release.

## Notas del release

Incluir:

- novedades: lector sincronizado, búsqueda, marcadores, vista EPUB original,
  app Tauri y Azure con word boundaries opcional;
- requisitos: Windows 10/11 x64, WebView2, internet para Edge;
- limitaciones: sin DRM, sin auto-update, sin firma, Edge no oficial;
- licencia AGPL-3.0-only y avisos de terceros;
- checksums.

## Rollback

Si un artefacto sale mal:

1. Marcar el release como pre-release o borrarlo en GitHub.
2. Borrar el tag remoto y local si hace falta:
   `git push origin :refs/tags/v0.3.0` y `git tag -d v0.3.0`.
3. Publicar un patch con el fix y checksums nuevos.
