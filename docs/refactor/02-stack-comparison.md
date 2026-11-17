# 02 — Comparativa tecnológica y stack recomendado

## 1. Método

Criterios, en orden de peso:

1. **Compatibilidad real** con Windows x64/ARM64, macOS x64/ARM64, Linux
   x64/ARM64, Android arm64, iOS y Web (cuando aplique).
2. **Rendimiento y consumo** en arranque, listas grandes, lectura, audio y
   conversión.
3. **Estabilidad y mantenimiento** de cada dependencia (fecha de última
   release, puntos de pub.dev, issues, licencia, bus factor).
4. **Encaje con el dominio**: EPUB, TTS local/cloud, ffmpeg, M4B, audio en
   segundo plano, SQLite, archivos grandes.
5. **Facilidad de desarrollo y testing** para un equipo pequeño asistido por
   agentes.
6. **Calidad visual y accesibilidad** sin sacrificar rendimiento.
7. **Costo de migración** y posibilidad de conservar la biblioteca existente.

Se consultaron docs oficiales de Flutter 3.50, pub.dev (versiones y métricas a
2026-11-17), los repositorios de los paquetes y el código actual del repo. Las
métricas de descargas/likes son señales de adopción, no benchmarks.

## 2. Framework de interfaz

| Opción | Plataformas | Ventajas | Límites | Veredicto |
|---|---|---|---|---|
| **Flutter 3.50** | Win x64/ARM64, macOS x64/ARM64, Linux x64/ARM64, Android, iOS, Web | Un solo UI codebase; Impeller; tooling maduro; desktop estable; plugins nativos; buen testing | Web limitado para FFI/SQLite/FFmpeg; algunos plugins no cubren todas las arquitecturas; app más pesada que Tauri | **Elegido** |
| Tauri 2 | Desktop + Android/iOS | Binarios pequeños; WebView nativo; Rust seguro | El sidecar Python no existe en Android; WebView difiere por plataforma; se mantiene el problema de origen | Descartado como target; se conserva la app actual durante la transición |
| React Native | Android/iOS; desktop vía Windows/macOS comunidad | Reutiliza React; ecosistema móvil | Desktop Linux débil; puentes nativos; no es un UI codebase único real | Descartado |
| KMP + Compose Multiplatform | Android/iOS/desktop estable; Web beta | UI y lógica Kotlin compartidas; rendimiento nativo; buen encaje Android | Reescribir todo el motor en Kotlin; ecosistema de TTS/FFmpeg/EPUB menor; Web beta | Alternativa si se decide reescritura nativa total |
| .NET MAUI | Android/iOS/Windows/macOS; **sin Linux** | Integración Microsoft; C# | No cumple “cualquier sistema”; ecosistema Flutter/Android menor | Descartado |
| Electron | Desktop | Ecosistema web; consistente | No mobile; binarios grandes; no resuelve Python en Android | Descartado |
| Capacitor/Ionic | Android/iOS/Web; desktop vía Electron | Reutiliza React; plugins móviles | Desktop no nativo; Python en Android sigue siendo un problema | Descartado como stack único |
| Flet 1.0 | 6 plataformas | Python + Flutter; wheels Android/iOS de onnxruntime/av/ffmpeg | UI propia (no Flutter nativo); audio en background limitado; menos control de media | Descartado para este brief, aunque validó que Python móvil es posible |
| pywebview | Desktop + Android | Conserva React + Python | Android vía Buildozer/Kivy; sin iOS; recetas nativas | Descartado |

**Por qué Flutter:** es el único framework que cubre las seis familias con una
UI propia, tooling de testing/profiling y un ecosistema de plugins suficientes
para el dominio. Tauri no resuelve el problema de Android; KMP sería una
reescritura nativa aún mayor; Flet/pywebview conservan Python pero no dan el
nivel de control visual y de media que pide el brief.

## 3. Estrategia del motor: la decisión más importante

