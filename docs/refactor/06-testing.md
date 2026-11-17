# 06 — Estrategia de pruebas

## 1. Principios

1. **Probar comportamiento, no implementación.** Los tests hablan de contratos
   y resultados, no de widgets internos.
2. **Fakes en los bordes, mocks solo cuando hace falta.** Servicios nativos,
   HTTP y filesystem se reemplazan por fakes deterministas.
3. **Pirámide con base fuerte.** Muchos unit tests de dominio/datos, widget
   tests por ViewModel, pocos E2E pero críticos.
4. **Los tests son documentación ejecutable.** Nombres en español/inglés
   consistente; un test = una intención.
5. **Determinismo.** Reloj, UUID, azar y red se inyectan; no `DateTime.now()`
   ni `Random()` sin control.
6. **Cada bug se reproduce con un test antes de arreglarlo.**
7. **Los presupuestos de rendimiento y a11y son tests, no opiniones.**

## 2. Pirámide objetivo

| Nivel | Proporción | Qué cubre |
|---|---:|---|
| Unit (dominio/datos) | 55–65% | Entidades, casos de uso, parsers, repositorios, TTS, DB |
| Widget | 20–25% | Pantallas/componentes con ViewModels y fakes |
| Golden | 5–10% | Sistema de diseño, estados, responsive, temas |
| Integration | 5–10% | Flujos con DB/filesystem reales en desktop |
| E2E (Patrol) | 2–5% | Importar → convertir → leer → exportar en Android/iOS |
| Manual/exploratorio | — | Audio real, dispositivos, accesibilidad con lectores |

Cobertura no es objetivo único. Se apunta a **≥85% en `domain/` y `data/`** y
**≥65% global**, con revisión de casos críticos sin cobertura.

## 3. Herramientas

| Herramienta | Uso |
|---|---|
| `flutter_test` | Unit y widget tests |
| `integration_test` | Flujos en dispositivo/desktop |
| `patrol` 4.11 | Interacciones nativas: file picker, permisos, notificaciones |
| `alchemist` 0.14 | Golden tests multi-tema/tamaño/text scale |
| `mocktail` 1.0.5 | Mocks sin codegen |
| `coverage` | `flutter test --coverage` + lcov |
| `flutter analyze` | Analyzer + lints |
| `very_good_analysis` 11 | Reglas estrictas |
| `riverpod_lint` 3.2 + `custom_lint` | Anti-patrones de Riverpod |
| `dart format` | Formato |
| `talker` | Logs en tests de integración (opcional) |
| `ffprobe`/`mutagen` (fixtures) | Validar audio/M4B |
| `axe` no aplica | Flutter usa Semantics; ver sección a11y |

## 4. Unit tests

### Dominio

- `BookDocument`, `Chapter`, `Segment`, `TocNode`, `BookImage`.
- Segmentación/chunking: límites, párrafos, diálogos, abreviaturas, comillas.
- Language detection: es/en/ambiguo, textos cortos, EPUB mal etiquetado.
- `EngineSpec`/`Voice`/`TtsRequest` validaciones.
- `JobState` transiciones y cancelación.
- `AmbiencePlan` límites (1 cama + 3 efectos, 8 s, 2 s, confianza).
- `ReadingState`/bookmarks.
- `Result<T, Failure>` y mapeo de errores.

### Datos

- Repositorios con fakes de DB/servicios.
- Drift DAOs con base en memoria (`NativeDatabase.memory()`).
- Migraciones: schema v1→vN con datos reales; export de schemas.
- Parser EPUB: fixtures con UTF-8, CP1252, BOM, EPUB2/3, TOC anidado,
  imágenes, capítulos sin título, EPUB corrupto, zip bomb, symlink.
- TTS providers: requests/responses grabadas; Edge WebSocket; Azure
  word boundaries; ElevenLabs timings; Gemini WAV; errores 401/402/429/500.
- Ffmpeg adapter: argumentos generados, errores, cancelación, timeout.
- Biblioteca: import atómico, colisión por hash, libro existente, path traversal,
  cover, manifest inválido.
