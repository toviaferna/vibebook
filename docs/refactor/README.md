# Refactorización Flutter: investigación y plan

> **Estado (2026-11-18):** implementación inicial en `app/`, PR #84. Ya
> funcionan biblioteca, importación EPUB, lector, TTS local Piper, karaoke,
> búsqueda, bookmarks, ambiente, M4B normal/ambientado e instaladores sin
> firma. Quedan pendientes audio en segundo plano, Drift/FTS5, lector
> paginado/Original, proveedores cloud y auto-update. **La app Tauri/Python
> sigue siendo la release estable; no hubo cutover, tag ni release.**
> Fecha de la investigación original: 2026-11-17.
> Rama de implementación: `feat/flutter-app`.

## Resumen ejecutivo

Vibebook funciona en Windows, Linux y macOS con Tauri + React + un sidecar Python.
Android fue históricamente un lector aislado porque el sidecar Python no puede
ejecutarse con PyInstaller en Android. El problema no es Tauri en sí: es dónde
corre el motor que hace EPUB, TTS, ffmpeg, M4B y ambientación.

La investigación concluye que **Flutter 3.50 es una base adecuada para la
interfaz y la capa de aplicación**, pero la decisión importante es la del motor
nativo. Hay dos caminos realistas:

1. **Flutter + Dart de punta a punta (recomendado como objetivo).** Una sola
   base de código, sin runtime Python, con `sherpa_onnx`/Piper, FFmpegKit,
   Drift y un lector EPUB propio. Es el resultado más mantenible y el de menor
   tamaño en régimen, pero exige reescribir el motor y validar tres puntos
   riesgosos: Kokoro en español, el modo EPUB Original y la mezcla de
   ambientación en vivo.
2. **Flutter + Python embebido (plan de contingencia).** Conserva el motor
   actual y sus 531 tests, y usa `serious_python` para correr Python dentro de
   la app en Android/iOS/escritorio. Reduce el tiempo y el riesgo funcional,
   pero mantiene dos lenguajes, un runtime pesado y limita Web.

La recomendación es **empezar con un spike técnico de 2–3 semanas** que valide
el camino 1 antes de comprometer la reescritura completa. Si el spike falla en
los puntos críticos, se adopta el camino 2 sin perder el trabajo de UI,
arquitectura y sistema de diseño.

## Hallazgos principales

- El APK Android 0.8.0 era un shell `reader-only` separado, con epubjs e
  IndexedDB; el sidecar Python estaba compilado fuera con `#[cfg(not(mobile))]`.
  No era una regresión de Tauri: era otra app.
- El motor Python tiene 13.860 líneas, 531 tests y una lógica valiosa de
  ingest, segmentación, TTS, timing, M4B, ambience y migración de biblioteca.
- La UI React tiene 16.235 líneas y una identidad visual sólida (Biblioteca:
  papel, tinta, oxblood, latón, pizarra) que conviene conservar, no reemplazar
  por Material 3 por defecto.
- Flutter 3.50 soporta Windows x64/ARM64, macOS x64/ARM64, Linux x64/ARM64,
  Android arm64 y web. La cobertura de plugins nativos es el límite real.
- `sherpa_onnx` 2.0.1 corre TTS local (Piper/VITS/Kokoro) en todas las
  plataformas, incluida WebAssembly, pero sus modelos Kokoro convertidos solo
  agregan inglés y chino; el Kokoro español actual requiere validación aparte.
- `ffmpeg_kit_flutter_new_audio` 2.5.8 cubre Android, iOS, macOS, Windows x64 y
  Linux x64 con FFmpeg 8.1.2. **No publica Windows/Linux ARM64**; para esas
  arquitecturas hace falta FFmpeg del sistema, un binario propio o emulación.
- `desktop_updater` 3.2.12 cubre actualizaciones firmadas en Windows/macOS y
  Linux en estado preview; Android/iOS deben usar stores o un canal manual.
