# Scorecard de escucha

Mismo texto: `samples/excerpt.txt` (3.580 caracteres, ~3,5 minutos).
Puntúa de 1 a 5. La decisión es subjetiva; lo importante es si escucharías un capítulo entero.

| Motor | Voz | Naturalidad | Emoción | Pronunciación | Ritmo/pausas | ¿30 min? | Notas |
|---|---|---:|---:|---:|---:|---|---|
| Edge TTS | `es-ES-AlvaroNeural` | | | | | | |
| Edge TTS | `es-ES-ElviraNeural` | | | | | | |
| Edge TTS | `es-ES-XimenaNeural` | | | | | | |
| Kokoro | `em_alex` | | | | | | |
| Chatterbox V3 | por definir | | | | | | |

## Archivos

- `out/edge_es_alvaro_preview.mp3` (30 s)
- `out/edge_es_elvira_preview.mp3` (30 s)
- `out/edge_es_ximena_preview.mp3` (30 s)
- `out/edge_es_alvaro.mp3` (completo)
- `out/edge_es_elvira.mp3` (completo)
- `out/edge_es_ximena.mp3` (completo)

## Criterio

Si Kokoro obtiene al menos 3/5 en naturalidad y la respuesta a “¿30 min?” es sí, se queda como baseline CPU. Si no, se prueba Chatterbox en GPU y se compara.
