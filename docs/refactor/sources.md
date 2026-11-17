# Fuentes y método de investigación

## Método

- Auditoría del repo: código, docs, tests, CI, workflows y releases.
- Consulta de documentación oficial y pub.dev entre el 16 y el 17 de noviembre
  de 2026.
- Comparación por criterios de compatibilidad, mantenimiento, rendimiento,
  encaje con el dominio, testing y costo de migración.
- Las métricas de pub.dev (likes, descargas, puntos) se usan como señal de
  adopción, **no** como benchmark de rendimiento.
- Los números de rendimiento de Flutter en `07-performance.md` son objetivos
  propuestos; se validan en el spike F0. Los números actuales de Tauri/Python
  salen de `docs/performance.md` y `docs/release.md`.

## Documentación oficial y paquetes

### Flutter / Dart

- Flutter, plataformas soportadas (3.50):
  https://docs.flutter.dev/reference/supported-platforms
- Flutter, guía de arquitectura:
  https://docs.flutter.dev/app-architecture/guide
- Flutter, recomendaciones de arquitectura:
  https://docs.flutter.dev/app-architecture/recommendations
- Flutter, performance best practices:
  https://docs.flutter.dev/perf/best-practices
- Flutter, desktop:
  https://docs.flutter.dev/platform-integration/desktop
- Flutter, isolates/concurrency:
  https://docs.flutter.dev/perf/isolates
- Flutter, app size:
  https://docs.flutter.dev/perf/app-size
- Flutter, integración:
  https://docs.flutter.dev/testing/integration-tests

### Estado, navegación, modelos y datos

- Riverpod: https://pub.dev/packages/flutter_riverpod
- Riverpod generator: https://pub.dev/packages/riverpod_generator
- Bloc: https://pub.dev/packages/flutter_bloc
- go_router: https://pub.dev/packages/go_router
- go_router_builder: https://pub.dev/packages/go_router_builder
- auto_route: https://pub.dev/packages/auto_route
- Freezed: https://pub.dev/packages/freezed
- json_serializable: https://pub.dev/packages/json_serializable
- Drift: https://pub.dev/packages/drift
- Drift, plataformas: https://drift.simonbinder.eu/platforms/
- Drift, migraciones: https://drift.simonbinder.eu/migrations/
- sqlite3: https://pub.dev/packages/sqlite3
- sqlite3_flutter_libs (EOL): https://pub.dev/packages/sqlite3_flutter_libs
- Isar: https://pub.dev/packages/isar
- isar_community: https://pub.dev/packages/isar_community
- ObjectBox: https://pub.dev/packages/objectbox
- Sembast: https://pub.dev/packages/sembast
- Hive CE: https://pub.dev/packages/hive_ce
- Dio: https://pub.dev/packages/dio
- http: https://pub.dev/packages/http

### Audio, TTS y FFmpeg

- just_audio: https://pub.dev/packages/just_audio
- audio_service: https://pub.dev/packages/audio_service
- audio_session: https://pub.dev/packages/audio_session
- media_kit: https://pub.dev/packages/media_kit
- just_audio_media_kit: https://pub.dev/packages/just_audio_media_kit
- audioplayers: https://pub.dev/packages/audioplayers
- sherpa_onnx: https://pub.dev/packages/sherpa_onnx
- sherpa-onnx, TTS: https://k2-fsa.github.io/sherpa/onnx/tts/index.html
- sherpa-onnx, Kokoro: https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/kokoro.html
- sherpa-onnx, Piper: https://k2-fsa.github.io/sherpa/onnx/tts/piper.html
- sherpa-onnx, Flutter: https://k2-fsa.github.io/sherpa/onnx/flutter/index.html
- flutter_onnxruntime: https://pub.dev/packages/flutter_onnxruntime
- ffmpeg_kit_flutter_new: https://pub.dev/packages/ffmpeg_kit_flutter_new
- ffmpeg_kit_flutter_new_audio: https://pub.dev/packages/ffmpeg_kit_flutter_new_audio
- ffmpeg_kit_flutter (discontinuado): https://pub.dev/packages/ffmpeg_kit_flutter
- edge_tts Dart: https://pub.dev/packages/edge_tts
- flutter_tts: https://pub.dev/packages/flutter_tts