| Estrategia | Reutiliza Python | Costo | Rendimiento | Android/iOS | Web | Riesgo |
|---|---:|---|---|---|---|---|
| **Dart puro** | No | Muy alto (reescribir 13,8k líneas) | Alto; un runtime | Sí, nativo | Parcial (FFmpeg/FFI limitados) | Alto por paridad funcional |
| **Python embebido** (`serious_python`) | Sí | Medio | Medio; runtime Python + GIL | Sí, con wheels | No | Medio; madurez de integración y background |
| **Rust core** (`flutter_rust_bridge`) | No | Muy alto | Muy alto | Sí | Parcial (WASM) | Alto; ffmpeg/ONNX cross-compile |
| **Servidor/cliente** | Sí | Bajo | Depende de red | Sí, como cliente | Sí | Depende de PC/servidor; no offline total |

### Recomendación

**Objetivo: Dart puro, con spike previo.** Es la única opción que cumple
simultáneamente “un solo lenguaje”, “sin runtime Python”, “mejor tamaño y
arranque” y “Web cuando se pueda”. La viabilidad está respaldada por:

- `sherpa_onnx` 2.0.1: TTS local, todas las plataformas, incluida WebAssembly.
- `ffmpeg_kit_flutter_new_audio` 2.5.8: FFmpeg 8.1.2 en Android/iOS/macOS/
  Windows x64/Linux x64.
- `drift` 2.35: SQLite nativo en todas las plataformas, con FTS5 e isolates.
- `epub_plus` 5.1.0 (MIT) como base vendorizable para el parser.
- `flutter_widget_from_html_core` 0.17.4 para el modo Original simplificado.

**Condición:** un spike de 2–3 semanas debe validar Kokoro español, el lector
paginado con karaoke, FFmpeg/M4B en Android y la mezcla de ambience. Si falla,
se adopta **Python embebido** como plan de contingencia: conserva el motor y
los 531 tests, usa Flutter para la UI y `serious_python` para el runtime. Esa
decisión queda documentada como ADR-0001.

## 4. Gestión de estado e inyección de dependencias

| Opción | Modelo | Fortalezas | Debilidades | Veredicto |
|---|---|---|---|---|
| **Riverpod 3.5** | Providers + Notifier/AsyncNotifier | DI compile-safe, caching async, auto-dispose, overrides de test, codegen, muy adoptado | Curva inicial; codegen; el equipo debe seguir convenciones | **Elegido** |
| Bloc 9.1 | Events → States | Explícito, trazable, buen testing | Más boilerplate; eventos/estados para cada pantalla; DI separada | Alternativa válida para equipos con cultura Bloc; no se mezcla |
| Provider | InheritedWidget+ChangeNotifier | Simple, oficial | No DI/caching async; escalabilidad limitada | Descartado para app grande |
| get_it + injectable | Service locator | Simple, sin BuildContext | Estado global mutable; test isolation manual; duplica DI si se usa Riverpod | Descartado |

**Decisión:** Riverpod es estado + DI. No se usa `get_it` ni un service locator
paralelo. Los servicios puros se exponen con `Provider`; los estados de pantalla
con `Notifier`/`AsyncNotifier`; los jobs con un `Notifier` dedicado y streams.

## 5. Navegación

| Opción | Fortalezas | Debilidades | Veredicto |
|---|---|---|---|
| **go_router 18.1** | Oficial, deep links, ShellRoute, typed routes con builder, Web | API extensa; requiere disciplina de rutas | **Elegido** |
| auto_route 11.2 | Codegen fuerte, tipado, tabs/nested | Menos “oficial”; más magia; otro generador | Descartado |
| Navigator 1/2 directo | Sin dependencia | Duplicación y errores en una app con 8+ rutas y shells | Descartado |

Rutas: `/`, `/import`, `/books/:id`, `/books/:id/studio`, `/books/:id/read`,
`/settings`, `/settings/providers`, `/settings/engines`, `/ambience`.
`StatefulShellRoute` para sidebar desktop/bottom nav mobile.

## 6. Modelos y serialización

| Opción | Fortalezas | Debilidades | Veredicto |
|---|---|---|---|
| **Freezed 4 + json_serializable 6.15** | Inmutabilidad, copyWith, unions, JSON, equality; recomendado por Flutter docs | build_runner; tiempo de generación | **Elegido** |
| built_value | Maduro, serialización explícita | Más verbose; codegen pesado | Descartado |
| dart_mappable | Codegen más rápido | Menos adopción en el ecosistema; no aporta unions tan claras | Descartado |
| clases manuales | Cero deps | Errores de igualdad/JSON; mucho boilerplate | Descartado para dominio |

