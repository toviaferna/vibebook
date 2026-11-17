# 09 — Plan de refactorización por fases

## 1. Reglas del plan

- **No se implementa hasta aprobar G1–G5** (`10-risks-decisions.md`).
- Cada fase termina en un **vertical slice testeable**, no en código a medias.
- Ninguna fase elimina funcionalidades sin aprobación explícita.
- La app Tauri actual sigue siendo la release estable hasta el cutover.
- No se crean tags, releases ni publicaciones sin aprobación del usuario.
- Cada fase registra baseline, resultados y decisiones en `docs/refactor/`.

## 2. Resumen de fases

| Fase | Objetivo | Duración estimada |
|---|---|---:|
| F0 | Spike técnico y decisión de motor | 2–3 semanas |
| F1 | Auditoría y baseline reproducible | 1 semana |
| F2 | Stack definitivo y ADRs | 1 semana |
| F3 | Esqueleto, tooling y CI | 1–2 semanas |
| F4 | Sistema de diseño y componentes base | 2–3 semanas |
| F5 | Infraestructura de datos y servicios | 3–4 semanas |
| F6 | Importación, biblioteca y detalle | 4–6 semanas |
| F7 | TTS, jobs y conversión | 5–8 semanas |
| F8 | Lector, audio y karaoke | 6–10 semanas |
| F9 | Ambientación y export | 3–5 semanas |
| F10 | Plataformas: Android, iOS, ARM64, Web | 4–6 semanas |
| F11 | Testing, rendimiento y accesibilidad | 3–4 semanas |
| F12 | Empaquetado, firma y updates | 2–3 semanas |
| F13 | Migración, beta y cutover | 3–4 semanas |
| F14 | Documentación y mantenimiento | continuo |

Estimación gruesa para una persona asistida por agentes: **6–9 meses**. La
paralelización de F4/F5/F6 y de tests puede reducir el calendario, pero no el
riesgo de integración. No es un compromiso contractual.

## 3. F0 — Spike técnico y decisión de motor

**Objetivo:** validar el camino Dart puro antes de comprometer la reescritura.
El plan ejecutable está en
[`docs/superpowers/plans/2026-11-17-flutter-engine-spike.md`](../superpowers/plans/2026-11-17-flutter-engine-spike.md).

**Alcance:**

- App Flutter mínima en Android arm64 y Windows.
- `sherpa_onnx` con Piper español (`es_MX-ald-medium`): 1 frase → WAV.
- Kokoro español: evaluar `flutter_onnxruntime` + G2P español o confirmar que
  no es viable sin Python.
- FFmpegKit audio: WAV → AAC/M4B con capítulos; medir en Android y Windows.
- Drift: crear DB, insertar 10k libros, medir query/scroll.
- Parser EPUB vendorizado: importar un EPUB real con acentos, TOC e imágenes.
- Lector mínimo: paginar un capítulo y resaltar una palabra por timing.
- Audio background: `just_audio` + `audio_service` con pantalla apagada.
- Ambience: dos players simultáneos y ducking; medir underruns.
- Web: `flutter build web` + lector; confirmar límites.

**Archivos/módulos:** `spike/` fuera del árbol de producción o rama
`spike/flutter-engine`; no se mezcla con `main`.

**Dependencias:** G1 aprobada para probar; hardware Android/Windows.

**Pruebas:**

- [ ] Piper genera audio inteligible en <2× tiempo real.
- [ ] Kokoro español: sí/no con evidencia y calidad aceptable.
- [ ] FFmpegKit produce M4B reproducible en Android/Windows.
- [ ] Drift 10k libros: query <50 ms, scroll 60 fps.
- [ ] EPUB real importado sin pérdida de acentos.
- [ ] Lector pagina y hace karaoke con timings.
- [ ] Audio sigue con pantalla apagada.
- [ ] Ambience no produce underruns en 10 min.
- [ ] APK/instalador dentro del presupuesto.

**Criterios de aceptación:**

- Informe de spike con métricas y capturas.
- Decisión G1: Dart puro, Python embebido o híbrido.
- Lista de features que no alcanzan paridad y su plan.

