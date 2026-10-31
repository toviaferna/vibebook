# audiol

Generador de audiolibros en español latinoamericano a partir de EPUB.

v0 usa **Edge TTS** por defecto y **Azure Speech** como opción para estilos
emocionales. El idioma por defecto es `es-MX`; también se soporta `es-PY`.
La salida es un M4B AAC con capítulos y metadata.

## Decisión actual

- **Motor por defecto:** Edge TTS, rápido y sin credenciales.
- **Voz por defecto:** `es-MX-JorgeNeural`.
- **Acentos aceptados:** México (`es-MX`) y Paraguay (`es-PY`). La voz final se
  elige por escucha con el bake-off de `scripts/bakeoff_latam.py`.
- **Azure Speech (opcional):** requiere `AZURE_SPEECH_KEY` y
  `AZURE_SPEECH_REGION`. Aporta estilos (`cheerful`, `sad`, `excited`,
  `whispering`, etc.) sobre las voces `es-MX`.
- **Kokoro queda descartado:** era el baseline CPU del bake-off inicial, pero
  no divide texto en español y tarda ~1,2x tiempo real (un libro de 10 h
  tardaría ~8 h). Los scripts de Kokoro quedan solo como referencia histórica;
  el producto no los importa.

Fuera de v0: PDF, SFX, base de datos, UI web, clonación de voz y Chatterbox.

## Requisitos

- Python 3.10 o superior.
- `ffmpeg` y `ffprobe` en `PATH` (obligatorios para concatenar y ensamblar).
- Dependencias de Python: `pip install -e .`.
- Opcional para Azure: credenciales de Azure Speech.

En este repositorio los binarios de ffmpeg viven en `.tools/bin`; cárgalos con:

```bash
source scripts/env.sh
```

## Uso

Listar voces:

```bash
audiol voices
audiol voices --locale es-MX
audiol voices --locale es-PY
```

Convertir un EPUB con Edge (motor y voz por defecto):

```bash
audiol convert samples/excerpt.epub --out out/excerpt
```

Convertir con una voz concreta:

```bash
audiol convert samples/excerpt.epub \
  --voice es-PY-MarioNeural \
  --out out/excerpt-py
```

Simular la conversión sin escribir archivos (cuenta capítulos, segmentos y
caracteres):

```bash
audiol convert samples/excerpt.epub --dry-run --out out/excerpt
```

Elegir motor y estilo (los estilos solo existen en Azure):

```bash
audiol convert samples/excerpt.epub \
  --engine azure \
  --voice es-MX-JorgeNeural \
  --style cheerful \
  --out out/excerpt-azure
```

Opciones de `audiol convert`:

| Opción | Default | Descripción |
|---|---|---|
| `--voice` | `es-MX-JorgeNeural` | Voz del catálogo |
| `--engine` | `edge` | `edge`, `azure` o `fake` (tests) |
| `--style` | `neutral` | Estilo Azure; requiere `--engine azure` |
| `--out` | `out/<nombre-del-epub>` | Carpeta de salida |
| `--max-chars` | `400` | Tamaño máximo de cada segmento |
| `--dry-run` | — | No escribe nada; imprime estadísticas |
| `--force` | — | Re-sintetiza aunque exista el caché |

Salidas por conversión:

- `book.md` — texto limpio y segmentado.
- `manifest.json` — metadata, voz, motor y segmentos.
- `audio/segments/` — audio por segmento (caché reanudable).
- `audio/chapters/` — MP3 por capítulo.
- `<titulo>.m4b` — AAC con capítulos.

Reejecutar sin `--force` reutiliza los segmentos ya sintetizados y solo genera
lo que falte.

## Voces

| Voz | Locale | Género | Motores | Estilos |
|---|---|---|---|---|
| `es-MX-JorgeNeural` | `es-MX` | masculino | Edge, Azure | `chat`, `cheerful`, `excited`, `sad`, `whispering` |
| `es-MX-DaliaNeural` | `es-MX` | femenino | Edge, Azure | `cheerful`, `sad`, `whispering` |
| `es-PY-MarioNeural` | `es-PY` | masculino | Edge | — |
| `es-PY-TaniaNeural` | `es-PY` | femenino | Edge | — |

Estilos Azure (`--engine azure`): `neutral`, `chat`, `cheerful`, `sad`,
`excited`, `whispering`. Edge ignora los estilos y usa la voz neutral.

## Pipeline

1. Leer el EPUB (`read_epub`).
2. Limpiar el texto y dividirlo en segmentos de hasta 400 caracteres
   (`prepare_book`).
3. Sintetizar cada segmento con Edge o Azure, con caché por voz/motor/estilo.
4. Concatenar los segmentos por capítulo y normalizar el volumen.
5. Ensamblar un M4B AAC con metadata y capítulos (`ffmpeg`).

## Tests

```bash
source scripts/env.sh
~/.venvs/audiol/bin/python -m pytest tests/test_cli_convert.py -q -rs
~/.venvs/audiol/bin/python -m pytest -q -rs
```

