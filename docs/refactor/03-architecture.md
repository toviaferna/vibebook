# 03 — Arquitectura propuesta

## 1. Principios

1. **Feature-first, no capas infinitas.** La app se organiza por funcionalidad
   y cada feature contiene su UI, ViewModel y repositorios cuando corresponde.
2. **Separación UI / dominio / datos.** La UI no conoce HTTP, SQLite ni ffmpeg.
   Los repositorios son la fuente de verdad; los servicios envuelven sistemas
   externos.
3. **Unidirectional data flow.** Eventos de UI → ViewModel → repositorio →
   estado inmutable → UI.
4. **Puertos y adaptadores para lo nativo.** TTS, audio, ffmpeg, archivos,
   keychain y updates se exponen como interfaces; las implementaciones varían
   por plataforma.
5. **Persistencia explícita.** Nada crítico vive solo en memoria. Jobs,
   posiciones, bookmarks y ajustes se persisten.
6. **La biblioteca en disco sigue siendo portable.** Drift indexa; el
   manifiesto y los archivos siguen siendo la fuente de verdad.
7. **Sin dependencias circulares.** `features` puede depender de `core` y
   `domain`; `domain` no depende de Flutter; `data` implementa `domain`.
8. **Tests en los bordes.** Cada repositorio, servicio y ViewModel tiene tests;
   los widgets se prueban con fakes.

## 2. Estructura del repositorio

```text
lib/
  main.dart
  app/
    app.dart                 # MaterialApp.router, tema, localization
    router.dart              # go_router + typed routes
    bootstrap.dart           # composición de dependencias
    lifecycle.dart           # arranque/cierre, jobs, updates
  core/
    design/                  # tokens, tema, tipografía, componentes base
    errors/                  # Failure, Result, mapeo de excepciones
    logging/                 # talker, timeline, crash reporting
    platform/                # file picker, paths, share, notifications
    utils/                   # fechas, slugs, validación, hash
    accessibility/           # helpers de semántica/foco
  domain/
    books/                   # Book, Chapter, Segment, Toc, BookImage
    library/                 # BookRecord, LibraryQuery, import policy
    tts/                     # EngineSpec, Voice, TtsRequest, TtsResult
    jobs/                    # Job, JobState, JobEvent
    reader/                  # ReadingState, Bookmark, ReaderPreferences
    ambience/                # SoundAsset, AmbiencePlan, Bed, Effect
    providers/               # ProviderConfig, ProviderStatus
    settings/                # AppSettings
  data/
    db/                      # Drift database, tables, DAOs, migrations
    library/                 # filesystem manifest repository
    ingest/                  # EPUB parser + normalizer
    tts/                     # engine registry + implementations
    audio/                   # playback, assembly, ffmpeg adapter
    ambience/                # assets, procedural, analyzer, mix
    providers/               # HTTP/WebSocket clients
    covers/                  # Open Library/Google Books + generated covers
    settings/                # secure storage + preferences
    jobs/                    # job runner, isolate workers, persistence
  features/
    library/                 # shelf, search, sort, filters
    import/                  # file picker, validation, progress
    book_detail/             # metadata, chapters, actions, cover
    studio/                  # voice/engine/style/rate, conversion progress
    reader/                  # text/book/original, karaoke, player, TOC
    ambience/                # asset library, plan editor, mix
    settings/                # appearance, playback, providers, engines
    onboarding/              # first run, permissions, folder choice
  l10n/
    app_es.arb
    app_en.arb
test/
  unit/
  widget/
  golden/
  integration/
  fixtures/
```

Reglas de dependencia:

- `features/*` → `domain/*`, `core/*`, `data/*` (solo a través de providers).
- `data/*` → `domain/*`, `core/*`.
- `domain/*` → nada de Flutter, Dio, Drift ni paquetes de UI.
- `core/*` no importa `features/*`.
- Los paquetes internos (`packages/epub_plus_vibebook`) no dependen de la app.

## 3. Capas y responsabilidades

### UI (features)

- **View**: widgets puros; recibe estado y callbacks.
- **ViewModel**: `Notifier`/`AsyncNotifier`; transforma estado de repositorios a
  UI state; comandos.
- **Widgets compartidos**: `core/design/components`.

### Dominio

- Entidades inmutables (Freezed) y value objects.
- Casos de uso solo cuando hay lógica compleja o reutilizada:
  `ImportBook`, `StartConversion`, `BuildReaderPages`, `RenderAmbience`.
- Interfaces de repositorios y servicios.

### Datos