**Riesgos:** Kokoro español, FFmpeg ARM64, background Android, calidad de
Piper, tamaño.

**Resultado:** decisión fundamentada y presupuesto realista.

## 4. F1 — Auditoría y baseline reproducible

**Objetivo:** congelar el estado actual y una línea base medible.

**Tareas:**

- Inventario de features, endpoints, tablas, motores y archivos.
- Script de benchmark para biblioteca, lector y conversión.
- Capturas de referencia de la UI actual (light/dark/reader palettes).
- Documentar la biblioteca legacy y su migración.
- Lista de paridad obligatoria vs deseable.

**Entregables:** `01-current-state.md` actualizado, `benchmarks/baseline.md`,
`parity-matrix.md`.

**Aceptación:** baseline reproducible en una máquina limpia; features
inventariadas sin huecos.

## 5. F2 — Stack definitivo y ADRs

**Objetivo:** cerrar decisiones y evitar cambios de rumbo a mitad de obra.

**Tareas:**

- Aprobar G1–G5.
- ADRs: motor, estado, DB, navegación, TTS, FFmpeg, biblioteca.
- Política de dependencias: versión, licencia, mantenimiento, reemplazo.
- Definir versiones exactas y lockfiles.
- Definir estrategia de ramas/PR y releases.

**Aceptación:** ADRs firmados; `pubspec.yaml` inicial con versiones fijadas.

## 6. F3 — Esqueleto, tooling y CI

**Objetivo:** proyecto Flutter compilable en las 6 plataformas, sin features.

**Tareas:**

- `flutter create` con org `com.vibebook`.
- Estructura `lib/` y `packages/`.
- `analysis_options.yaml` (very_good_analysis + riverpod_lint).
- `build_runner`, Freezed, Drift, go_router, Riverpod.
- `main.dart`, `App`, router vacío, tema base.
- CI: analyze, test, build Linux/Windows/macOS/Android/Web (iOS cuando haya
  runner).
- Scripts: `make`/`tool/` para build, test, format, goldens, release.
- `THIRD_PARTY_NOTICES` base.

**Pruebas:** `flutter analyze`, `flutter test` (smoke), builds vacíos.

**Aceptación:** CI verde en 5 jobs; app abre en Windows/Linux/macOS/Android.

**Riesgos:** toolchain Flutter/Android/iOS en Windows; se documenta.

## 7. F4 — Sistema de diseño y componentes base

**Objetivo:** implementar tokens, tema y componentes antes de pantallas.

**Tareas:**

- `ThemeExtension` de colores/tipografía/espaciado/radios/motion.
- Fuentes bundleadas (Spectral, Literata, Public Sans, IBM Plex Mono,
  Atkinson).
- Componentes base: Button, TextField, Select, Dialog, Sheet, Toast, Progress,
  EmptyState, ErrorState, SectionHeader, AppScaffold.
- Light/dark + reader palettes.
- Responsive helpers.
- Iconos Lucide.
- Golden tests base.
- Página de “design gallery” interna (solo debug).

**Pruebas:** goldens de componentes en 2 temas/2 breakpoints/2 text scales;
contraste AA.

**Aceptación:** componentes reutilizables, sin lógica de negocio; goldens
aprobados.

## 8. F5 — Infraestructura de datos y servicios

**Objetivo:** cimientos de datos, settings, logging, archivos y seguridad.

**Tareas:**

- Drift: tablas, DAOs, migraciones, FTS5, tests de schema.
- `LibraryRepository`: scan, read manifest, atomic write, reconcile.
- `SettingsRepository`: preferences + secure storage.
- `ProviderKeyStore`: secure storage + migración.
- `PathService`, `FilePickerService`, `ShareService`.
- `Talker` logging + error mapping.
- `Result`/`Failure`.
- `AppBootstrap` y lifecycle.
- Fakes de todos los servicios.

**Pruebas:** DB en memoria, migraciones, path safety, secure storage fake,
errores.

**Aceptación:** se puede importar un manifiesto existente y listarlo desde una
pantalla mínima.

