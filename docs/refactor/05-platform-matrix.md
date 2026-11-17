# 05 — Matriz de compatibilidad por plataforma

## 1. Principio

Flutter compila para muchas plataformas, pero **una app no es automáticamente
compatible**: los plugins nativos, los códecs, los permisos y el ciclo de vida
cambian. Esta matriz distingue:

- **Soportado:** se construye, se prueba y se publica.
- **Soportado con condiciones:** funciona, pero depende de un runtime/binario
  externo o de una limitación documentada.
- **Best-effort:** se intenta, no se garantiza.
- **No soportado:** no se promete.

## 2. Matriz general

| Plataforma | Arquitectura | Flutter | App | TTS local | ffmpeg/M4B | Audio background | Estado |
|---|---|---|---|---|---|---|---|
| Windows 10/11 | x64 | Sí | Sí | Sí | Sí | No aplica | **Soportado** |
| Windows 11 | ARM64 | Sí | Sí | Sí | Condicional¹ | No aplica | **Soportado con condiciones** |
| macOS 12+ | arm64 | Sí | Sí | Sí | Sí | Sí (app activa) | **Soportado** |
| macOS 12+ | x64 | Sí | Sí | Sí | Sí | Sí | **Soportado** (Intel en deprecación) |
| Linux x64 | x64 | Sí | Sí | Sí | Sí | No aplica | **Soportado** |
| Linux ARM64 | arm64 | Sí | Sí | Sí | Condicional¹ | No aplica | **Soportado con condiciones** |
| Android 7+ | arm64-v8a | Sí | Sí | Sí | Sí | Sí | **Soportado** |
| iOS 16+ | arm64 | Sí | Sí | Sí | Sí | Sí | **Soportado con condiciones²** |
| Web | wasm/js | Sí | Parcial | Parcial³ | No | Limitado | **Best-effort** |

¹ FFmpegKit no publica Windows/Linux ARM64. Se usa FFmpeg del sistema, un
binario empaquetado o emulación x64 (Windows 11 ARM64). La app debe detectar y
explicar la limitación.
² Requiere macOS + Apple Developer para firmar/notarizar; App Store o
TestFlight. El mínimo se fija en iOS 16 por los runtimes ONNX/FFmpeg.
³ `sherpa_onnx` tiene soporte WebAssembly, pero el modelo y el WASM pesan; el
ensamblado M4B y el acceso a archivos no están disponibles. Web se limita a
biblioteca/lector/cloud TTS o a un backend servidor.

## 3. Windows

### x64

- **Build:** `flutter build windows --release`.
- **Requisitos:** Windows 10 1809+; WebView2 no es necesario (Flutter usa su
  propio motor).
- **Nativos:** sherpa_onnx (x64), FFmpegKit audio (x64), sqlite3, just_audio +
  media_kit.
- **Instalador:** Inno Setup 7.1 (x64) + ZIP portable; `desktop_updater` para
  updates Inno/ZIP; Authenticode opcional.
- **Datos:** `%LOCALAPPDATA%\Vibebook`; modo portable con `portable.flag`.
- **Riesgos:** SmartScreen sin firma; codecs de audio; rutas no ASCII (probar
  `ø`, `ñ`).

### ARM64

- **Build:** Flutter 3.50 soporta Windows ARM64; se necesita SDK/host ARM64 o
  el canal/artefacto correspondiente. Verificar en CI con runner ARM64.
- **Nativos:** sherpa_onnx soporta arm64; FFmpegKit **no**. Opciones:
  1. FFmpeg del sistema (si está instalado).
  2. Binario FFmpeg ARM64 empaquetado (compilado con MSYS2/LLVM).
  3. Emulación x64 del binario FFmpeg (Windows 11 ARM64).
- **Decisión:** la app detecta la arquitectura y usa el fallback disponible;
  si no hay, permite convertir sin M4B o muestra un requisito claro.
- **Instalador:** Inno Setup 7 soporta `arm64`; `desktop_updater` debe probarse
  en ARM64 antes de prometer updates.

## 4. macOS

- **Build:** `flutter build macos --release`; arm64 y x64 (o universal).
- **Mínimo:** macOS 12+ (Monterey); Apple Silicon recomendado.
- **Nativos:** sherpa_onnx, FFmpegKit audio, sqlite3, just_audio/audio_service.
- **Empaquetado:** `.app` + DMG; `codesign`, hardened runtime, `notarytool`,
  staple; `desktop_updater` helper si se habilita auto-update.