### EPUB y render

- epub_plus: https://pub.dev/packages/epub_plus
- epubx: https://pub.dev/packages/epubx
- epub_parser: https://pub.dev/packages/epub_parser
- flureadium: https://pub.dev/packages/flureadium
- flutter_epub_viewer_kit: https://pub.dev/packages/flutter_epub_viewer_kit
- flutter_widget_from_html_core: https://pub.dev/packages/flutter_widget_from_html_core
- flutter_html: https://pub.dev/packages/flutter_html
- archive: https://pub.dev/packages/archive
- xml: https://pub.dev/packages/xml
- html: https://pub.dev/packages/html

### UI, iconos, i18n y testing

- Material 3: https://m3.material.io/
- lucide_icons_flutter: https://pub.dev/packages/lucide_icons_flutter
- flutter_localizations: https://docs.flutter.dev/ui/accessibility-and-internationalization/internationalization
- intl: https://pub.dev/packages/intl
- slang: https://pub.dev/packages/slang
- alchemist: https://pub.dev/packages/alchemist
- patrol: https://pub.dev/packages/patrol
- integration_test: https://docs.flutter.dev/testing/integration-tests
- mocktail: https://pub.dev/packages/mocktail
- very_good_analysis: https://pub.dev/packages/very_good_analysis
- riverpod_lint: https://pub.dev/packages/riverpod_lint
- talker: https://pub.dev/packages/talker
- sentry_flutter: https://pub.dev/packages/sentry_flutter

### Distribución y updates

- desktop_updater: https://pub.dev/packages/desktop_updater
- auto_updater: https://pub.dev/packages/auto_updater
- flutter_distributor (discontinuado): https://pub.dev/packages/flutter_distributor
- msix: https://pub.dev/packages/msix
- Inno Setup: https://jrsoftware.org/isinfo.php
- Inno Setup, arquitecturas:
  https://jrsoftware.org/ishelp/index.php?topic=archidentifiers
- Flutter Windows build architecture:
  https://docs.flutter.dev/release/breaking-changes/windows-build-architecture
- Android foreground services:
  https://developer.android.com/develop/background-work/services/fgs
- Android 16 KB page size:
  https://developer.android.com/guide/practices/page-sizes
- Apple notarization:
  https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution
- Flatpak: https://docs.flatpak.org/
- AppImage: https://appimage.org/

### Alternativas evaluadas

- .NET MAUI, plataformas:
  https://learn.microsoft.com/dotnet/maui/supported-platforms
- Compose Multiplatform:
  https://kotlinlang.org/compose-multiplatform/
- KMP:
  https://kotlinlang.org/docs/multiplatform.html
- Tauri mobile:
  https://v2.tauri.app/develop/
- Flet, paquetes binarios Android/iOS:
  https://flet.dev/docs/reference/binary-packages-android-ios/
- Flet, WebView: https://flet.dev/docs/controls/webview/
- pywebview, freezing/Android:
  https://pywebview.flowrl.com/guide/freezing.html
- Chaquopy: https://chaquo.com/chaquopy/
- serious_python: https://pub.dev/packages/serious_python

### Licencias

- AGPL-3.0: https://www.gnu.org/licenses/agpl-3.0.html
- LGPL-3.0: https://www.gnu.org/licenses/lgpl-3.0.html
- FFmpeg license: https://ffmpeg.org/legal.html
- SIL OFL: https://openfontlicense.org/
- Apache-2.0: https://www.apache.org/licenses/LICENSE-2.0
- MIT: https://opensource.org/license/mit

## Limitaciones de la investigación

- No se ejecutaron benchmarks de Flutter en hardware real; F0 los produce.
- No se probaron todos los paquetes en todas las arquitecturas; la matriz
  distingue “soportado” de “condicional”.
- Las APIs de proveedores cloud pueden cambiar; los clientes se aíslan.
- Los precios/cuotas de TTS no se evaluaron en detalle; son externos al stack.
- La disponibilidad de runners ARM64/macOS en CI depende de la cuenta.
- Las versiones exactas se fijan en F2/F3 con lockfiles; este documento usa
  versiones de referencia a noviembre de 2026.
