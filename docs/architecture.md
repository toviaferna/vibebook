# Arquitectura de vibebook

## Objetivo

Convertir un EPUB en un audiolibro en español latinoamericano con voz natural,
capítulos y un M4B AAC. El diseño prioriza bajo consumo de recursos. El Studio
usa un servidor local y SQLite solo para la biblioteca; la app de escritorio
empaqueta ese backend como sidecar.

El paquete Python se llama `audiol`; el comando instalado es `vibebook`, con
alias `audiol`.

## Alcance de v0

- Entrada: EPUB sin DRM.
- Salida: Markdown limpio, audio por capítulo y M4B con capítulos.
- Voces: Edge TTS para MX/PY; Azure TTS para estilos en `es-MX`.
- CLI local, reanudable y con caché por segmento.
- Fuera de v0: PDF, SFX, sincronización multidispositivo y clonación de voz.

## Voces

| Modo | Motor | Voces | Emoción | Coste |
|---|---|---|---|---|
| Local sin cuenta | Piper | `es_MX-ald-medium` | Rate | 0 |
| Fallback local | eSpeak NG | `es-419` | Rate | 0 |
| Rápido y gratis | Edge TTS | `es-MX-JorgeNeural`, `es-MX-DaliaNeural`, `es-PY-MarioNeural`, `es-PY-TaniaNeural` | Rate y pitch | 0 |
| Emoción gratis | Azure TTS F0 | `es-MX-JorgeNeural`, `es-MX-DaliaNeural` | SSML: `chat`, `cheerful`, `excited`, `sad`, `whispering` | 0,5 M caracteres/mes |
| Emoción fuerte | Chatterbox `es-mx-latam` | clonación y exageración | GPU | Futuro |
| Descartado | Kokoro | - | - | No se usa |

El motor por defecto se resuelve local-first: Piper si hay binario y voz, luego
eSpeak NG, y Edge solo como legado explícito. Los libros existentes conservan su
motor. El rate por defecto es `-10%`.

### Registro de motores

`tts/spec.py` declara cada motor con capacidades explícitas: tipo
(`builtin`/`plugin`), transporte (`local`/`http`/`command`), red, clave,
estilos, calidad de timing, tamaño máximo, formato, licencia y fuente.
`tts/registry.py` centraliza el catálogo, la disponibilidad y la creación de
proveedores; `factory.py` mantiene la firma histórica.

`GET /api/engines` expone el catálogo. Un motor puede estar en el catálogo y no
estar implementado todavía: en ese caso `implemented` y `available` son
`false`, y la conversión falla con un error claro en lugar de intentar usarlo.
Edge y Azure se conservan como legado externo; Piper y eSpeak NG corren local.
Los plugins VEP se registran en `plugins.json`, sus tokens viven en
`secrets.json` y sus voces se integran al catálogo y al Studio.

Piper se ejecuta como proceso separado con `subprocess.run`, sin `shell=True` y
con timeout. La voz se descarga explícitamente, se verifica por tamaño y MD5 y
se resuelve desde `VIBEBOOK_PIPER_VOICES`, el directorio de datos o un bundle.
eSpeak NG usa el mismo aislamiento y `--path` para encontrar sus datos. En
Windows, las rutas no ASCII se convierten a rutas cortas 8.3 antes de invocar
los binarios. Los plugins VEP hablan HTTP/JSON, se validan por manifiesto,
timeout y audio, y nunca exponen su token. Detalle en
[engines.md](engines.md).

## Temas y apariencia

La identidad visual es **Verdín**: papel frío, verde, latón y tipografía
editorial. Hay dos luces separadas:

- `theme_mode` (`system | light | dark`) controla toda la app. Se aplica como
  `data-theme` en `<html>`, escucha `prefers-color-scheme` cuando está en
  `system` y se persiste en settings + `localStorage`.
- `reader_palette` (`paper | sepia | night`) controla solo la página del lector.
  Se aplica como `data-reader-palette` en `.reader-shell`; no cambia el resto de
  la app.

`web/index.html` aplica el tema guardado antes del primer paint para evitar el
flash. El ajuste viejo `reader_theme` se acepta como alias y se migra a
`reader_palette` (`light → paper`). Los clientes viejos siguen recibiendo
`reader_theme` en la respuesta.

Las fuentes de producción son Spectral (display), Literata (lectura), Public
Sans (UI), IBM Plex Mono (metadatos) y Atkinson Hyperlegible (opción de
accesibilidad), servidas con Fontsource. El ruido de pantalla completa y los
blur decorativos se eliminaron para cuidar el rendimiento.

## Ambientación

`ambience/` separa biblioteca, plan, análisis y (más adelante) mezcla:

- `library.py`: importa audio, calcula SHA-256, exige licencia, guarda JSON y
  actualiza el índice SQLite `sound_assets`;
- `procedural.py`: genera camas loopables de 30 s con ffmpeg (`rain`, `wind`,
  `sea`, `room`, `fire`, `night`);
- `plan.py`: valida y persiste `ambience/plan.json`, actualiza el manifiesto y
  respeta 1 cama + 3 efectos por capítulo, separación de 8 s y guardas de 2 s;
- `analyzer.py`: heurístico español offline; no inventa segment IDs.

Los assets importados quedan sin aprobar hasta que el usuario los escucha. El
flujo base no requiere red, cuenta ni API paga.

## Pipeline

