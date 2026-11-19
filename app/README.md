# Vibebook Flutter

Implementación Flutter de Vibebook. Convive con la app Tauri/Python existente
mientras se completa la migración. **La app Tauri/Python sigue siendo la
release estable**; esta rama no crea tags ni publicaciones.

## Estado actual

- **Biblioteca local**: escanea `<library>/<slug>-<hash>/manifest.json`,
  muestra portadas, búsqueda, detalle, estado de conversión y eliminación con
  confirmación.
- **Importación EPUB**: validación, decodificación determinista
  UTF-8/Windows-1252, estructura/TOC, imágenes, portada, detección de idioma y
  manifiesto compatible con la app Python.
- **Lector**: texto, índice, búsqueda dentro del libro, paletas
  paper/sepia/night, tamaño de letra, ilustraciones, reproducción de audio por
  capítulo con velocidad/volumen, y avance automático al terminar
  (configurable).
- **Karaoke**: lee los timings por segmento y resalta la palabra activa. Los
  timings nuevos se estiman a partir de la duración real de cada segmento.
- **TTS local real**: Piper mediante `sherpa-onnx` + `piper-phonemize`, en un
  isolate aparte para no bloquear la interfaz.
- **Motor Edge (online, experimental)**: voces neuronales de Microsoft vía el
  servicio Read Aloud, con karaoke por palabra real (`native_word`),
  reintentos y cooldowns. No oficial: el texto sale del equipo.
- **Voces**: catálogo con descarga e instalación de modelos Piper (España y
  México), instalación offline desde `.tar.bz2` y detección de modelos locales.
- **Salida**: MP3 por capítulo (64 kbps mono) con fallback a WAV y exportación
  M4B con capítulos usando FFmpegKit.
- **Ambiente**: seis grabaciones de campo CC0 (lluvia, viento, mar, fuego,
  noche, bosque), con loops de 90 s, reproducción en vivo con atenuación bajo
  la voz, exportación de **M4B ambientado** y un plan por capítulo basado en
  palabras clave del texto.
- **Marcadores y posición**: se guardan en `bookmarks.json` junto al libro,
  con salto al capítulo/segundo guardado y restauración al abrir el lector.
- **Ajustes**: tema, paleta, lectura, biblioteca, modelos, velocidad de voz,
  ambiente y datos de versión.
- **Instalador Windows**: script de Inno Setup y job de CI sin firma.
- **Android**: configuración de firma opcional por `key.properties`; sin
  keystore el APK queda firmado con la clave de debug.
- **Tests**: 59 pruebas de texto, modelos, ingest EPUB, repositorio, timings,
  WAV, ambiente, plan por capítulo, reproducción, navegación del lector,
  catálogo de voces, DRM/token Edge, cliente y sintetizador Edge, bookmarks y
  widget.

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
- Android: directorio de documentos de la app / `library`

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

Voces incluidas en el catálogo (todas en español):

- Davefx (España, masculina media, CC0).
- Sharvard (España, masculina media, CC-BY 3.0; el modelo trae 2 oradores).
- Carlfm (España, masculina liviana x_low de 16 kHz, dominio público).
- GLaDOS (España, robótica, sin licencia declarada).
- Ald (México, masculina media, Unlicense).
- Claude (México, masculina alta, Apache-2.0).
- Daniela (Argentina, femenina alta, CC-BY-SA 4.0).

Las licencias indicadas son las del dataset de entrenamiento; el enlace de
cada voz en el catálogo apunta a su model card.

### Voces externas y crear la propia

Cualquier voz Piper compatible se puede usar sin tocar la app: descargá el
`.onnx` + `tokens.txt` + `.onnx.json` (por ejemplo de
`rhasspy/piper-voices`), ponelos en una subcarpeta de la carpeta de modelos
y la app la detecta al escanear. El `.onnx.json` importa: define el sample
rate, la voz de espeak y los parámetros de inferencia.

Crear una voz propia es posible pero no es clonación: hay que entrenar un
modelo VITS con un dataset propio (horas de audio limpio + transcripciones)
con `piper_train` y exportarlo a ONNX. Requiere GPU o mucha paciencia en
CPU. Para "mi propia voz" sin entrenar, los motores online (Edge, Azure,
ElevenLabs) son el camino realista; Piper queda para voces ya entrenadas.

## Verificación

```bash
flutter analyze
flutter test
```

La app incluye modos de verificación sin interfaz, útiles para CI o para
diagnosticar una instalación:

