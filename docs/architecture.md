# vibebook — Diseño del MVP

> El paquete Python se llama `audiol`; el comando instalado es `vibebook`
> (alias `audiol`).

## Objetivo

Convertir un EPUB en un audiolibro en español latinoamericano, con voz natural y capítulos, usando la menor infraestructura posible: sin GPU, sin servidor y sin base de datos.

## Alcance de v0

- Entrada: EPUB sin DRM.
- Salida: Markdown limpio, audio por capítulo y un `.m4b` con capítulos y AAC.
- Voces: Edge TTS para MX/PY; Azure TTS para estilos de emoción en `es-MX`.
- CLI local, reanudable y con caché por segmento.
- Sin PDF, sin SFX, sin UI web, sin sincronización multidispositivo y sin clonación de voz.

## Decisiones de voz

| Modo | Motor | Voces | Emoción | Coste |
|---|---|---|---|---|
| Rápido / gratis | Edge TTS | `es-MX-JorgeNeural`, `es-MX-DaliaNeural`, `es-PY-MarioNeural`, `es-PY-TaniaNeural` | Limitada (rate/pitch) | $0 |
| Emoción gratis | Azure TTS F0 | `es-MX-JorgeNeural`, `es-MX-DaliaNeural` | SSML: `chat`, `cheerful`, `excited`, `sad`, `whispering` | 0,5 M chars/mes |
| Emoción fuerte (futuro) | Chatterbox `es-mx-latam` | clonación / exageración | GPU | Gratis en Colab/Kaggle |
| Descartado | Kokoro | — | — | — |

**Default:** `es-MX-JorgeNeural` con Edge. El usuario puede cambiar a `es-PY-MarioNeural`, `es-PY-TaniaNeural` o `es-MX-DaliaNeural` con `--voice`.

**Estilos:** solo `es-MX` los tiene en Azure. `es-PY` se usa con Edge y queda sin estilos; si se quiere emoción con acento paraguayo, la ruta futura es Chatterbox `es-mx-latam` o Gemini.

## Arquitectura

```text
EPUB
  → ingest (ebooklib + BeautifulSoup)
  → clean (reglas de texto)
  → chunk (frases/párrafos ≤400 chars)
  → synthesize (EdgeProvider | AzureProvider | FakeProvider)
  → assemble (ffmpeg: concat, loudnorm, AAC M4B con capítulos)
  → book.m4b + manifest.json + book.md
```

### Principios

- **CLI primero, archivos como estado.** No hay base de datos ni servidor.
- **Un proveedor es un adaptador, no el producto.** Edge y Azure comparten el mismo contrato.
- **Caché por contenido.** La clave es `sha256(texto + voz + motor + estilo)`; si el archivo existe, se reutiliza.
- **Rutas absolutas en ffmpeg.** Evita el bug de Audiblez que duplicaba el prefijo de la carpeta.
- **Audio final AAC.** Evita M4B PCM de 384 kbps.
- **Sin Kokoro en el camino principal.** Queda como referencia histórica, no como dependencia.

## Contratos de datos

```python
Book(title, author, language, chapters)
Chapter(index, title, segments)
Segment(id, chapter_index, paragraph_index, text, style, voice)
AudioResult(path, word_boundaries)
```

### Estructura de salida

```text
out/<libro>/
  book.md
  manifest.json
  audio/
    segments/<segment_id>_<hash>.mp3
    chapters/chapter_001.mp3
  <libro>.m4b
```

## Manejo de errores y reanudación

- Edge/Azure: 3 intentos con backoff exponencial ante errores de red o 429/5xx.
- 401 de Azure: error claro con instrucción de configurar `AZURE_SPEECH_KEY` y `AZURE_SPEECH_REGION`.
- Si un segmento ya existe y no está vacío, se omite.
- `--force` regenera todo.
- Un fallo deja los segmentos ya generados; al reejecutar se reanuda.

## Pruebas

- Unitarias: catálogo de voces, EPUB, cleaner, chunker, SSML, manifiesto.
- Integración: proveedor falso → M4B; requiere `ffmpeg`/`ffprobe` y se salta si no están.
- Manual: escucha de 30 s por voz (MX/PY) y de estilos Azure (`cheerful`, `sad`, `excited`, `whispering`).
- Criterio de aceptación: el M4B dura lo esperado, tiene capítulos, no pierde frases y suena natural en al menos una voz LatAm.

## Recursos

- Sin GPU. Edge tarda ~1,5–1,7 h por libro de 10 h; Azure es remoto.
- Disco: ~1–2 GB por libro con intermedios; los segmentos se pueden borrar tras el M4B.
- Dependencias: `ebooklib`, `beautifulsoup4`, `lxml`, `edge-tts`, `requests`, `pytest` (dev).
- `ffmpeg`/`ffprobe` externos.

## Riesgos

- Edge TTS es no oficial; sirve para prototipo, no para producto.
- La cuota gratuita de Azure es 0,5 M chars/mes; un libro típico ronda 0,55 M.
- El acento MX/PY es una decisión subjetiva; hay que escucharlo.
- EPUB con DRM no se procesa.
- La calidad de limpieza de PDF queda fuera de v0; PDF es otro proyecto.