- Drift 2.35 ya no necesita `sqlite3_flutter_libs`: `sqlite3` 3.x incorpora
  SQLite mediante build hooks en todas las plataformas.

## Stack recomendado (objetivo)

| Responsabilidad | Elección | Versión de referencia |
|---|---|---|
| UI | Flutter | 3.50 estable |
| Lenguaje | Dart | 3.14 |
| Estado + DI | Riverpod + riverpod_generator | 3.5 / 4.0 |
| Navegación | go_router + go_router_builder | 18.1 / 4.5 |
| Modelos | Freezed + json_serializable | 4.0 / 6.15 |
| Persistencia | Drift + SQLite 3.x | 2.35 / 3.9 |
| HTTP | Dio | 5.11 |
| Seguridad de claves | flutter_secure_storage | 11.2 |
| Audio | just_audio + audio_service + media_kit (desktop) | 0.10 / 0.18 / 1.2 |
| TTS local | sherpa_onnx (Piper/VITS; Kokoro con spike) | 2.0.1 |
| ffmpeg / M4B | ffmpeg_kit_flutter_new_audio + fallback desktop ARM64 | 2.5.8 |
| EPUB | fork interno de epub_plus + ingest propio | 5.1.0 base |
| HTML original | flutter_widget_from_html_core | 0.17.4 |
| i18n | flutter_localizations + intl + ARB | SDK / 0.20 |
| Iconos | lucide_icons_flutter | 4.0.3 |
| Testing | flutter_test + integration_test + Patrol + Alchemist + mocktail | — |
| Lints | very_good_analysis + riverpod_lint | 11.0 / 3.2 |
| Logging | talker + talker_flutter; Sentry opcional | 5.2 / 10.4 |
| Updates desktop | desktop_updater | 3.2.12 |

La justificación, alternativas descartadas y riesgos están en
[`02-stack-comparison.md`](02-stack-comparison.md).

## Mapa de documentos

1. [`01-current-state.md`](01-current-state.md): auditoría del proyecto actual.
2. [`02-stack-comparison.md`](02-stack-comparison.md): comparativa y stack.
3. [`03-architecture.md`](03-architecture.md): arquitectura propuesta.
4. [`04-design-system.md`](04-design-system.md): sistema de diseño.
5. [`05-platform-matrix.md`](05-platform-matrix.md): compatibilidad por plataforma.
6. [`06-testing.md`](06-testing.md): estrategia de pruebas.
7. [`07-performance.md`](07-performance.md): presupuestos y profiling.
8. [`08-distribution.md`](08-distribution.md): empaquetado, firma y updates.
9. [`09-plan.md`](09-plan.md): plan por fases.
10. [`10-risks-decisions.md`](10-risks-decisions.md): riesgos y decisiones pendientes.
11. [`parity-matrix.md`](parity-matrix.md): paridad funcional actual → Flutter.
12. [`benchmarks/README.md`](benchmarks/README.md): plantilla de mediciones.
13. [`sources.md`](sources.md): fuentes, método y limitaciones.

ADR específicos en [`adr/`](adr/).

## Puertas de decisión

Antes de escribir código de producto hay que aprobar:

- **G1 — Motor:** ¿Flutter + Dart puro, con spike previo, o Flutter + Python
  embebido desde el inicio?
- **G2 — Paridad:** ¿Kokoro español y el modo EPUB Original son obligatorios
  desde la primera versión Flutter?
- **G3 — Plataformas:** ¿iOS y Web son objetivos oficiales o best-effort?
- **G4 — Distribución:** ¿hay certificados de firma (Apple Developer, Windows
  Authenticode) o se distribuye sin firma como hasta ahora?
- **G5 — Datos:** ¿se conserva el formato de biblioteca actual en disco y se
  migra el índice, o se acepta una migración irreversible?

Ninguna de estas puertas se resuelve por defecto en este documento; las
recomendaciones están marcadas como tales en
[`10-risks-decisions.md`](10-risks-decisions.md).