- **Repositorios**: fuente de verdad; cache, reintentos, mapeo, transacciones.
- **Servicios**: HTTP, WebSocket, filesystem, ffmpeg, keychain, audio.
- **DB**: Drift DAOs; migraciones; FTS5.
- **Workers**: isolates para ingest, parseo, hash, generación de páginas y
  trabajos de audio; comunicación por mensajes serializables.

## 4. Estado y DI

- `ProviderScope` en `main.dart`.
- Providers:
  - `appDatabaseProvider`, `libraryRepositoryProvider`,
    `settingsRepositoryProvider`, `ttsRegistryProvider`, `jobRunnerProvider`,
    `playbackServiceProvider`, `ffmpegServiceProvider`.
- Cada feature expone sus providers en `features/<name>/providers.dart`.
- `AsyncNotifier` para listas/consultas; `Notifier` para estado de UI.
- `ref.listen` para efectos (navegación, snackbars, diálogos).
- `ProviderScope(overrides: ...)` en tests; nunca singletons globales.
- `riverpod_lint` y `custom_lint` en CI.

## 5. Navegación

Rutas tipadas con `go_router_builder`:

```text
/                         Library
/import                   Import
/books/:id                BookDetail
/books/:id/studio         Studio
/books/:id/read           Reader
/books/:id/ambience       Ambience
/settings                 Settings
/settings/providers       Providers
/settings/engines         Engines
/settings/about           About
```

Shells:

- Desktop: `NavigationRail`/sidebar de 264 px + topbar.
- Mobile: `NavigationBar` + app bar contextual.
- Reader: shell inmersivo sin sidebar; topbar mínima.
- Deep links: `vibebook://books/<id>/read`; Web URLs con hash o path según
  hosting.

Guards:

- `redirect` a onboarding si no hay biblioteca elegida.
- `redirect` a detalle si el libro no existe.
- Confirmación de salida durante conversión activa.

## 6. Persistencia

### Drift / SQLite

Tablas nuevas (nombres estables, migraciones versionadas):

```text
books(id, title, author, language, language_declared, path, cover_path,
      status, voice, engine, style, rate, duration_ms, chapter_count,
      created_at, updated_at)
jobs(id, book_id, status, stage, completed_segments, total_segments,
     chapter_index, chapter_title, current_text, message, error,
     options_json, created_at, updated_at, started_at, finished_at)
job_events(id, job_id, sequence, type, payload_json, created_at)
book_state(book_id, position_ms, chapter_index, playback_rate, updated_at,
           sequence)
bookmarks(id, book_id, chapter_index, position_ms, note, created_at)
reading_state(book_id, chapter_index, char_offset, page_index, page_count,
              percent, cfi, updated_at, sequence)
reading_bookmarks(id, book_id, chapter_index, char_offset, page_index, note,
                  created_at)
book_preferences(book_id, reader_mode, reader_palette, reader_font, reader_size,
                 page_turn, ambience_enabled, book_karaoke, updated_at)
settings(key, value_json, updated_at)
sound_assets(id, kind, prompt, tags_json, provider, model, seed, duration_ms,
             loopable, sample_rate, channels, loudness_lufs, license,
             attribution, source_url, checksum, approved, created_at,
             last_used_at, usage_count)
providers(id, key_ref, region, status, last_tested_at)
```

Índices: estado/fecha/título/duración en `books`; `jobs(book_id, created_at)`;
`jobs(status)`; bookmarks por libro/posición; FTS5 `book_search` con
título/autor/texto si se necesita búsqueda global.

### Biblioteca en disco

Se conserva el layout actual:

```text
<library>/<slug>-<sha8>/
  manifest.json
  book.md
  source.epub
  cover.jpg
  images/
  audio/segments/
  audio/chapters/
  timings/
  ambience/plan.json
  <titulo>.m4b
```

El repositorio de biblioteca:
- escanea directorios y lee manifiestos;
- reconcilia con Drift (upsert/mark missing);
- escribe manifiestos de forma atómica (tmp + rename);
- nunca borra archivos fuera de un libro;
- valida paths con `safeBookPath` (equivalente a `paths.py`).

### Migración desde la app actual

1. Detectar `library.db` y `provider-keys.json` en el directorio de datos.
2. Importar `books`, `book_state`, `bookmarks`, `reading_state`,
   `reading_bookmarks`, `book_preferences`, `settings` y `sound_assets`.
3. Reconciliar con manifiestos; si hay conflicto, gana el manifiesto y se
   registra el diff.
4. Copiar claves de proveedores a `flutter_secure_storage` y borrar el archivo
   solo si el usuario acepta.
5. No mover ni renombrar libros; no borrar `.books/`.
6. Backup automático `library.db.pre-flutter` y un log de migración.

## 7. Pipeline de importación

