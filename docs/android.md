# Android lector-only (P4)

> Estado: **MVP de lector**. La app Android abre EPUB, guarda la biblioteca y la
> posición en el dispositivo, y no incluye Python, ffmpeg ni conversión.

## Decisión

Android no corre el sidecar Python de forma práctica: PyInstaller no soporta
Android y embeber Python multiplica tamaño y complejidad. Por eso la app Android:

- importa EPUB con el file picker del WebView;
- guarda bytes y CFI en IndexedDB;
- renderiza con Epub.js;
- recuerda la última página;
- no convierte, no usa red y no requiere cuenta.

La app de escritorio sigue siendo el lugar para convertir, ambientar y exportar.

## Estructura

```text
web/mobile.html                  entrada del lector
web/src/mobile/MobileReaderApp   biblioteca + lector
web/src/mobile/storage.ts        IndexedDB
web/src/mobile/mobile.css        shell Biblioteca
web/vite.mobile.config.ts        build separado
src-tauri/tauri.android.conf.json frontendDist = web/dist-mobile
src-tauri/src/lib.rs             sidecar desactivado con #[cfg(not(mobile))]
```

El build Android no incluye el sidecar: `tauri.android.conf.json` no declara
resources y `lib.rs` omite `sidecar::initialize` en mobile.

## Build

Requisitos:

- JDK 17;
- Android SDK + NDK 27;
- Rust targets Android;
- Tauri CLI.

```bash
npm ci
npm ci --prefix web
uv sync --frozen
npm --prefix web run build:android
npx tauri android init --ci
npx tauri android build --apk --target aarch64 --ci
```

El APK queda en `src-tauri/gen/android/app/build/outputs/apk/`.
El workflow manual `.github/workflows/android.yml` ejecuta este flujo en CI,
alinea el APK con `zipalign`, lo firma con una keystore de prueba generada en el
runner (`vibebook-ci`) y lo verifica con `apksigner`. El artefacto `android-apk`
incluye el APK firmado y `checksums-android.txt`.

## Estado validado

Build `aarch64` de v0.4.1 en GitHub Actions:

- APK firmado: **11,23 MB**, 679 entradas.
- Incluye `AndroidManifest.xml`, `classes.dex`,
  `lib/arm64-v8a/libvibebook_desktop_lib.so` y `assets/tauri.conf.json`.
- `apksigner verify` pasa con firma v1+v2+v3; el checksum del artefacto
  coincide con el digest de GitHub.
- `checksums-android.txt` usa el nombre del APK, sin el prefijo `artifacts/`.
- Queda pendiente la prueba en dispositivo y el cierre de SAF/SQLite/audio.

## Rendimiento

- Objetivo APK: ≤ 50 MB.
- Arranque: ≤ 3 s en gama media.
- Page-turn: 60 fps; sin WebGL.
- Epub.js se carga solo en el lector.
- No hay sidecar ni ffmpeg.

## Limitaciones actuales

- IndexedDB en vez de SQLite/SAF; la importación usa el file picker del WebView.
- No hay sincronización con desktop ni export de biblioteca.
- No hay audio local todavía; el lector es texto/EPUB.
- No hay Play Store: el APK de CI se firma con una keystore efímera de prueba.
  Para actualizar sobre una instalación previa hay que desinstalar o usar una
  keystore estable.
- El CI valida build, firma y contenido del APK, pero no se probó en un
  dispositivo físico en este entorno.
- Si el rendimiento de Tauri mobile no alcanza, el plan permite evaluar
  Kotlin/Compose nativo con benchmark.

## Criterio para cerrar P4

1. APK arm64 ≤ 50 MB.
2. Importar EPUB → leer → cambiar página → cerrar → reabrir → misma posición.
3. 60 fps en un dispositivo de gama media.
4. Sin sidecar vivo y sin permisos innecesarios.
5. Captura de pantalla del lector y del estante en el Release.
