# Vibebook Flutter

Implementación Flutter de Vibebook. Convive con la app Tauri/Python existente
mientras se completa la migración. **La app Tauri/Python sigue siendo la
release estable**; esta rama no crea tags ni publicaciones.

## Estado actual

- **Biblioteca local**: escanea `<library>/<slug>-<hash>/manifest.json`,
  muestra portadas, búsqueda, detalle y estado de conversión.
- **Importación EPUB**: validación, decodificación determinista
  UTF-8/Windows-1252, estructura/TOC, imágenes, portada, detección de idioma y
  manifiesto compatible con la app Python.
- **Lector**: texto, índice, paletas paper/sepia/night, tamaño de letra,
  ilustraciones y reproducción de audio por capítulo.
- **Karaoke**: lee los timings por segmento y resalta la palabra activa. Los
  timings nuevos se estiman a partir de la duración real de cada segmento.
- **TTS local real**: Piper mediante `sherpa-onnx` + `piper-phonemize`, en un
  isolate aparte para no bloquear la interfaz.
- **Voces**: catálogo con descarga e instalación de modelos Piper (España y
  México), instalación offline desde `.tar.bz2` y detección de modelos locales.
- **Salida**: MP3 por capítulo (64 kbps mono) con fallback a WAV y exportación
  M4B con capítulos usando FFmpegKit.
- **Ajustes**: tema, paleta, lectura, carpeta de biblioteca, carpeta de modelos,
  velocidad de voz y datos de versión.
- **Tests**: 19 pruebas de texto, modelos, ingest EPUB, repositorio, timings,
  WAV y widget.

## Requisitos

- Flutter 3.50+ / Dart 3.14.
- Windows: Visual Studio Build Tools con C++.
- Android: Android SDK 36, build-tools 36, NDK 28.2 y JDK 17+.
- No hace falta instalar `ffmpeg` por separado: FFmpegKit viene con la app.

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

## Voces locales

La forma más simple es abrir el **Estudio → Agregar voz** y descargar una voz
del catálogo. Las voces quedan en la carpeta de modelos de la app y se pueden
usar sin conexión.

También se puede copiar a mano una carpeta con:

```text
<nombre-del-modelo>/
  modelo.onnx
  tokens.txt
  modelo.onnx.json    # opcional: sample rate, voz espeak, inferencia
```

La carpeta de modelos se cambia desde **Ajustes → Voz** o desde el Estudio.
`espeak-ng-data` no hace falta en la carpeta del modelo: `piper-phonemize`
trae sus propios datos.

Voces incluidas en el catálogo:

- Davefx (español de España, CC0).
- Ald (español de México, Unlicense).

## Verificación

```bash
flutter analyze
flutter test
```

La app incluye modos de verificación sin interfaz, útiles para CI o para
diagnosticar una instalación:

```bash
# Una frase -> WAV
vibebook_app --tts-smoke <model-dir> <out.wav> <out.json>

# EPUB -> biblioteca -> audio/timings reales
vibebook_app --convert-smoke <model-dir> <book.epub> <library-dir> <out.json> [chapters]

# Exportar M4B de un libro ya convertido
vibebook_app --m4b-smoke <book-dir> <out.json> [out.m4b]

# Reproducir un audio con el plugin nativo
vibebook_app --audio-smoke <audio-file> <out.json>

# Instalar un .tar.bz2 o una entrada del catálogo sin interfaz
vibebook_app --install-smoke <archive.tar.bz2|catalog:id> <models-root> <out.json>
```

Resultados medidos en Windows durante esta iteración:

- Piper: 8,9 s de audio en ~1,1 s de síntesis.
- Libro de prueba de 6 capítulos (~4 min): conversión completa en ~42 s.
- M4B de 6 capítulos: 2,1 MB.
- APK arm64: **182,7 MB** con Piper, sherpa-onnx y FFmpegKit.
- Reproducción MP3: posición avanzando y estado `playing` verificados.

## Build

```bash
flutter build windows --release
flutter build apk --release --target-platform android-arm64
flutter build linux --release
flutter build macos --release   # solo en macOS
```

### macOS sin certificado (igual que la release Tauri)

`flutter build macos` **solo funciona en macOS** (Xcode + SDK de Apple). WSL es
Linux y no puede compilar macOS. No hace falta un certificado Apple Developer
para generar un `.dmg`: el build queda **sin firmar y sin notarizar**, igual
que los `.dmg` que ya publica la app Tauri.

El workflow de CI usa dos runners (`macos-15` y `macos-15-intel`) y publica:

- `Vibebook-macos-arm64.dmg`
- `Vibebook-macos-x64.dmg`

Para abrirlos en otra Mac:

```bash
xattr -dr com.apple.quarantine /Applications/Vibebook.app
# o clic derecho -> Abrir la primera vez
```

Sin firma/notarización, Gatekeeper muestra una advertencia. La firma y
notarización quedan pendientes y requieren una cuenta Apple Developer; la
release Tauri actual tiene la misma limitación.

### Linux / WSL

El proyecto Linux se genera y compila con las dependencias de GTK/GStreamer:

```bash
sudo apt-get install -y clang cmake ninja-build pkg-config \
  libgtk-3-dev libblkid-dev liblzma-dev libsecret-1-dev \
  libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev
flutter build linux --release
```

En WSL se puede compilar; para ver la ventana hace falta WSLg (Windows 11) o un
servidor X. El CI de Linux publica `vibebook-linux-x64.tar.gz`.

**iOS queda descartado** de esta migración por pedido explícito y por requerir
macOS, Xcode y credenciales de firma.

En Windows, si Developer Mode no está habilitado, Flutter no puede crear los
symlinks de plugins. La alternativa usada en este entorno es crear junctions en
`windows/flutter/ephemeral/.plugin_symlinks` a partir de
`.flutter-plugins-dependencies`; ver `docs/refactor/`.

También se agregó un fallback para rutas Windows con caracteres no ASCII: las
librerías nativas reciben la ruta corta 8.3 (`GetShortPathNameW`) cuando hace
falta, porque `piper-phonemize`/espeak-ng falla con rutas Unicode.

## Limitaciones actuales

- **Ambience** (paisajes sonoros en vivo y export ambientado) todavía no está.
- No hay **bookmarks/Drift** ni base de datos de estado de lectura; se guarda el
  último libro/capítulo en preferencias.
- No hay **audio en segundo plano** con pantalla apagada.
- No hay **firma, instaladores ni auto-update**.
- **macOS** se compila sin firma en CI y genera `.dmg` arm64/x64, pero no se
  probó en una Mac real. Gatekeeper pide confirmación, igual que en Tauri.
- **iOS** está descartado.
- **Android** compila, pero no se probó en un dispositivo físico.
- Los motores cloud (Edge, Gemini, ElevenLabs, Azure) no están conectados; la
  app usa Piper local.
- Web no está en el alcance de esta iteración (TTS nativo y FFmpegKit no
  aplican igual).
- En Android, un APK universal/arm64 pesa ~183 MB por las librerías nativas.

## Estructura

```text
lib/
  app/                 # MaterialApp, router, shell, providers
  core/                # texto, tokens, tema, componentes, rutas nativas
  data/                # EPUB, biblioteca, settings, M4B, TTS
    tts/               # modelos, catálogo, descarga, worker, conversión
  domain/              # modelos y timings
  features/            # library, import, detail, studio, reader, settings
  dev/                 # modos de verificación sin interfaz
test/                  # unit/widget/ingest/library/tts tests
```
