# Changelog

## v0.4.1 — 2026-11-09

### Agregado

- APK Android lector-only firmado en CI y adjunto como asset experimental.
- Swipe horizontal y “Fin del libro” en el lector.

### Cambiado

- Lector: transición de página natural en lugar del giro 3D con hoja vacía.
- Lector: al llegar a la última página se pasa al capítulo siguiente; al
  retroceder en la primera se vuelve al capítulo anterior.
- Lector: la posición se conserva al cambiar tipografía/tamaño y se restaura si
  el estado de lectura llega tarde.
- Lector: swipe horizontal en mobile, rango de páginas y “Fin del libro”.

## v0.4.0 — 2026-11-08

Release de identidad, ambientación y plataformas.

### Agregado

- Identidad **Verdín** (I1–I5): contexto de diseño, tres direcciones, tokens,
  temas claro/oscuro, marca, estante, detalle, lector, ajustes y QA visual.
- Ambientación open source (A1–A6): biblioteca de sonidos, camas procedurales,
  plan por capítulo, analizador heurístico, mezcla Web Audio, M4B ambientado y
  providers opcionales de Freesound/plugin local.
- Sincronía karaoke Y1–Y4: diagnóstico, offsets PCM, cliente estable,
  calibración del encoder y `repair-sync`.
- Linux x64 (AppImage/deb) y macOS arm64/x64 (DMG unsigned).
- Workflow de release multi-plataforma con checksums y un único GitHub Release.
- Android lector-only MVP: file picker, IndexedDB, Epub.js y CFI persistente.
- Capturas de identidad, informe de contraste, axe y presupuesto de rendimiento.

### Cambiado

- El lector separa `theme_mode` de la app y `reader_palette` de la lectura.
- La UI deja la paleta crema/terracota por Verdín.
- Los assets de ambiente requieren licencia y aprobación explícita.

### Limitaciones conocidas

- macOS y Windows sin firma de código; SmartScreen/Gatekeeper pueden advertir.
- Android es un MVP lector-only; falta validar APK en CI/dispositivo y agregar
  SAF nativo, SQLite y audio local.
- Sin auto-update ni cuenta/cloud.
- Edge/Azure siguen como legado opt-in; el default es Piper/eSpeak local.
- Freesound y plugins de sonido son opcionales y no se configuran solos.

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
