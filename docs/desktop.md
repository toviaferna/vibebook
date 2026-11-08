# App de escritorio

Vibebook Desktop es un shell Tauri que envuelve la misma API y la misma interfaz
web del Studio. El backend Python corre como sidecar local, con ffmpeg incluido
en el ejecutable, y la ventana carga la SPA empaquetada.

## Requisitos

- Windows 10/11 x64.
- WebView2. Windows 11 lo incluye; en Windows 10 el instalador de Tauri puede
  descargarlo o usar el bootstrapper incluido.
- Internet para Edge TTS. Azure es opcional.
- Piper y eSpeak NG son opcionales y funcionan offline; ver
  [engines.md](engines.md).
- Los plugins VEP pueden ser locales por HTTP o remotos por HTTPS; el token se
  guarda en `secrets.json`.
- Para compilar: Rust, Visual Studio Build Tools con el workload C++, Node 22,
  `uv` y `npm`.

## Uso

En un release, descargá una de estas opciones:

- Instalador NSIS (`Vibebook_<versión>_x64-setup.exe`).
- Instalador MSI (`Vibebook_<versión>_x64_en-US.msi`).
- ZIP portable (`Vibebook-<versión>-windows-x64.zip`).

El ZIP portable no requiere instalación. Descomprimilo y ejecutá `Vibebook.exe`.
Si querés que la biblioteca quede dentro de la carpeta portable, creá un archivo
vacío llamado `portable.flag` al lado del ejecutable. En ese modo los datos van a
`data/library`; si no existe el flag, se usa la carpeta de datos del usuario.

La biblioteca y el audio nunca salen de la máquina. El sidecar escucha solo en
`127.0.0.1` y exige un token efímero que genera el shell al arrancar.

## Desarrollo

Desde la raíz del repositorio:

```powershell
npm ci
npm ci --prefix web
uv sync
make sidecar
npm run desktop:dev
```

`make sidecar` construye `web/dist` y `dist/vibebook-sidecar.exe`. Tauri lo copia
como recurso y lo lanza al abrir la ventana. En desarrollo, Vite corre en
`http://127.0.0.1:5173` y el sidecar se inicia con `--dev` para permitir CORS de
ese origen.

Si querés incluir Azure con word boundaries en el binario, instalá el extra antes
de empaquetar:

```powershell
uv sync --extra azure-sdk
make sidecar
```

Para incluir Piper en el sidecar, dejá el binario y la voz en
`packaging/piper/bin` y `packaging/piper/voices` antes de `make sidecar`:

```powershell
uv run vibebook piper download --dest packaging/piper/voices
make sidecar
```

El spec de PyInstaller copia esas carpetas si existen. Sin ellas, la app sigue
funcionando y Piper aparece como no instalado.

eSpeak NG se puede incluir de la misma forma en `packaging/espeak/bin`; el spec
también copia esa carpeta si existe. Sin Piper ni eSpeak, la app pide elegir un
motor legado explícitamente.

Comandos útiles:

```powershell
npm run desktop:check
npm run desktop:build
cargo fmt --manifest-path src-tauri/Cargo.toml
cargo check --manifest-path src-tauri/Cargo.toml
```

`npm run desktop:build` genera NSIS y MSI en
`src-tauri/target/release/bundle/`. El ejecutable queda en
`src-tauri/target/release/`.

## Ciclo de vida

1. La app genera un token de 32 bytes y elige un puerto libre (`--port 0`).
2. Lanza `vibebook-sidecar serve --json-ready --token ...`.
3. Lee la línea JSON `{"event":"ready","port":...,"token":"..."}`.
4. Expone `api_config` a la SPA con `baseUrl` y `token`.
5. La SPA usa ese `baseUrl` para las llamadas y agrega el token a las URLs de
   audio, portadas y M4B, que no pueden enviar headers personalizados.
6. Al cerrar la ventana, mata el árbol de procesos del sidecar.

Si el sidecar no arranca, la ventana muestra un diagnóstico con el mensaje y la
ruta del log.

## Logs y diagnóstico

- Sidecar: `%LOCALAPPDATA%\com.vibebook.desktop\logs\vibebook-sidecar.log`.
- WebView2: `%LOCALAPPDATA%\com.vibebook.desktop\EBWebView\`.
- En desarrollo, el firewall de Windows puede pedir permiso para Node/Vite. Es
  solo para el servidor de desarrollo local.

## Limitaciones conocidas

- Solo Windows x64 por ahora.
- Edge TTS es un servicio no oficial y puede limitar peticiones.
- Piper y eSpeak NG requieren binario; el release actual no los incluye todavía.
- Azure no entrega word boundaries por REST; esos capítulos usan resaltado por
  segmento.
- No hay auto-update ni firma de código todavía. Windows SmartScreen puede
  mostrar una advertencia con binarios sin firmar.
- La licencia del proyecto y la revisión de licencias de terceros siguen
  pendientes antes del release público. Ver
  [`packaging/THIRD_PARTY_NOTICES.md`](../packaging/THIRD_PARTY_NOTICES.md).

## Release

El workflow `.github/workflows/release-desktop.yml` compila en Windows al pushear
un tag `v*` o manualmente con `workflow_dispatch`. Genera:

- ZIP portable.
- Instalador NSIS.
- Instalador MSI.
- `checksums.txt` con SHA-256.

Los artefactos se adjuntan al GitHub Release cuando el disparador es un tag.