Se separan **DTOs de API** y **modelos de dominio** cuando el mapeo aporta
claridad (p. ej. respuestas de proveedores vs `TtsRequest`). No se duplican
modelos sin motivo.

## 7. Persistencia

| Opción | Modelo | Plataformas | Migraciones | FTS | Veredicto |
|---|---|---|---|---|---|
| **Drift 2.35** | SQLite relacional + DAOs | Todas | Sí, schema exports y tests | FTS5 | **Elegido** |
| Isar 3.1 | NoSQL embebido | Todas | Limitadas | No | Descartado: última release 2023, Dart 2; `isar_community` tiene baja adopción |
| ObjectBox 5.3 | NoSQL | Todas | Sí | No | Descartado: NoSQL para datos relacionales; dependencia binaria comercial/extra |
| Sembast 3.10 | NoSQL JSON | Todas | Manual | No | Descartado para biblioteca/consultas |
| Hive CE 2.23 | Key-value | Todas | Manual | No | Solo para preferencias simples, no biblioteca |
| sqflite 2.4 | SQLite plugin | Android/iOS/macOS | Manual | Sí | Descartado: no Windows/Linux |

**Drift** permite queries tipadas, streams reactivos, transacciones, joins,
FTS5 para búsqueda y ejecución en isolate. `sqlite3` 3.x incorpora SQLite
automáticamente; **no** se agrega `sqlite3_flutter_libs` (EOL). La biblioteca
en disco sigue siendo la fuente de verdad; Drift es el índice/estado.

## 8. HTTP y servicios externos

| Opción | Fortalezas | Debilidades | Veredicto |
|---|---|---|---|
| **Dio 5.11** | Interceptores, cancelación, timeouts, progreso, adapters, retries | API grande; hay que configurar bien | **Elegido** |
| http 1.6 | Simple, oficial-ish | Sin interceptores/cancelación/progreso; se duplica lógica | Descartado para TTS/descargas |
| gRPC | Eficiente | No aplica a APIs REST/WebSocket | Descartado |

Clientes específicos: Edge TTS por WebSocket; Gemini/ElevenLabs/Azure por
HTTP/WebSocket; VEP por HTTP/JSON. Todos con timeouts, reintentos con backoff,
cancelación y límites de tamaño. Las claves viven en `flutter_secure_storage`,
nunca en logs.

## 9. Audio y reproducción

| Opción | Plataformas | Background | Fortalezas | Debilidades |
|---|---|---|---|---|
| **just_audio 0.10 + audio_service 0.18** | Android/iOS/macOS/Web (+ desktop vía media_kit) | Android/iOS/macOS | Player maduro, posición/velocidad, notificación, lock screen | Windows/Linux requieren `just_audio_media_kit`; background desktop no aplica |
| media_kit 1.2 | Todas | Android/iOS vía servicio propio | Excelente rendimiento, libmpv, audio/video | Integración con `audio_service` no es de primera clase; tamaño |
| audioplayers 6.8 | Todas | Limitado | Simple, multiplataforma | Menos control de sesión/background que just_audio |

**Decisión:** `PlaybackService` abstracto.
- Android/iOS/macOS: `just_audio` + `audio_service` + `audio_session`.
- Windows/Linux: `just_audio` + `just_audio_media_kit`.
- Web: `just_audio` con limitaciones de autoplay/background.
- Si `just_audio_media_kit` no rinde, se cambia la implementación desktop a
  `media_kit` sin tocar la UI.

## 10. TTS local

| Opción | Modelos | Plataformas | Timings | Madurez | Veredicto |
|---|---|---|---|---|---|
| **sherpa_onnx 2.0.1** | Piper/VITS/Kokoro (según modelo) | Todas + WASM | Segmento (estimar palabra) | Apache-2.0, activo | **Elegido para Piper/VITS** |
| flutter_onnxruntime 1.9 | ONNX genérico | Todas | No | 53 likes, activo | Alternativa para Kokoro si hace falta |
| kokoro_tts_flutter 0.2 | Kokoro | Android/iOS/desktop | No | 13 likes, 2025 | Riesgo; no se adopta sin spike |
| flutter_tts 4.2 | Voces del sistema | Android/iOS/macOS/Windows/Web | No | Maduro | Fallback de eSpeak/sistema, no motor principal |