Los tests de CLI usan `--engine fake` y no tocan la red. Los tests de ensamblado
se saltan si `ffmpeg`/`ffprobe` no están en `PATH`; con `scripts/env.sh` deben
correr, no saltarse.

Smoke test del CLI sin red:

```bash
audiol convert samples/excerpt.epub --engine fake --out out/smoke
```

## Bake-off LatAm

Genera cuatro previews Edge (~800 caracteres) para escuchar MX y PY:

```bash
source scripts/env.sh
~/.venvs/audiol/bin/python scripts/bakeoff_latam.py
ls -lh out/bakeoff_latam/
```

Archivos:

- `out/bakeoff_latam/es-MX-JorgeNeural.mp3`
- `out/bakeoff_latam/es-MX-DaliaNeural.mp3`
- `out/bakeoff_latam/es-PY-MarioNeural.mp3`
- `out/bakeoff_latam/es-PY-TaniaNeural.mp3`

Puntúa las muestras en `results/listening-scorecard.md`. Si gana una voz PY, el
default del CLI cambia a `es-PY-MarioNeural` o `es-PY-TaniaNeural`; si gana MX,
se mantiene `es-MX-JorgeNeural`.

Bake-off opcional de estilos Azure (solo si existen las credenciales):

```bash
source scripts/env.sh
~/.venvs/audiol/bin/python - <<'PY'
from pathlib import Path

from audiol.chunk import chunk_text
from audiol.tts.azure import AzureProvider

chunks = chunk_text(Path("samples/excerpt.txt").read_text(encoding="utf-8"))
parts = []
for chunk in chunks:
    parts.append(chunk)
    if len(" ".join(parts)) >= 800:
        break
text = " ".join(parts)
out = Path("out/bakeoff_latam")
out.mkdir(parents=True, exist_ok=True)
provider = AzureProvider()
for style in ["neutral", "cheerful", "sad", "excited", "whispering"]:
    path = out / f"azure_es-MX-Jorge_{style}.mp3"
    provider.synthesize(text, "es-MX-JorgeNeural", path, style=style)
    print(path)
PY
```

## Muestra

`El Lazarillo de Tormes` (Project Gutenberg #320, dominio público, español).
El capítulo de prueba es el **Tratado Primero**.

```bash
./scripts/fetch_sample.sh
python3 scripts/prepare_sample.py
```

Genera:

- `samples/tratado_primero.txt` — capítulo completo (~25k caracteres).
- `samples/tratado_primero.epub` — EPUB de un solo capítulo.
- `samples/excerpt.txt` — extracto plano de ~3.500 caracteres.
- `samples/excerpt.epub` — EPUB del extracto para pruebas rápidas.

## Historial del bake-off

| Motor | Voz | Caracteres | Audio | Muro | Factor tiempo real | Estado |
|---|---|---:|---:|---:|---:|---|
| Edge TTS | `es-ES-AlvaroNeural` | 3.580 | 214,0 s | 36,8 s | 5,82x | Histórico (España) |
| Edge TTS | `es-ES-ElviraNeural` | 3.580 | 211,4 s | 34,4 s | 6,14x | Histórico (España) |
| Edge TTS | `es-ES-XimenaNeural` | 3.580 | 220,2 s | 31,6 s | 6,98x | Histórico (España) |
| Kokoro | `em_alex` | 3.580 | 203,7 s | 165,4 s | 1,23x | Descartado |
| Chatterbox V3 | — | — | — | — | — | Fuera de v0 |

Hallazgos que motivaron la decisión:

- Edge TTS es 5,8–7x tiempo real; Kokoro en CPU solo 1,23x.
- Kokoro no implementa chunking para idiomas distintos del inglés y truncaba
  párrafos largos.
- Audiblez 0.4.9 tenía el CLI roto y generaba M4B PCM a 384 kbps; este proyecto
  usa ffmpeg directamente y codifica AAC a 64 kbps.
- El concat de ffmpeg exige rutas absolutas; el ensamblador las resuelve.
- La calidad subjetiva se decide escuchando el bake-off MX/PY, no con métricas.

## Entorno de referencia

- WSL2 Ubuntu 22.04.
- `ffmpeg`/`ffprobe` estáticos en `.tools/bin`.
- Python 3.10 en `~/.venvs/audiol` (ext4); el venv no se guarda en `/mnt/c`.
- `source scripts/env.sh` deja ffmpeg y las dependencias de audio en `PATH`.

## Estado

- [x] Ingesta de EPUB, limpieza, chunking y manifiesto.
- [x] Proveedores Edge y Azure, contrato común y proveedor fake para tests.
- [x] Ensamblado de capítulos y M4B AAC con metadata.
- [x] Orquestador reanudable con caché por segmento.
- [x] CLI `audiol voices` y `audiol convert`.
- [x] Bake-off LatAm MX/PY generado.
- [ ] Elección de voz MX/PY por escucha (usuario).
- [ ] Estilos Azure evaluados (requiere credenciales).