- Migración: library.db actual + manifiestos; idempotencia; backup.

### Reglas

- No llamadas reales a red en unit tests.
- No `sleep`; usar reloj/futures controlados.
- Fixtures pequeños (<1 MB) salvo un caso de rendimiento marcado.
- Cada provider tiene un test de contrato común.

## 5. Widget tests

- Cada pantalla con su ViewModel y providers overrideados.
- Estados: loading, empty, error, success, disabled, offline.
- Interacciones: tap, teclado, foco, scroll, búsqueda, selección.
- Responsive: compact/medium/expanded.
- Temas: light/dark; lector paper/sepia/night.
- Text scale: 1.0, 1.5, 2.0.
- Semantics: labels, roles, focus order; `SemanticsTester`.
- No se testea pixel-perfect aquí; eso es golden.

## 6. Golden tests

Con Alchemist:

- Componentes base: Button, TextField, Select, Dialog, Toast, Progress.
- Biblioteca: shelf vacío, 1 libro, 100 libros (solo viewport), error.
- Detalle: con/sin portada, con/sin audio, con ambience.
- Estudio: engines, voices, progreso, error.
- Lector: texto, libro doble página, karaoke activo, TOC, player, ajustes.
- Ajustes: providers, engine cards, tema.
- Light/dark + reader palettes + compact/expanded + text scale 1.0/2.0.
- Goldens en un solo runner (Linux CI) para evitar diferencias de plataforma.
- Revisión humana de cada golden actualizado; no `--update-goldens` ciego en CI.

## 7. Integration tests

Desktop (Windows/Linux/macOS):

- Importar un EPUB fixture → se crea biblioteca → se lista.
- Convertir con un motor fake local → audio/timings/M4B.
- Leer → cambiar página → guardar posición → reabrir.
- Exportar M4B ambientado con fixtures de audio.
- Migrar una biblioteca legacy.

Android/iOS (Patrol):

- File picker nativo para importar.
- Permiso de notificaciones/foreground service.
- Reproducir audio con pantalla apagada.
- Pausar/reanudar conversión al background.
- Compartir/exportar archivo.
- Deep link a lector.

Los tests de plataforma se ejecutan en CI cuando el runner está disponible; si
no, se marcan como manuales y no se declara “soportado” sin evidencia.

## 8. E2E críticos

1. Primer arranque → elegir biblioteca → importar EPUB → ver portada.
2. Importar → convertir con Piper fake → progreso → abrir lector → karaoke.
3. Leer sin audio → convertir → el player aparece sin reimportar.
4. Cambiar tema/paleta/tipografía → persistir → reabrir.
5. Buscar → bookmark → reabrir → restaurar.
6. Generar camas → analizar → activar ambience → exportar.
7. Configurar proveedor cloud (fake HTTP) → test → voz → convertir.
8. Borrar libro → confirmar → desaparece de biblioteca y disco.
9. Migrar biblioteca legacy → mismo id/título/estado.
10. Error de red/429 → mensaje accionable → reintentar.

## 9. Contratos de TTS

Cada motor implementa el mismo contrato:

```text
- voices() devuelve voces válidas para el locale.
- synthesize(texto vacío) falla con ValidationFailure.
- synthesize(texto > maxChars) se chunkéa o falla explícitamente.
- rate fuera de rango falla.
- style no soportado se rechaza o degrada con warning.
- audio result tiene path, duración y timings (o vacío).
- errores 401/402/429/500 se mapean a Failure con code.
- cancelación aborta y limpia archivos parciales.
```

Fixtures por proveedor:

- Edge: WebSocket frames de audio + word boundaries.
- Azure: SSML + word boundary events / REST fallback.
- ElevenLabs: JSON con character timings + MP3.
- Gemini: WAV 24 kHz + metadata.
- Piper/VITS: WAV + duración.
- Kokoro: WAV + idioma/voz.
- VEP: JSON de voces + audio.

## 10. Audio y M4B

- Validar con `ffprobe`: codec AAC, sample rate, canales, duración.
- Capítulos: count, títulos, timestamps.
- Timing: offsets/durations monotónicos; cobertura de palabras ≥80% para
  karaoke; fallback a segmento.