**Kokoro español:** el modelo `kokoro-v1.0.onnx` que usa Vibebook es
multilingüe y las voces `ef_dora`, `em_alex`, `em_santa` son españolas. Los
modelos que sherpa-onnx publica de Kokoro solo agregan inglés/chino. Por eso
Kokoro español requiere:
- un frontend G2P español + tokenización + `flutter_onnxruntime`, o
- conservar el motor Python para Kokoro, o
- reemplazarlo por Piper español + cloud.

Es el riesgo #1 del camino Dart puro y se valida en el spike. Piper español
(`es_MX-ald-medium`) sí es viable vía sherpa-onnx.

## 11. ffmpeg, M4B y audio de ambience

| Opción | Cobertura | Licencia | Riesgo |
|---|---|---|---|
| **ffmpeg_kit_flutter_new_audio 2.5.8** | Android/iOS/macOS/Win x64/Linux x64; FFmpeg 8.1.2 | LGPL-3.0 (sin GPL) | Sin Win/Linux ARM64; tamaño; fork comunitario |
| ffmpeg_kit_flutter 6.0.3 | Android/iOS/macOS | LGPL/GPL | **Discontinuado** |
| media_kit/libmpv | Todas | LGPL/GPL según build | Reproducción, no ensamblado/M4B |
| FFmpeg del sistema | Linux/macOS; Windows si está instalado | Según build | UX: depende del usuario; no mobile |
| Binario FFmpeg propio | Todas si se compila | Según build | CI/cross-compile; tamaño; actualizaciones |

**Decisión:** FFmpegKit audio en las plataformas cubiertas; en Windows/Linux
ARM64, binario FFmpeg empaquetado o fallback al sistema, con detección y
mensaje claro. La app no debe fallar silenciosamente: si no hay motor de audio,
se ofrece conversión sin M4B o descarga de un runtime.

## 12. EPUB y lector

| Opción | Parsing | Render | Plataformas | Veredicto |
|---|---|---|---|---|
| **epub_plus 5.1.0 (fork/vendor)** | OPF/NCX/HTML/imágenes | No renderiza | Todas | **Base elegida**; se vendoriza y se extiende |
| epubx 4.0 | Similar, más viejo | No | Todas | Base del fork; no se usa directo |
| flureadium 0.19 (Readium) | Muy completo | Sí (EPUB/PDF/audio) | Android/iOS/macOS/Web | Descartado: sin Windows/Linux |
| flutter_epub_viewer_kit | Básico | Sí | Android/iOS/Web | Descartado: no desktop |
| Lector propio | Control total | Flutter widgets | Todas | **Elegido para Texto/Libro** |
| WebView | EPUB.js | Fiel | Mobile/desktop con plugins variables | Solo modo Original si se aprueba |

El parser se vendoriza (MIT) para corregir encoding determinista, TOC,
imágenes y estructura sin depender de un paquete sin mantenimiento. El lector
propio usa `TextPainter`/`RichText` para paginar y resaltar karaoke; el modo
Original usa `flutter_widget_from_html_core` con CSS simplificado o un WebView
por plataforma, decisión pendiente.

## 13. i18n, iconos y diseño

| Responsabilidad | Elección | Alternativa | Motivo |
|---|---|---|---|
| i18n | `flutter_localizations` + `intl` + ARB | slang 4.19 | Oficial, sin dependencia extra; ARB y `gen_l10n` cubren es/en y plurales. slang queda como opción si se necesita runtime switching avanzado |
| Iconos | `lucide_icons_flutter` 4.0.3 | Material Symbols, Phosphor | Conserva el lenguaje visual actual (Lucide), activo y multiplataforma |
| Tema | Material 3 + `ThemeExtension` custom | shadcn_ui, forui | Control total de la identidad Biblioteca sin adoptar otro sistema |
| Animación | APIs de Flutter + `flutter_animate` puntual | Rive/Lottie | Evitar dependencias pesadas; Rive solo si hay una ilustración que lo justifique |
| Gráficos | `fl_chart` 1.3 si hace falta | syncfusion (licencia) | Solo para métricas/estadísticas; no es core |