```text
file picker / drag&drop
  → validación de extensión y tamaño
  → lectura de bytes
  → validación ZIP (entradas, cifrado, symlinks, ratio, tamaño real)
  → parseo OPF/NCX/nav
  → decodificación determinista de XHTML
  → normalización de bloques (títulos, párrafos, imágenes)
  → detección de idioma
  → segmentación/chunking (max_chars)
  → manifiesto + book.md + portada + imágenes
  → commit atómico al library
  → upsert en Drift
```

El parser se ejecuta en un isolate; la UI recibe progreso (`reading`,
`parsing`, `normalizing`, `writing`). Los errores se mapean a `ImportFailure`
con código y mensaje accionable.

## 8. Pipeline de conversión

```text
StartConversion(bookId, options)
  → valida motor/voz/estilo/rate
  → crea job en Drift (queued)
  → JobRunner toma el job
  → prepara capítulos/segmentos
  → por capítulo:
       sintetiza segmentos con concurrencia del motor
       cachea audio + timings por segmento
       ensambla capítulo (PCM → MP3)
       escribe timing
  → ensambla M4B (ffmpeg)
  → commit atómico del manifiesto/audio
  → job completed
```

- Cancelación: flag persistido + `CancellationToken` por segmento.
- Reanudación: cache key por texto/voz/motor/estilo/rate/fingerprint; los
  segmentos ya sintetizados se reutilizan.
- Progreso: `JobEvent` persistido y stream a la UI; SSE ya no es necesario
  porque no hay HTTP interno, pero se puede modelar como `Stream<JobEvent>`.
- Concurrencia: por motor (Piper 2, eSpeak 1, Edge 2, Azure 4, Gemini/
  ElevenLabs según límites). Configurable solo a la baja.
- Aislamiento: la síntesis y el ensamblado corren fuera del isolate de UI.
- Errores: reintentos con backoff; error persistido con stage y mensaje.

## 9. Abstracción TTS

```text
EngineSpec(
  id, label, kind, transport, requiresNetwork, requiresKey,
  supportsStyles, timingQuality, audioSuffix, maxChars,
  concurrency, license, sourceUrl, implemented
)

TtsEngine:
  Future<List<Voice>> voices()
  Future<AudioResult> synthesize(TtsRequest)
  Future<void> validateConfig()
```

Implementaciones:

- `PiperTtsEngine` / `VitsTtsEngine` sobre sherpa-onnx.
- `KokoroTtsEngine` sobre flutter_onnxruntime + G2P español (spike) o
  adaptador Python si se elige el fallback.
- `EdgeTtsEngine` (WebSocket, vendor de `edge_tts` MIT).
- `GeminiTtsEngine`, `ElevenLabsTtsEngine`, `AzureTtsEngine` (Dio/WebSocket).
- `SystemTtsEngine` (flutter_tts) como fallback de eSpeak/sistema.
- `VepPluginEngine` (HTTP/JSON, manifiesto y token).
- `FakeTtsEngine` solo en tests/dev.

`TtsRegistry` resuelve disponibilidad, defaults, voces y concurrencia. La UI
solo ve `EngineSpec`/`Voice`; nunca conoce detalles de proveedor.

## 10. EPUB y lector

### Parser

- Vendor `epub_plus` (MIT) en `packages/epub_plus_vibebook`.
- Correcciones propias: encoding determinista, TOC/nav, títulos generados,
  imágenes con alt/caption, `source_href`/`fragment`.
- Modelo normalizado `BookDocument` con `Chapter`, `Paragraph`, `Segment`,
  `ImageRef`, `TocNode`.
- El parser no renderiza; produce texto y metadata.

### Render

- **Texto**: `CustomScrollView` + `SelectableText.rich`; segmentos como spans;
  karaoke por palabra; auto-scroll con pausa.
- **Libro**: paginador propio con `TextPainter` y `RichText`; mide ancho/alto,
  divide párrafos, cachea páginas por libro/contenido/viewport/fuente/tamaño;
  `PageView` horizontal con giro 3D; doble página en pantallas anchas.
- **Original**: `flutter_widget_from_html_core` con CSS permitido; si se
  requiere fidelidad total, WebView por plataforma (decisión G2). Sin scripts.
- Imágenes: extraídas a `images/`, servidas desde archivo local; `Image.file`
  con cache y tamaños.
- Búsqueda: FTS5 sobre texto normalizado; resaltado y salto a página/segmento.
- Bookmarks: por capítulo + offset/página; persistentes.
- Accesibilidad: semántica por párrafo, foco, tamaños, contraste, reduced
  motion, navegación por teclado.

## 11. Ambientación