- **Gatekeeper:** sin notarización, documentar clic derecho → Abrir y
  `xattr -dr com.apple.quarantine`.
- **Datos:** `~/Library/Application Support/com.vibebook.desktop`.
- **Riesgos:** Intel en deprecación por Flutter/macOS; binarios universales
  duplican tamaño; App Store requiere sandbox y revisión.

## 5. Linux

- **Build:** `flutter build linux --release`.
- **Requisitos:** GTK3, `libsecret-1-dev` (secure storage), `libjson-glib-dev`
  (FFmpegKit), `clang`, `cmake`, `ninja-build`, `pkg-config`.
- **Nativos:** sherpa_onnx x64/arm64; FFmpegKit x64; sqlite3; just_audio +
  media_kit.
- **Empaquetado:** AppImage (linuxdeploy/appimagetool), `.deb` (dpkg-deb),
  Flatpak (flatpak-builder). AppImage requiere FUSE2.
- **Updates:** Flatpak/DEB/APT recomendado; `desktop_updater` Linux es preview
  (solo ZIP directo), no prometer paridad con Windows/macOS.
- **ARM64:** Flutter soporta Linux ARM64; FFmpegKit no. Usar FFmpeg del sistema
  o binario propio; CI en runner ARM64.
- **Datos:** `~/.local/share/vibebook` (XDG).

## 6. Android

- **Build:** `flutter build appbundle --release --target-platform android-arm64`
  (y APK para sideload).
- **Mínimo:** Android 7.0 (API 24); target SDK actual de Flutter/Play.
- **Nativos:** sherpa_onnx arm64, FFmpegKit audio arm64, sqlite3, just_audio +
  audio_service.
- **Permisos:**
  - `READ_MEDIA_AUDIO`/`READ_EXTERNAL_STORAGE` solo si se importa audio;
  - `POST_NOTIFICATIONS` (Android 13+) para playback/conversión;
  - `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_MEDIA_PLAYBACK` y
    `FOREGROUND_SERVICE_DATA_SYNC` si hay jobs largos;
  - acceso por SAF para archivos elegidos; no se pide acceso total.
- **Background:** `audio_service` para playback; `flutter_foreground_task` o
  un servicio propio para conversión. Sin servicio, Android puede matar el job.
- **Almacenamiento:** biblioteca en almacenamiento interno de la app; importar
  copia el EPUB; exportar usa SAF/share.
- **Distribución:** AAB Play Store o APK firmado para sideload. Sin Play Store,
  updates manuales; no se promete auto-update.
- **Riesgos:** Doze/battery optimization; 16 KB page size (ONNX Runtime
  reciente); tamaño del APK; modelos descargados.

## 7. iOS

- **Build:** `flutter build ipa --release` en macOS; Xcode + Apple Developer.
- **Mínimo:** iOS 16+ (por ONNX/FFmpeg; confirmar con los pods finales).
- **Nativos:** sherpa_onnx iOS, FFmpegKit iOS, sqlite3, just_audio +
  audio_service.
- **Background:** `UIBackgroundModes` audio para playback; `BGProcessingTask`
  para conversiones largas (no garantizado; debe reanudar).
- **Archivos:** file picker + security-scoped URLs; se copia el EPUB a la
  biblioteca de la app.
- **Distribución:** App Store/TestFlight; sandbox; privacidad; sin ejecución
  de binarios descargados.
- **Riesgos:** revisión de App Store por descarga de modelos; tamaño; ONNX
  Runtime estático; FFmpeg LGPL notices; mínimo iOS.

## 8. Web

- **Build:** `flutter build web --wasm` (o JS).
- **Soportado:** biblioteca (si se usa backend/almacenamiento web), lector,
  búsqueda, bookmarks, ajustes, TTS cloud, quizá TTS local WASM.
- **No soportado:** ffmpeg/M4B, acceso libre al filesystem, background audio
  confiable, descarga de modelos grandes sin UX clara.
- **Drift:** `WasmDatabase` + worker; persistencia IndexedDB/OPFS.
- **`sherpa_onnx` Web:** WASM; validar tamaño/rendimiento; no se promete.
- **Decisión:** Web es **best-effort** y se define como “lector + nube” o se
  excluye del primer release. No se promete paridad.