## 14. Testing, calidad y logging

| Responsabilidad | Elección | Alternativa | Motivo |
|---|---|---|---|
| Unit/widget | `flutter_test` | — | SDK |
| Integración | `integration_test` + `patrol` 4.11 | Appium | Patrol maneja file picker/permisos/notificaciones |
| Golden | `alchemist` 0.14 | golden_toolkit (discontinuado) | Activo, múltiples temas/tamaños |
| Mocks | `mocktail` 1.0.5 | mockito | Sin codegen |
| Lints | `very_good_analysis` 11 + `riverpod_lint` 3.2 | flutter_lints | Más estricto; detecta problemas de Riverpod |
| Logs | `talker` 5.2 + `talker_flutter` | logger, Sentry | Logs en app, historial, reporte; Sentry opcional |
| Crash reporting | `sentry_flutter` 10.4 (opt-in) | Firebase Crashlytics | Privacidad; no se activa por defecto |

## 15. Distribución y updates

| Plataforma | Instalador | Update | Firma |
|---|---|---|---|
| Windows x64/ARM64 | Inno Setup 7.1 (x64/ARM64) + ZIP portable | `desktop_updater` 3.2 (Inno/ZIP) | Authenticode opcional |
| macOS arm64/x64 | DMG | `desktop_updater` + helper/notarización | Apple Developer |
| Linux x64/ARM64 | AppImage + DEB + Flatpak | Flatpak/DEB o `desktop_updater` Linux (preview) | GPG/Flatpak |
| Android arm64 | AAB/APK | Play Store o sideload manual | Keystore |
| iOS | IPA/TestFlight | App Store | Apple Developer |
| Web | Sitio estático/PWA | Deploy | TLS |

`desktop_updater` se eligió por updates firmados con Ed25519, UI integrada y
cobertura Windows/macOS/Linux; Linux sigue en preview. Alternativas:
`auto_updater` (solo Windows/macOS), `flutter_distributor` (discontinuado),
Sparkle nativo (solo macOS).

## 16. Dependencias descartadas y por qué

- **Isar / isar_community:** la versión principal es de 2023 y Dart 2; la
  comunidad tiene baja adopción. Drift es más seguro.
- **sqlite3_flutter_libs:** EOL desde sqlite3 3.x; no se agrega.
- **ffmpeg_kit_flutter:** discontinuado; se usa el fork `_new_audio`.
- **golden_toolkit:** discontinuado; Alchemist.
- **flutter_distributor:** discontinuado.
- **get_it + injectable:** duplica la DI de Riverpod.
- **auto_route:** go_router es la recomendación oficial.
- **flutter_html 3.0:** paquete con pocos puntos y sin actualización reciente;
  `flutter_widget_from_html_core` está activo.
- **lucide_icons (original):** incompatible con Dart 3; se usa
  `lucide_icons_flutter`.
- **Kokoro Flutter packages de baja adopción:** no se adoptan sin spike.

## 17. Resumen de decisiones

| Decisión | Elección | Estado |
|---|---|---|
| Framework | Flutter 3.50 | Aprobado técnicamente |
| Motor | Dart puro con spike; Python embebido como fallback | **Pendiente G1** |
| Estado/DI | Riverpod 3.5 | Recomendado |
| Navegación | go_router 18.1 | Recomendado |
| Modelos | Freezed 4 + json_serializable | Recomendado |
| DB | Drift 2.35 | Recomendado |
| HTTP | Dio 5.11 | Recomendado |
| Audio | just_audio + audio_service + media_kit desktop | Recomendado |
| TTS local | sherpa_onnx; Kokoro con spike | **Pendiente G2** |
| FFmpeg | ffmpeg_kit_flutter_new_audio + fallback ARM64 | Recomendado |
| EPUB | fork de epub_plus + lector propio | Recomendado |
| i18n | gen_l10n + ARB | Recomendado |
| Updates | desktop_updater | Recomendado |
| Firma | Authenticode/Apple Developer | **Pendiente G4** |