## 9. F6 — Importación, biblioteca y detalle

**Objetivo:** paridad del flujo de entrada y estante.

**Tareas:**

- Vendor `epub_plus` + ingest propio.
- Validación ZIP, encoding, estructura, TOC, imágenes, language detection.
- `ImportBook` use case + progreso.
- Biblioteca: shelf, búsqueda, orden, filtros, paginación.
- Detalle: metadata, capítulos, portada, acciones, borrar.
- Portadas: extracción, generación, búsqueda.
- Migración de biblioteca legacy (fase temprana).
- Tests unit/widget/golden/integration.

**Aceptación:** importar EPUB real → ver portada → abrir detalle → borrar;
biblioteca de 10k libros fluida; migración idempotente.

**Riesgos:** parser, encoding, portadas, rendimiento de listas.

## 10. F7 — TTS, jobs y conversión

**Objetivo:** convertir un libro con motores locales/cloud y persistir jobs.

**Tareas:**

- `EngineSpec`/`Voice`/`TtsRegistry`.
- Piper/VITS sherpa; Kokoro (según F0); Edge/Gemini/ElevenLabs/Azure; VEP.
- Claves, validación, test de proveedor.
- `JobRunner` con isolates, persistencia, cancelación, reanudación.
- Caché de segmentos/duraciones.
- Ensamblado por capítulo y M4B.
- UI Studio: engine/voz/estilo/rate, progreso, cancelar/reanudar.
- Previews de voz.
- Tests de contrato y E2E de conversión.

**Aceptación:** convertir un EPUB con Piper fake/real; audio/timings/M4B
válidos; cancelar/reanudar; job sobrevive reinicio.

**Riesgos:** Kokoro, cloud APIs, ffmpeg ARM64, concurrencia, memoria.

## 11. F8 — Lector, audio y karaoke

**Objetivo:** paridad del lector sincronizado.

**Tareas:**

- Modelo `BookDocument`, capítulos, segmentos, imágenes.
- Texto: scroll, selección, búsqueda, bookmarks.
- Libro: paginador, doble página, page-turn, 2K, album.
- Original: HTML sanitizado (o WebView según G2).
- Player: just_audio/audio_service, velocidad, timer, media session.
- Karaoke: timing exacto/estimado, segmento/palabra, fallback.
- Preferencias por libro: paleta, fuente, tamaño, modo, karaoke.
- Estado de lectura y audio; debounce.
- TOC, atajos, pantalla completa, reduced motion.
- Tests de paginación, karaoke, a11y, perf.

**Aceptación:** leer un libro con y sin audio; karaoke sincronizado; posición
persistida; 60 fps; a11y AA.

**Riesgos:** paginación, fidelidad Original, memoria, background audio.

## 12. F9 — Ambientación y export

**Objetivo:** paridad del plan, mezcla y export ambientado.

**Tareas:**

- Assets: import, licencia, checksum, aprobación.
- Camas procedurales con FFmpeg.
- Analizador heurístico.
- Plan por capítulo y editor.
- Mezcla en vivo (players/Web Audio).
- Export M4B ambientado (ffmpeg).
- UI de biblioteca/plan/atribución.
- Tests de límites, mezcla, licencias.

**Aceptación:** generar camas, analizar, activar, exportar; sin clipping;
licencias visibles; CPU razonable.

**Riesgos:** mezcla en vivo, ffmpeg, memoria, latencia.

## 13. F10 — Plataformas: Android, iOS, ARM64, Web

**Objetivo:** que “compila” se convierta en “funciona”.

**Tareas:**

- Android: SAF, permisos, foreground service, 16 KB, AAB, emulador real.
- iOS: file picker, background audio, BGTask, sandbox, TestFlight.
- Windows ARM64: Flutter + plugins + FFmpeg fallback.
- Linux ARM64: runner, FFmpeg, AppImage/DEB.
- Web: decidir alcance; lector/cloud; PWA.
- Matriz de capacidades y mensajes de limitación.
- Pruebas en hardware real.