- `AmbienceRepository`: assets, plan, aprobación, licencias, checksums.
- `ProceduralBedGenerator`: ffmpeg para las seis camas.
- `AmbienceAnalyzer`: heurístico español offline (port del actual).
- `AmbiencePlayer`: mezcla en vivo.
  - Móvil/desktop: múltiples `AudioPlayer` de just_audio (cama loop + efectos)
    con volúmenes/ducking; si no alcanza, motor nativo (miniaudio vía FFI).
  - Web: Web Audio API mediante `package:web`/JS interop; limitado.
- `AmbienceExporter`: ffmpeg `amix`/`sidechaincompress` para M4B ambientado.
- Límites: 1 cama + 3 efectos, 8 s de separación, 2 s de guardas, confianza
  ≥0.5; validados en dominio y DB.

## 12. Seguridad

- Sin servidor HTTP local: la app no expone puertos ni tokens.
- Claves en `flutter_secure_storage`:
  - Android Keystore, iOS Keychain, macOS Keychain, Windows DPAPI,
    Linux libsecret, Web WebCrypto.
  - Si Linux no tiene keyring, se informa y se ofrece archivo 0600 como
    fallback explícito, no silencioso.
- EPUB/HTML no confiable: sanitización, sin scripts, límites de tamaño/ratio,
  paths seguros.
- Red: TLS, timeouts, límites de respuesta, validación de URLs de plugins,
  sin redirects a hosts no permitidos.
- Logs: nunca claves, tokens, contenido completo de libros ni datos personales.
- Updates: metadata firmada Ed25519; verificación de hash/length antes de
  instalar; no se ejecuta un instalador sin firma.
- Privacidad: sin telemetría por defecto; Sentry opt-in; no se suben libros.

## 13. Errores y observabilidad

- `Result<T, Failure>` o sealed classes para bordes; excepciones solo dentro de
  servicios.
- `Failure` con `code`, `message`, `cause`, `recoverable`, `action`.
- `FlutterError.onError` + `PlatformDispatcher.instance.onError` +
  `runZonedGuarded`.
- `ErrorWidget.builder` con UI accionable; logs a Talker.
- Timeline events en `dart:developer` para import, TTS, ffmpeg, reader page
  build.
- Sentry opcional con scrubbing; no se activa sin consentimiento.

## 14. i18n y accesibilidad

- ARB + `gen_l10n`; español por defecto, inglés como segunda lengua.
- Formatos con `intl`; RTL preparado (aunque no haya idioma RTL inicial).
- Todas las cadenas visibles en ARB; no strings hardcodeados.
- Semántica, labels, hints y announcements; foco visible; orden de tabulación.
- Contraste WCAG AA; tamaños escalables; `MediaQuery.textScalerOf`.
- `prefers-reduced-motion` → `MediaQuery.disableAnimationsOf` y duración 0.

## 15. Plataforma y servicios

Interfaces en `core/platform`:

- `FilePickerService` (file_selector/desktop_drop).
- `PathService` (path_provider; biblioteca portable).
- `KeyValueStore` (shared_preferences para preferencias no sensibles).
- `SecureKeyStore` (flutter_secure_storage).
- `NotificationService` (local notifications; opcional).
- `ShareService` (share_plus).
- `WindowService` (window_manager/tray_manager en desktop).
- `UpdateService` (desktop_updater; no-op en mobile).
- `BackgroundTaskService` (flutter_foreground_task/WorkManager; mobile).
- `PlaybackService` (just_audio/audio_service/media_kit).
- `FfmpegService` (FFmpegKit/binario).
- `TtsRuntime` (sherpa_onnx/flutter_onnxruntime).

Cada interfaz tiene una implementación real y una fake para tests.

## 16. Dependencias entre features

```text
library ──► import? (no; import escribe library)
library ──► book_detail
book_detail ──► studio
book_detail ──► reader
book_detail ──► ambience
studio ──► jobs
reader ──► playback + ambience
settings ──► providers/engines
```

No hay dependencia circular: `jobs` no conoce UI; `reader` no conoce `studio`
salvo un comando “convertir” que navega por ruta.

## 17. Decisiones arquitectónicas registradas

- ADR-0001: Flutter + Dart puro como objetivo, Python embebido como fallback.
- ADR-0002: Riverpod para estado/DI.
- ADR-0003: Drift para persistencia.
- ADR-0004: go_router para navegación.
- ADR-0005: sherpa_onnx/Piper para TTS local; Kokoro con spike.
- ADR-0006: FFmpegKit audio + fallback ARM64.
- ADR-0007: biblioteca en disco como fuente de verdad; Drift como índice.

Ver [`adr/`](adr/).
