# Release

Vibebook se distribuye como app local y como app de escritorio para Windows,
Linux y macOS. La release recomendada es **v0.6.0**, la ola de integridad,
seguridad, lector P1 y audio versionado. Android se publica como APK lector-only
experimental, firmado en CI.

**Estado:** v0.6.0 publicado el 2026-11-10 con 13 assets: Windows ZIP/NSIS/MSI,
Linux AppImage/DEB, macOS arm64/x64, APK Android y checksums por plataforma.
Incluye conversión atómica, tickets de medios, CSP de Tauri, persistencia de
lectura con secuencia, paginación corregida, segmentación versionada y Flatpak.
El APK sigue sin probarse en un dispositivo físico; SAF/SQLite/audio local y
on-device quedan pendientes.

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

El workflow `.github/workflows/release.yml` genera los artefactos de escritorio;
el workflow `.github/workflows/android.yml` genera el APK en tags `v*` o manual.

El Release incluye:

- Windows: `Vibebook-<versión>-windows-x64.zip`,
  `Vibebook_<versión>_x64-setup.exe`, `Vibebook_<versión>_x64_en-US.msi`.
- Linux: `Vibebook_<versión>_amd64.AppImage`, `Vibebook_<versión>_amd64.deb`.
- macOS Intel: `Vibebook_<versión>_x64.dmg`. El arm64 nativo requiere un runner
  `macos-15`; si la cuenta alcanza su límite de gasto, el Release sale sin ese
  DMG y se documenta en el body.
- Android: `Vibebook-<versión>-android-arm64.apk` (experimental, firmado en CI).
- `checksums-windows.txt`, `checksums-linux.txt`, `checksums-macos-x64.txt`,
  `checksums-android.txt`; `checksums-macos-arm64.txt` cuando existe el DMG.
- Un único GitHub Release con todos los artefactos disponibles.

Los jobs de plataforma no publican releases individuales. El job `release`
solo corre con tags `v*` y falla si falta un artefacto.

## Rendimiento observado

Medición local (Windows 11, sidecar onefile, biblioteca temporal de 100 libros):

- sidecar onefile listo para health: ~4,4 s;
- primer `GET /api/books?limit=100`: ~550 ms;
- listado caliente de 100 libros: ~18 ms;
- proceso Python del sidecar: ~13 MB;
- bundle web: ~118 KiB JS gzip + ~8 KiB CSS gzip + Epub.js lazy;
- instaladores NSIS/MSI: ~99 MB; ZIP portable: ~103 MB.

Lighthouse del lector: accesibilidad 1.0 y best practices 1.0. Axe E2E sin
violaciones serious/critical.

## Tag

Después de mergear y verificar `main`:

```powershell
git switch main
git pull --ff-only
git tag -a v0.6.0 -m "Vibebook v0.6.0 — integridad, seguridad y lector P1"
git push origin v0.6.0
```

El tag dispara el Release. Un `workflow_dispatch` manual construye artefactos
sin publicar si no es un tag.

## Known issue v0.5.0 (histórico)

- El DMG **macOS arm64 nativo** no se publicó por el límite de gasto de GitHub.
  En v0.6.0 se reintenta el runner `macos-15`; si vuelve a fallar, el Release
  documenta la ausencia y publica x64. Para completar el arm64:
  1. restablecer el límite de gasto en GitHub Billing;
  2. correr de nuevo el workflow `Release` sobre el tag;
  3. adjuntar `Vibebook_0.6.0_aarch64.dmg` y `checksums-macos-arm64.txt` si el
     job `release` no los sube solo.

## Notas del release

El body del Release describe requisitos, artefactos y limitaciones. Después de
publicarlo, revisar:

- novedades: segmentación TTS, reparación incremental, Biblioteca, responsive,
  rendimiento, ambientación, M4B, sync, Linux/macOS;
- requisitos: Windows/WebView2, Linux/WebKitGTK/FUSE, macOS unsigned;
- limitaciones: sin firma, sin Android todavía, sin auto-update, Edge legado;
- licencia AGPL-3.0-only y avisos de terceros;
- checksums por plataforma.

Para reemplazar el body, editá el Release en GitHub o usá `PATCH
/repos/{owner}/{repo}/releases/{id}` con `body`.

## Verificación post-publicación

- Confirmar `tag_name`, `draft=false`, `prerelease=false` y que el tag apunte al
  commit de `main`.
- Confirmar los artefactos de escritorio disponibles: ZIP/NSIS/MSI de Windows,
  AppImage/deb de Linux y DMG de macOS (x64 y arm64 cuando el runner esté
  disponible), más los `checksums-*.txt` correspondientes.
- Confirmar el APK Android experimental y `checksums-android.txt` adjuntos al
  Release.
- Comparar cada línea de los checksums con el `digest` SHA-256 del asset en la
  API de GitHub.
- Descargar al menos un artefacto por plataforma y verificar su hash local.
- Revisar el body: requisitos, artefactos, APK Android adjunto y aviso de
  macOS unsigned.

## Rollback

Si un artefacto sale mal:

1. Marcar el Release como pre-release o borrarlo en GitHub.
2. Borrar el tag remoto/local si hace falta:
   `git push origin :refs/tags/v0.5.0` y `git tag -d v0.5.0`.
3. Publicar un patch con el fix y checksums nuevos.

No se reutiliza un tag ya publicado para artefactos distintos.
