# audiol

Lector de libros a audiolibro con voz natural. Proyecto en fase de bake-off.

## Decisión actual

No construir el pipeline desde cero. La estrategia aprobada es:

- **Baseline:** Audiblez + Kokoro en CPU (sin GPU).
- **Bake-off:** comparar el mismo capítulo en español con Kokoro, Chatterbox y Edge TTS.
- **A construir:** solo el cleaner, el director de emoción y la capa de producto.
- **Fuera de v0:** PDF, SFX, base de datos, servidor, UI grande y app multidispositivo.

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
- `samples/excerpt.epub` — EPUB del extracto para el bake-off rápido.

## Resultados

| Motor | Voz | Caracteres | Audio | Muro | Factor tiempo real | Tamaño |
|---|---|---:|---:|---:|---:|---:|
| Edge TTS | `es-ES-AlvaroNeural` | 3.580 | 214,0 s | 36,8 s | 5,82x | 1,28 MB |
| Edge TTS | `es-ES-ElviraNeural` | 3.580 | 211,4 s | 34,4 s | 6,14x | 1,27 MB |
| Edge TTS | `es-ES-XimenaNeural` | 3.580 | 220,2 s | 31,6 s | 6,98x | 1,32 MB |
| Kokoro (Audiblez) | `em_alex` | — | — | — | — | — |
| Chatterbox V3 | — | — | — | — | — | — |

Archivos para escuchar:

- `out/edge_es_alvaro_preview.mp3` / `out/edge_es_alvaro.mp3`
- `out/edge_es_elvira_preview.mp3` / `out/edge_es_elvira.mp3`
- `out/edge_es_ximena_preview.mp3` / `out/edge_es_ximena.mp3`
- `out/edge_es_*.srt`

Métrica reproducible:

```bash
PATH="$PWD/.tools/bin:$PATH" python3 scripts/measure.py \
  out/edge_es_alvaro.mp3 samples/excerpt.txt \
  --engine edge-tts --voice es-ES-AlvaroNeural --wall-seconds 36.8
```

## Entorno

- WSL2 Ubuntu 22.04, 4 núcleos, 5,8 GB RAM.
- `ffmpeg`/`ffprobe` estáticos en `.tools/bin`.
- `espeak-ng` extraído sin root en `.tools/espeak-root` y envuelto en `.tools/bin/espeak-ng`.
- El wrapper fuerza `PULSE_SERVER=unix:/tmp/no-pulse` para que espeak-ng no se cuelgue esperando el servidor de audio de WSL.
- Python 3.10 en `~/.venvs/audiol` (ext4, rápido); Edge TTS en `.venv-edge`.
- El venv del proyecto no se guarda en `/mnt/c` porque pip se bloquea escribiendo miles de archivos en el filesystem de Windows.

## Bake-off

| Test | Motor | Comando base | Estado |
|---|---|---|---|
| A | Kokoro (Audiblez) | `audiblez samples/excerpt.epub -v em_alex` | Pendiente |
| B | Chatterbox V3 | `epub2tts-chatterbox` en Colab/Kaggle | Pendiente |
| C | Edge TTS | `edge-tts -f samples/excerpt.txt -v es-ES-AlvaroNeural` | Hecho |

Criterio de aceptación: el capítulo se escucha completo, sin frases perdidas ni clics, y la calidad es al menos 3/5. Si Kokoro pasa, no se añade GPU.

## Estado

- [x] Entorno inspeccionado.
- [x] EPUB de dominio público descargado.
- [x] Extracto y EPUB de prueba generados.
- [x] Edge TTS generado y medido (dos voces).
- [ ] Audiblez instalado y probado.
- [ ] Muestra Kokoro generada y medida.
- [ ] Muestra Chatterbox generada y medida.
- [ ] Motor por defecto elegido.
