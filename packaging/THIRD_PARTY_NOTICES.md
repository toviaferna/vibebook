# Third-party notices

Vibebook se distribuye bajo GNU Affero General Public License v3.0 only
(`AGPL-3.0-only`). Ver `LICENSE`.

Vibebook usa y empaqueta componentes de terceros. Esta lista es un inventario
inicial, no asesoramiento legal. Antes de publicar binarios hay que revisar las
licencias exactas de cada versión distribuida y cumplir sus obligaciones,
especialmente las de los componentes copyleft.

## Componentes principales

| Componente | Licencia | Uso |
|---|---|---|
| Tauri | MIT / Apache-2.0 | Shell de escritorio |
| Serde | MIT / Apache-2.0 | Serialización en Rust |
| getrandom | MIT / Apache-2.0 | Token local del sidecar |
| tauri-plugin-single-instance | MIT / Apache-2.0 | Instancia única |
| Epub.js | BSD-2-Clause | Vista EPUB original |
| @xmldom/xmldom | MIT | Parser XML de Epub.js |
| FastAPI | MIT | API local |
| Uvicorn | BSD-3-Clause | Servidor ASGI |
| Pydantic | MIT | Modelos de la API |
| EbookLib | AGPL-3.0 | Lectura de EPUB |
| Beautiful Soup | MIT | Limpieza de HTML |
| lxml | BSD-3-Clause | Parser XML/HTML |
| Piper | GPL-3.0-or-later | Motor TTS local, proceso separado |
| eSpeak NG | GPL-3.0-or-later | Fallback TTS local, proceso separado |
| Voz Piper `es_MX-ald-medium` | Unlicense (dataset Aldo); modelo Piper | Voz local por defecto |
| edge-tts | LGPL-3.0 | Motor TTS legado |
| Mutagen | GPL-2.0-or-later | Metadata de audio |
| platformdirs | MIT | Rutas de datos del usuario |
| requests | Apache-2.0 | Cliente HTTP |
| python-multipart | Apache-2.0 | Subida de archivos |
| static-ffmpeg | MIT | Descarga de ffmpeg/ffprobe |
| PyInstaller | GPL-2.0-or-later con excepción | Empaquetado del sidecar |
| FFmpeg / ffprobe | Depende del build (LGPL/GPL) | Ensamblado y medición de audio |
| Fraunces, Public Sans, Source Serif 4, IBM Plex Mono, Atkinson Hyperlegible | SIL Open Font License 1.1 | Tipografías de la UI |

## Notas

- **EbookLib (AGPL-3.0)** y **Mutagen (GPL-2.0-or-later)** son copyleft. La
  distribución de binarios puede exigir ofrecer el código fuente correspondiente
  y cumplir las condiciones de cada licencia.
- **Piper y eSpeak NG (GPL-3.0-or-later)** se ejecutan como procesos separados.
  Si se distribuyen sus binarios, hay que ofrecer el código fuente
  correspondiente y conservar sus avisos. La voz `es_MX-ald-medium` se descarga
  desde `rhasspy/piper-voices`; su dataset usa Unlicense.
- **edge-tts (LGPL-3.0)** se usa como dependencia; revisar si el binario
  empaquetado requiere permitir el reemplazo de la biblioteca.
- **Plugins VEP** son servidores externos que el usuario agrega por URL; no se
  empaquetan en el binario. Cada plugin declara su licencia y fuente.
- **FFmpeg** se incluye como ejecutable separado. La licencia depende del build
  descargado por `static-ffmpeg`; los builds con códecs GPL requieren cumplir la
  GPL. Verificar el build exacto antes de distribuir.
- **PyInstaller** permite empaquetar programas propietarios gracias a su
  excepción; el bootloader sigue bajo GPL con esa excepción.
- Las tipografías se distribuyen bajo SIL OFL 1.1. No se modificaron.

## Fuentes

- https://github.com/tauri-apps/tauri
- https://github.com/OHF-Voice/piper1-gpl
- https://github.com/espeak-ng/espeak-ng
- https://huggingface.co/rhasspy/piper-voices
- https://github.com/rany2/edge-tts
- https://github.com/aerkalov/ebooklib
- https://github.com/quodlibet/mutagen
- https://ffmpeg.org/legal.html
- https://pyinstaller.org/en/stable/license.html
- https://github.com/static-ffmpeg/static-ffmpeg
- https://fonts.google.com/
