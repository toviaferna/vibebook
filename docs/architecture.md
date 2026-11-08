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
| Rápido y gratis | Edge TTS | `es-MX-JorgeNeural`, `es-MX-DaliaNeural`, `es-PY-MarioNeural`, `es-PY-TaniaNeural` | Rate y pitch | 0 |
| Emoción gratis | Azure TTS F0 | `es-MX-JorgeNeural`, `es-MX-DaliaNeural` | SSML: `chat`, `cheerful`, `excited`, `sad`, `whispering` | 0,5 M caracteres/mes |
| Emoción fuerte | Chatterbox `es-mx-latam` | clonación y exageración | GPU | Futuro |
| Descartado | Kokoro | - | - | No se usa |

La voz por defecto es `es-MX-JorgeNeural` con Edge. El rate por defecto es
`-10%`.

### Registro de motores

`tts/spec.py` declara cada motor con capacidades explícitas: tipo
(`builtin`/`plugin`), transporte (`local`/`http`/`command`), red, clave,
estilos, calidad de timing, tamaño máximo, formato, licencia y fuente.
`tts/registry.py` centraliza el catálogo, la disponibilidad y la creación de
proveedores; `factory.py` mantiene la firma histórica.

`GET /api/engines` expone el catálogo. Un motor puede estar en el catálogo y no
estar implementado todavía: en ese caso `implemented` y `available` son
`false`, y la conversión falla con un error claro en lugar de intentar usarlo.
Edge y Azure se conservan como legado externo; el catálogo ya reserva Piper y
eSpeak NG para el camino local.

## Pipeline

```text
EPUB
  -> ingest (estructura + texto)
  -> clean
  -> chunk
  -> synthesize (motor resuelto por el registro)
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
- `assemble.py`: concatena, normaliza a -19 LUFS y crea el M4B AAC.

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