- **PWA:** manifest, icons, service worker para assets; no para biblioteca
  grande.

## 9. Detección de plataforma y capacidades

No usar `Platform.isAndroid` disperso. Centralizar:

```text
PlatformInfo:
  os: windows | macos | linux | android | ios | web
  arch: x64 | arm64 | arm32 | wasm
  isDesktop, isMobile, isWeb
CapabilityService:
  localTts, localKokoro, ffmpeg, m4bExport, backgroundAudio,
  backgroundJobs, secureStorage, filePicker, autoUpdate
```

La UI consulta capacidades, no plataformas. Ejemplo: si `ffmpeg=false`, el botón
“Exportar M4B” se deshabilita con explicación; no se oculta sin más.

## 10. Servicios específicos por plataforma

| Servicio | Windows | macOS | Linux | Android | iOS | Web |
|---|---|---|---|---|---|---|
| File picker | file_selector | file_selector | file_selector | file_selector/SAF | UIDocumentPicker | input file |
| Secure storage | DPAPI | Keychain | libsecret | Keystore | Keychain | WebCrypto |
| Audio bg | — | audio_service | — | audio_service | audio_service | limitado |
| Jobs bg | isolate | isolate | isolate | foreground task | BGTask | limitado |
| Updates | desktop_updater | desktop_updater | Flatpak/DEB/preview | store/manual | App Store | deploy |
| Window/tray | window_manager/tray_manager | ídem | ídem | — | — | — |
| Share | share_plus | share_plus | share_plus | share_plus | share_plus | Web Share |
| Notifications | local notifications | local notifications | local notifications | local + channel | local + permisos | limitado |

## 11. Matriz de funcionalidades

| Feature | Win x64 | Win ARM64 | macOS | Linux x64 | Linux ARM64 | Android | iOS | Web |
|---|---|---|---|---|---|---|---|---|
| Biblioteca | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Importar EPUB | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Leer texto/libro | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| EPUB Original | ✅/⚠️ | ✅/⚠️ | ✅/⚠️ | ✅/⚠️ | ✅/⚠️ | ✅/⚠️ | ✅/⚠️ | ⚠️ |
| Audio + karaoke | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| TTS cloud | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Piper/VITS local | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Kokoro español | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| eSpeak/sistema | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| M4B | ✅ | ⚠️ | ✅ | ✅ | ⚠️ | ✅ | ✅ | ❌ |
| Ambience vivo | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Ambience export | ✅ | ⚠️ | ✅ | ✅ | ⚠️ | ✅ | ✅ | ❌ |
| Auto-update | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ❌ | ❌ | — |

Leyenda: ✅ soportado; ⚠️ condicional/limitado; ❌ no soportado; — no aplica.

## 12. CI por plataforma

| Runner | Jobs |
|---|---|
| `ubuntu-latest` | analyze, unit, widget, golden, build Linux x64, build Web |
| `windows-latest` | build Windows x64, installer, unit, integration desktop |
| `macos-15` | build macOS arm64, iOS, DMG |
| `macos-15-intel` | build macOS x64 |
| `ubuntu-24.04-arm` (si disponible) | build Linux ARM64 |
| `windows-11-arm` (si disponible) | build Windows ARM64 |
| Android emulator (Linux) | integration/Patrol |

Los runners ARM64 y iOS pueden ser costosos o no estar disponibles; se marcan
como “best effort” hasta validarlos. No se publica un artefacto sin probarlo.

## 13. Limitaciones documentadas que la UI debe mostrar

- Sin ffmpeg: “La exportación M4B no está disponible en esta arquitectura.
  Podés convertir a MP3 o instalar FFmpeg.”
- Sin keyring Linux: “Las claves se guardarán en un archivo local con permisos
  restringidos; instalá libsecret para usar el llavero.”
- Sin firma macOS: “Gatekeeper puede bloquear la app; usá clic derecho → Abrir.”
- Android sin servicio: “La conversión puede pausarse si la app queda en
  segundo plano.”
- Web: “El lector funciona; la conversión local no está disponible.”
- Kokoro no validado: “Kokoro español está en prueba; usá Piper o cloud.”
