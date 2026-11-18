# Vibebook Flutter

Primera implementación Flutter de Vibebook. Convive con la app Tauri/Python
existente mientras se completa la migración.

## Estado actual

- Biblioteca local: escanea `<library>/<slug>-<hash>/manifest.json`, muestra
  portadas, búsqueda y detalle.
- Importación EPUB: valida, decodifica XHTML (UTF-8/Windows-1252), extrae
  capítulos, TOC, imágenes y portada, detecta el idioma y escribe un manifiesto
  compatible con la app Python.
- Lector de texto con índice, paletas paper/sepia/night, tamaño de letra y
  reproducción de audio por capítulo cuando existe.
- Estudio con selección de motor/voz y una conversión **demo** que genera WAV de
  silencio para validar el pipeline. La síntesis real y el M4B son la siguiente
  fase.
- Ajustes: tema, paleta, lectura, carpeta de biblioteca y datos de versión.
- Tests de texto, modelos, ingest EPUB, repositorio de biblioteca y widget.

## Requisitos

- Flutter 3.50+ / Dart 3.14.
- Para Windows: Visual Studio Build Tools con C++.
- Para Android: Android SDK 36, build-tools 36, NDK 28.2 y JDK 17+.
- `ffmpeg` no es necesario para el modo demo.

## Ejecutar

```bash
cd app
flutter pub get
flutter run -d windows
# o
flutter run -d <android-device>
```

La biblioteca se detecta automáticamente:

- Windows: `%LOCALAPPDATA%\vibebook\vibebook\library`
- Linux: `$XDG_DATA_HOME/vibebook/library` o `~/.local/share/vibebook/library`
- macOS: `~/Library/Application Support/vibebook/library`
- Android/iOS: directorio de documentos de la app / `library`

Se puede cambiar desde **Ajustes → Biblioteca**.

## Tests

```bash
flutter analyze
flutter test
```

## Build

```bash
flutter build windows --release
flutter build apk --release --target-platform android-arm64
```

Medici?n local de esta iteraci?n: APK arm64 de **171,9 MB** con FFmpegKit y
las librer?as de sherpa-onnx incluidas.

## Limitaciones de esta primera iteración

- La conversión es demo (silencio), no TTS real.
- No hay M4B, ambience ni karaoke por palabra todavía.
- No hay firma ni instaladores.
- La app Tauri/Python sigue siendo la release estable.
- En Windows, Flutter necesita Developer Mode para enlaces simbólicos de
  plugins; si no está habilitado, se pueden usar junctions en
  `windows/flutter/ephemeral/.plugin_symlinks` (ver `docs/refactor/`).

## Estructura

```text
lib/
  app/                 # MaterialApp, router, shell, providers
  core/                # texto, tokens, tema, componentes
  data/                # EPUB, biblioteca, settings, conversión demo
  domain/              # modelos
  features/            # library, import, detail, studio, reader, settings
test/                  # unit/widget/ingest/library tests
```