```text
EPUB
  -> ingest (estructura + texto)
  -> clean
  -> chunk
  -> synthesize (motor resuelto por el registro; Piper/eSpeak local o nube)
  -> assemble (ffmpeg)
  -> book.m4b + manifest.json + book.md
```

### Estructura del libro

`ingest/structure.py` resuelve la estructura antes de extraer párrafos:

- lee el TOC como árbol, sin aplanar partes ni subcapítulos;
- usa títulos exactos, sin prefijar “Capítulo”;
- si no hay TOC, divide por headings dominantes;
- separa partes, prólogos y apéndices con `epub:type` y heurísticas;
- guarda `level`, `kind`, `number` y un `toc` jerárquico opcional en el
  manifiesto.

Los libros viejos conservan su manifiesto; el reanálisis es explícito para no
romper audio ni timings existentes.

### Etapas

- `ingest/epub.py`: lee el spine, usa los anclajes del índice para dividir
  documentos que agrupan varios capítulos, ignora documentos de navegación y
  avisa si un documento no tiene texto.
- `ingest/images.py`: extrae ilustraciones, las valida/optimiza con Pillow, las
  deduplica y las ancla a un capítulo/párrafo.
- `clean.py`: elimina números de página, encabezados de Gutenberg, marcas de
  agua, líneas duplicadas y corrige guiones.
- `chunk.py`: agrupa frases hasta 400 caracteres; parte las frases largas.
- `tts/`: adaptadores con el contrato `TTSProvider` y `AudioResult`.
- `convert.py`: prepara el libro, cachea segmentos, reintenta fallos
  transitorios y arma capítulos.
- `assemble.py`: decodifica cada segmento a PCM mono 24 kHz, concatena por
  frames, registra offsets exactos, codifica el capítulo una sola vez a MP3 con
  loudnorm y crea el M4B AAC. El timing se construye desde esos offsets, sin
  escalar dos veces las palabras.
- Lector: el tiempo se actualiza con RAF, el seek sincroniza al instante y el
  resaltado conserva la palabra anterior en huecos cortos; `ReaderContent` está
  memoizado para evitar renders completos por frame. El timing guarda
  `timing_offset_ms` para el delay medido del encoder y el lector lo aplica.
- `repair.py`: reconstruye audio/timing de libros viejos desde
  `audio/segments`; omite capítulos sin segmentos y actualiza el manifiesto de
  forma atómica.

## Contratos

```python
Book(title, author, language, chapters)
Chapter(index, title, segments)
Segment(id, chapter_index, paragraph_index, text)
AudioResult(path)
```

La voz, el motor, el estilo y el rate viven en la configuración de la
conversión y en el manifiesto, no en cada segmento.

## Caché y reanudación

La clave es `sha256(texto + voz + motor + estilo + rate)`. El audio se escribe
en un archivo temporal y se publica con `os.replace` solo cuando termina. Un
fallo elimina el temporal; la siguiente ejecución reanuda. Si cambian los IDs
de los segmentos pero el texto es el mismo, el caché se reutiliza por clave.

Edge espera 1 segundo entre peticiones y reintenta hasta 5 veces con backoff
exponencial desde 2 segundos.

## Ensamblado

- Los segmentos se concatenan por capítulo con ffmpeg y `loudnorm`.
- El M4B usa AAC a 64 kbps, metadata y capítulos.
- Las rutas del concat son absolutas.
- `find_binary()` resuelve ffmpeg/ffprobe desde `FFMPEG_BINARY` /
  `FFPROBE_BINARY`, `VIBEBOOK_FFMPEG_DIR`, recursos del ejecutable congelado,
  PATH, `.tools/bin` o `static-ffmpeg`.

## Escritorio

La app Tauri es un shell nativo que carga la misma SPA y arranca el backend
Python como sidecar:

```text
Vibebook.exe
  -> genera token y puerto libre
  -> vibebook-sidecar serve --json-ready
  -> lee {"event":"ready","port":...,"token":...}
  -> api_config(baseUrl, token) a la SPA
  -> mata el árbol del sidecar al cerrar
```

El sidecar escucha solo en `127.0.0.1`, valida `X-Vibebook-Token` o `?token=`
para recursos que no pueden enviar headers (audio, portadas, M4B) y sirve la SPA
empaquetada. El ZIP portable usa `portable.flag` para guardar la biblioteca en
`data/library` junto al ejecutable. Ver [desktop.md](desktop.md).

## CLI y entorno

- `uv` gestiona Python 3.12 y las dependencias.
- `uv run vibebook ...` no requiere activar un venv.
- `vibebook voices` lista el catálogo.
- `vibebook convert` acepta EPUB, voz, motor, estilo, rate y salida.
- `vibebook --version` lee la versión del paquete instalado.

## Pruebas

- Tests unitarios para EPUB, limpieza, chunking, voces, SSML y manifiesto.
- Tests de integración con `FakeProvider` y ffmpeg para concat y M4B.
- El proveedor falso escribe WAV; Edge y Azure se prueban con dobles.
- `uv run pytest` cubre la suite; `make check` añade ruff y mypy.

## Riesgos

- Edge TTS es no oficial y puede limitar peticiones.
- La cuota gratuita de Azure es 0,5 M caracteres/mes.
- El acento MX/PY es una decisión de escucha.
- EPUB con DRM no se procesa.
- PDF queda fuera de v0.