```bash
# Una frase -> WAV (Piper)
vibebook_app --tts-smoke <model-dir> <out.wav> <out.json>

# Una frase -> WAV (Edge, online y manual; no entra a CI)
vibebook_app --edge-tts-smoke <es-ES-ElviraNeural> <out.wav> <out.json>

# EPUB -> biblioteca -> audio/timings reales con Edge (online, manual)
vibebook_app --edge-convert-smoke <book.epub> <library-dir> <voice> <out.json> [chapters]

# EPUB -> biblioteca -> audio/timings reales
vibebook_app --convert-smoke <model-dir> <book.epub> <library-dir> <out.json> [chapters]

# Exportar M4B de un libro ya convertido
vibebook_app --m4b-smoke <book-dir> <out.json> [out.m4b]

# Exportar un M4B con ambiente
vibebook_app --ambient-m4b-smoke <book-dir> <preset> <out.json> [out.m4b]
```

El plan de ambiente se genera desde el Estudio con **Analizar capítulos** y se
guarda en `<libro>/ambience/plan_flutter.json` (no sobrescribe el plan de la app
Tauri/Python).

Resultados medidos en Windows durante esta iteración:

- Piper: 8,9 s de audio en ~1,1 s de síntesis.
- Edge (online, real): 7,3 s de audio con 21 límites de palabra en una frase.
- Edge completo (online, real): EPUB de 1 capítulo / 80 párrafos → 21:31 de
  audio con karaoke `native_word` en ~3,4 min.
- Libro real de 1 capítulo (21.579 caracteres, 20:25 de audio): conversión
  completa en ~167 s.
- M4B de ese capítulo: 9,8 MB; con ambiente mezclado: 10,2 MB.
- Seis grabaciones de campo CC0 convertidas a loops de 90 s (1,44 MB cada una).
- M4B ambientado con ducking y plan por capítulo: verificado con FFmpegKit.
- APK arm64: **182,7 MB** con Piper, sherpa-onnx y FFmpegKit.
- Reproducción MP3: posición avanzando y estado `playing` verificados.

## Build

```bash
flutter build windows --release
flutter build apk --release --target-platform android-arm64
flutter build linux --release
flutter build macos --release   # solo en macOS
```

### Instalador de Windows

```powershell
flutter build windows --release
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\windows\vibebook.iss
# app/dist/Vibebook-Setup-0.1.0.exe
```

Es un instalador **sin firma**: SmartScreen puede advertir. Ver
[`packaging/windows/README.md`](packaging/windows/README.md).

### Firma de Android

Copiá `android/key.properties.example` a `android/key.properties`, apuntá
`storeFile` a tu keystore y completá las contraseñas. Sin ese archivo, el APK
de release se firma con la clave de debug y **no debe distribuirse**.

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
  libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
  libjson-glib-dev
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

## Artefactos de prueba

Esta rama genera artefactos para probar, **no una release**. No se crearon
tags, versiones ni publicaciones; la app Tauri sigue siendo la estable hasta
que la prueba y la aprobación explícita habiliten el cutover.

- Windows: `dist/Vibebook-Setup-0.1.0.exe` (sin firma) y
  `Vibebook-windows-portable.zip`.
- Android: `build/app/outputs/flutter-apk/app-release.apk` (arm64; sin keystore
  propio queda firmado con debug, solo para pruebas).
- macOS: `Vibebook-macos-arm64.dmg` y `Vibebook-macos-x64.dmg` desde el
  workflow `Flutter` (sin firma).
- Linux: `vibebook-linux-x64.tar.gz` desde el workflow `Flutter`.

## Limitaciones actuales

- **Edge TTS es un servicio no oficial**: el texto se envía a Microsoft, puede
  limitar peticiones, fallar o desaparecer sin aviso. Piper sigue siendo el
  motor recomendado para uso offline y estable.

- El plan de ambiente es **heurístico** (palabras clave en español/inglés), no
  comprensión semántica. Los capítulos sin señales claras quedan sin ambiente y
  usan el paisaje global.
- Los bookmarks/posición usan un **JSON por libro**, no Drift. Es portable y
  suficiente para esta etapa, pero falta migrar la base de datos completa.
- El lector es de **scroll continuo**: faltan el modo paginado/Libro y el modo
  Original.
- No hay **audio en segundo plano** con pantalla apagada ni controles de media
  session.
- El instalador de Windows y los DMG de macOS son **sin firma**. No hay
  auto-update ni notarización.
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
  data/                # EPUB, biblioteca, settings, M4B, bookmarks, TTS
    ambience/          # biblioteca de grabaciones, analizador y plan
    tts/               # modelos, catálogo, descarga, worker, conversión
  domain/              # modelos, timings, bookmarks, presets y plan
  features/            # library, import, detail, studio, reader, settings
  dev/                 # modos de verificación sin interfaz
assets/ambience/       # loops CC0 y créditos
packaging/windows/     # script de Inno Setup
test/                  # unit/widget/ingest/library/tts/ambience/bookmarks tests
```
