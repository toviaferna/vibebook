# Release

Vibebook se distribuye como app local y como app de escritorio para Windows,
Linux y macOS. La release recomendada es **v0.4.0**. Android ya tiene un MVP
lector-only, pero su APK no se publica hasta validarlo en CI y en un dispositivo.

**Estado:** v0.4.0 publicado el 2026-11-09 con Windows x64, Linux x64 y macOS
arm64/x64. Los checksums de los 7 artefactos se verificaron contra los digests
de GitHub. Android sigue fuera del Release hasta validar el APK.

## Checklist previo

- [ ] Todos los PRs de la ola están mergeados en `main`.
- [ ] CI en verde: `test`, `web`, `desktop`, `desktop-linux`, `e2e`.
- [ ] Release workflow verificado: macOS arm64/x64 se construyen en el tag con
      macos-15/macos-15-intel y los artefactos anidados se publican con `**`.
- [ ] `LICENSE` AGPL-3.0-only presente y referenciado en README.
- [ ] `packaging/THIRD_PARTY_NOTICES.md` revisado.
- [ ] Versiones consistentes: `pyproject.toml`, `package.json`,
      `web/package.json`, `src-tauri/Cargo.toml`, `src-tauri/tauri.conf.json`,
      `src-tauri/Cargo.lock`.
- [ ] `uv run pytest`, `ruff`, `mypy`, `uv build`.
- [ ] `cd web && npm run lint && npm run typecheck && npm run test && npm run build`.
- [ ] `cd web && npm run check:bundle && npm run e2e`.
- [ ] `cargo fmt --check` y `cargo check` en las tres plataformas.
- [ ] `npm run sidecar` y `npm run desktop:build` locales.
- [ ] Instalar NSIS/MSI en una máquina limpia: importar → convertir → leer →
      karaoke → exportar ambientado.
- [ ] Probar AppImage/deb en Ubuntu 22.04/24.04 y Debian 12.
- [ ] Probar DMG arm64/x64; documentar Gatekeeper y `xattr`.
- [ ] Verificar checksums y que cerrar la app no deja el sidecar vivo.
- [ ] Revisar SmartScreen, axe/Lighthouse y `SECURITY.md`.

## Artefactos

El workflow `.github/workflows/release.yml` genera:

- Windows: `Vibebook-<versión>-windows-x64.zip`,
  `Vibebook_<versión>_x64-setup.exe`, `Vibebook_<versión>_x64_en-US.msi`.
- Linux: `Vibebook_<versión>_amd64.AppImage`, `Vibebook_<versión>_amd64.deb`.
- macOS: `Vibebook_<versión>_aarch64.dmg`, `Vibebook_<versión>_x64.dmg`.
- `checksums-windows.txt`, `checksums-linux.txt`, `checksums-macos-arm64.txt`,
  `checksums-macos-x64.txt`.
- Un único GitHub Release con todos los artefactos.

Los jobs de plataforma no publican releases individuales. El job `release`
solo corre con tags `v*` y falla si falta un artefacto.

## Rendimiento observado

Medición local (Windows 11, sidecar onefile, biblioteca temporal de 100 libros):

- sidecar onefile listo para health: ~4,4 s;
- primer `GET /api/books?limit=100`: ~550 ms;
- listado caliente de 100 libros: ~18 ms;
- proceso Python del sidecar: ~13 MB;
- bundle web: ~150 KiB JS gzip + ~11 KiB CSS gzip + Epub.js lazy;
- instaladores NSIS/MSI: ~99 MB; ZIP portable: ~103 MB.

Lighthouse del lector: accesibilidad 1.0 y best practices 1.0. Axe E2E sin
violaciones serious/critical.

## Tag

Después de mergear y verificar `main`:

```powershell
git switch main
git pull --ff-only
git tag -a v0.4.0 -m "Vibebook v0.4.0 — Verdín, ambiente y plataformas"
git push origin v0.4.0
```

El tag dispara el Release. Un `workflow_dispatch` manual construye artefactos
sin publicar si no es un tag.

## Notas del release

El body del Release describe requisitos, artefactos y limitaciones. Después de
publicarlo, revisar:

- novedades: Verdín, lector, ambientación, M4B, sync, Linux/macOS;
- requisitos: Windows/WebView2, Linux/WebKitGTK/FUSE, macOS unsigned;
- limitaciones: sin firma, sin Android todavía, sin auto-update, Edge legado;
- licencia AGPL-3.0-only y avisos de terceros;
- checksums por plataforma.

Para reemplazar el body, editá el Release en GitHub o usá `PATCH
/repos/{owner}/{repo}/releases/{id}` con `body`.

## Verificación post-publicación

- Confirmar `tag_name`, `draft=false`, `prerelease=false` y que el tag apunte al
  commit de `main`.
- Confirmar 7 artefactos: ZIP/NSIS/MSI de Windows, AppImage/deb de Linux y dos
  DMG de macOS, más los 4 `checksums-*.txt`.
- Comparar cada línea de los checksums con el `digest` SHA-256 del asset en la
  API de GitHub.
- Descargar al menos un artefacto por plataforma y verificar su hash local.
- Revisar el body: requisitos, artefactos, Android fuera del Release y aviso de
  macOS unsigned.

## Rollback

Si un artefacto sale mal:

1. Marcar el Release como pre-release o borrarlo en GitHub.
2. Borrar el tag remoto/local si hace falta:
   `git push origin :refs/tags/v0.4.0` y `git tag -d v0.4.0`.
3. Publicar un patch con el fix y checksums nuevos.

No se reutiliza un tag ya publicado para artefactos distintos.