- M4B: metadata, cover, chapters, tamaño razonable.
- Ambience: mezcla no clipping, ducking, cues en rango, licencias.
- Fixtures de audio pequeños generados por ffmpeg (tonos/silencio), no binarios
  grandes en git.

## 11. Base de datos y migraciones

- Exportar schemas con `drift_dev schema dump`.
- Tests de migración desde cada versión a la actual con datos representativos.
- Migración desde SQLite legacy (`library.db`) con libros, jobs, estados,
  bookmarks, settings y sound_assets.
- Idempotencia: ejecutar dos veces no duplica.
- Rollback/backup: si falla, no se pierde la DB anterior.
- Tests de concurrencia: jobs y UI escribiendo estado.

## 12. Accesibilidad

- `SemanticsTester` en pantallas críticas.
- Contraste: validar tokens con un script (WCAG AA).
- Foco: recorrido de tab, orden, escape, retorno.
- Teclado: atajos del lector y biblioteca.
- Text scale 2.0 sin overflow (`FlutterError` falla el test).
- Reduced motion: duración 0, sin transform 3D.
- Pruebas manuales con TalkBack (Android), VoiceOver (iOS/macOS), NVDA
  (Windows) y Orca (Linux) antes de release.
- No usar `excludeSemantics` sin alternativa.

## 13. Performance tests

- `flutter test integration_test/perf` con `watchPerformance`.
- Presupuestos:
  - primer frame <2.5 s desktop, <3 s mobile;
  - biblioteca 10k libros: scroll 60 fps, query <50 ms;
  - abrir lector <1.5 s; page-turn 60 fps;
  - importar EPUB 10 MB <2 s; 100 MB <10 s;
  - TTS local RTF <2× tiempo real (Piper);
  - memoria lector <300 MB; app idle <250 MB.
- Medir en profile, no debug.
- Guardar resultados por commit en `docs/refactor/benchmarks/`.
- Un PR que empeora >10% un presupuesto debe justificarlo.

## 14. Seguridad

- Path traversal: `../`, absolutos, symlinks, NUL.
- ZIP bomb: ratio, entradas, tamaño real.
- HTML/EPUB: scripts, handlers, URLs externas, iframes.
- Claves: no aparecen en logs, DB, crash reports ni UI completa.
- Updates: metadata sin firma/hash incorrecto se rechaza.
- Plugins: HTTPS, IP pública, redirects, SSRF.
- Dependencias: `dart pub outdated`, `osv-scanner`/`dependabot`, revisión de
  licencias.

## 15. CI

```text
analyze:
  dart format --set-exit-if-changed .
  flutter analyze
  dart run custom_lint

test:
  flutter test --coverage
  genhtml coverage/lcov.info

golden:
  flutter test test/golden

integration:
  flutter test integration_test -d windows|linux|macos

android:
  patrol test -d emulator

build:
  flutter build windows|macos|linux|appbundle|ipa|web --release
```

- Matriz de SO; cache de pub/Flutter; artefactos por job.
- Los tests de red usan fixtures; no requieren claves reales.
- Un job de “provider smoke” opcional corre con claves de CI y se marca
  `continue-on-error` hasta estabilizarlo.
- No se publica un release si falla un test crítico o un golden sin revisar.

## 16. Criterios de aceptación de testing

- [ ] `flutter analyze` y `custom_lint` sin errores.
- [ ] Unit tests de dominio/datos ≥85% de cobertura.
- [ ] Widget tests de todas las pantallas y estados.
- [ ] Goldens revisados en light/dark/paletas/breakpoints/text scale.
- [ ] E2E de importar → convertir → leer → exportar en al menos un desktop.
- [ ] E2E Android de importar → leer → background audio.
- [ ] Migración legacy probada con una biblioteca real anonimizada.
- [ ] Tests de accesibilidad y contraste.
- [ ] Tests de seguridad de paths/ZIP/claves.
- [ ] Benchmarks registrados contra los presupuestos.
