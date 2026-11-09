# App de escritorio por plataforma

Vibebook empaqueta la SPA, el sidecar Python y ffmpeg/Piper en una app Tauri.
La conversión es local; no hay cuenta ni servicio pago.

## Matriz

| Plataforma | Arquitectura | App | Sidecar | Conversión | Estado |
|---|---|---|---|---|---|
| Windows 10/11 | x64 | Tauri | Sí | Sí | Actual |
| Linux | x64 | Tauri | Sí | Sí | P1 |
| macOS | arm64 / x64 | Tauri | Sí | Sí | P2, unsigned |
| Android | arm64 | Tauri mobile | No | No | P4, lector |

## Windows

- Instaladores NSIS/MSI y ZIP portable.
- Sin firma: SmartScreen puede advertir. “Más información → Ejecutar de todas
  formas”.
- WebView2 viene con Windows 11; en Windows 10 puede requerir el runtime.
- Datos en `%LOCALAPPDATA%\Vibebook`; el ZIP portable usa `portable.flag` y
  guarda la biblioteca junto al ejecutable.
- El ZIP incluye `LEEME.md`, `THIRD_PARTY_NOTICES.md` y `sidecar/`.

## Linux

Requisitos:

- Ubuntu 22.04/24.04 o Debian 12;
- WebKitGTK 4.1 y GTK3;
- `ffmpeg`/`ffprobe` (el sidecar también puede usar su copia empaquetada);
- FUSE 2 para ejecutar AppImage.

```bash
sudo apt-get install libwebkit2gtk-4.1-dev libayatana-appindicator3-dev \
  librsvg2-dev patchelf libfuse2
```

Build:

```bash
npm ci
npm ci --prefix web
uv sync --frozen
npm --prefix web run build
uv run pyinstaller packaging/pyinstaller/vibebook-sidecar.spec --noconfirm
npm run desktop:build -- --bundles appimage,deb
```

Salidas en `src-tauri/target/release/bundle/appimage` y `bundle/deb`.
Datos en `~/.local/share/vibebook` (o `data/library` si hay `portable.flag`).
Sin firma; verificar checksums.

## macOS

- arm64 (macOS 14+) y x64, `.dmg` sin firma/notarización.
- Gatekeeper bloquea el primer doble clic. Documentar:

```bash
xattr -dr com.apple.quarantine /Applications/Vibebook.app
```

o clic derecho → Abrir. No prometer una experiencia “doble clic” perfecta.
- Datos en `~/Library/Application Support/com.vibebook.desktop`.
- Sidecar y ffmpeg dentro del `.app`; Piper opcional.
- Build:

```bash
brew install ffmpeg
npm ci && npm ci --prefix web
uv sync --frozen
npm --prefix web run build
uv run pyinstaller packaging/pyinstaller/vibebook-sidecar.spec --noconfirm
npm run desktop:build -- --target aarch64-apple-darwin --bundles dmg
```

Para x64 usar un runner x64 y `--target x86_64-apple-darwin`.

## Android

P4 es lector-only: importa EPUB, guarda posición y reproduce audio existente. No
incluye Python, ffmpeg ni conversión. Ver `docs/android.md`.

## Sidecar y logs

El shell arranca `vibebook-sidecar serve --json-ready` con token y puerto libre.
En Windows el log queda en `%LOCALAPPDATA%\Vibebook\logs\vibebook-sidecar.log`;
en Linux/macOS en el directorio de logs de la app. Si el motor local no inicia,
la UI muestra el error y la ruta del log.

## Release

Los tags `v*` disparan `.github/workflows/release.yml`. El workflow construye
Windows, Linux, macOS arm64/x64 y publica un único Release con checksums. No se
publica si un job falla.
