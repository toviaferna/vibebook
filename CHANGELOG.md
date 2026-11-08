# Changelog

## v0.3.0 — 2026-11-08

Primera release pública.

### Agregado

- Lector sincronizado con karaoke por palabra, auto-scroll, temas y atajos.
- Búsqueda accent-insensitive y marcadores persistentes.
- Vista del EPUB original con sandbox y sanitización.
- App de escritorio Tauri con sidecar Python, instaladores Windows y ZIP portable.
- Word boundaries de Azure mediante el extra opcional `azure-sdk`.
- Suite E2E con Playwright y chequeos axe.

### Licencia

- Proyecto bajo GNU AGPL v3.0 only. Ver `LICENSE` y
  `packaging/THIRD_PARTY_NOTICES.md`.

### Limitaciones conocidas

- Windows x64 para la app de escritorio.
- Sin firma de código ni auto-update.
- Edge TTS es un servicio no oficial.
- EPUB con DRM no soportado.