**Aceptación:** importar → convertir → leer → background audio en Android;
build iOS instalable; builds ARM64 abren; Web lector funcional.

**Riesgos:** plugins sin arm64, App Store, background, tamaño.

## 14. F11 — Testing, rendimiento y accesibilidad

**Objetivo:** calidad medible antes de release.

**Tareas:**

- Completar unit/widget/golden/integration/E2E.
- Benchmarks y comparación con presupuestos.
- A11y: contraste, foco, teclado, lectores de pantalla, text scale.
- Seguridad: paths, ZIP, claves, updates.
- Caos: cancelar jobs, cerrar app, disco lleno, red lenta, EPUB corrupto.
- Corregir deuda y flaky tests.

**Aceptación:** presupuestos dentro de rango; a11y AA; sin P0/P1 abiertos;
cobertura objetivo.

## 15. F12 — Empaquetado, firma y updates

**Objetivo:** artefactos instalables y verificables.

**Tareas:**

- Inno Setup x64/ARM64 + ZIP; MSIX opcional.
- DMG + firma/notarización.
- AppImage/DEB/Flatpak.
- AAB/APK firmado; IPA.
- Web deploy.
- `desktop_updater` con claves y feed.
- Checksums, notices, SBOM.
- Instalación limpia y upgrade desde versión anterior.

**Aceptación:** cada artefacto se instala, abre, importa, convierte, lee y
exporta; checksums verificados; update funciona.

## 16. F13 — Migración, beta y cutover

**Objetivo:** pasar usuarios de Tauri a Flutter sin perder datos.

**Tareas:**

- Migración de `library.db`, estados, bookmarks, settings, keys.
- Backup y rollback.
- Beta cerrada con usuarios reales.
- Comparar paridad y corregir.
- Congelar features de Tauri; solo fixes críticos.
- Documentar diferencias y limitaciones.
- Plan de rollback a Tauri durante la beta.

**Aceptación:** biblioteca legacy idéntica; lectura/posición/bookmarks
preservados; beta sin P0; aprobación del usuario para cutover.

## 17. F14 — Documentación y mantenimiento

**Objetivo:** que el proyecto siga siendo mantenible.

**Tareas:**

- Actualizar `docs/` (arquitectura, plataformas, providers, engines, release).
- ADRs y decisiones.
- Guía de contribución y setup.
- Runbooks: release, rollback, incidentes, migración.
- Dependencias: política de upgrades y auditoría.
- Postmortem de la migración.

**Aceptación:** un builder nuevo puede clonar, correr tests y build sin ayuda;
docs coinciden con el código.

## 18. Paralelización y dependencias

```text
F0 → G1
F1 → F2 → F3
F3 → F4 ─┬→ F6 ─┬→ F7 ─→ F9
         ├→ F5 ─┘   └→ F8
         └→ tests/CI
F6/F7/F8 → F10 → F11 → F12 → F13 → F14
```

- F4 y F5 pueden ir en paralelo tras F3.
- F6 depende de F5; F7 de F5/F6; F8 de F6; F9 de F7/F8.
- F10 no debe esperar a que todo esté “perfecto”, pero sí a que el flujo
  importar→leer funcione.
- F11 es continuo, no solo al final.

## 19. Puertas de calidad por fase

Cada fase debe cumplir:

- [ ] `flutter analyze` + `custom_lint` sin errores.
- [ ] Tests nuevos y existentes verdes.
- [ ] Goldens revisados.
- [ ] Sin regresiones de rendimiento >10%.
- [ ] A11y del slice (semántica/foco/contraste).
- [ ] Documentación del slice.
- [ ] Demo grabada o instalable de prueba.
- [ ] Aprobación del usuario para avanzar si cambia alcance.

## 20. Qué no se hace en este plan

- No se migra a Flutter por moda: se hace porque resuelve Android/iOS y unifica
  la UI, con evidencia de F0.
- No se reescribe el motor sin spike.
- No se eliminan Kokoro, EPUB Original ni ambience sin aprobación.
- No se promete Web con paridad total.
- No se publica nada sin aprobación.
- No se cambia el formato de biblioteca sin migración reversible.
