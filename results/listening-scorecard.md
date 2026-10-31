# Scorecard de escucha

Mismo texto de referencia: `samples/excerpt.txt` (~3.500 caracteres). Las
previews LatAm se generan con `scripts/bakeoff_latam.py` (~800 caracteres).
Puntúa de 1 a 5. La decisión es subjetiva; lo importante es si escucharías un
capítulo entero con esa voz.

## Voces LatAm (Edge)

| Motor | Voz | Locale | Naturalidad | Emoción | Pronunciación | Ritmo/pausas | ¿30 min? | Notas |
|---|---|---|---:|---:|---:|---:|---|---|
| Edge TTS | `es-MX-JorgeNeural` | `es-MX` | | | | | | Default actual |
| Edge TTS | `es-MX-DaliaNeural` | `es-MX` | | | | | | |
| Edge TTS | `es-PY-MarioNeural` | `es-PY` | | | | | | |
| Edge TTS | `es-PY-TaniaNeural` | `es-PY` | | | | | | |

## Estilos Azure (`es-MX-JorgeNeural`)

Solo si existen `AZURE_SPEECH_KEY` y `AZURE_SPEECH_REGION`. Comparar contra la
versión Edge de la misma voz.

| Motor | Voz | Estilo | Naturalidad | Emoción | Pronunciación | Ritmo/pausas | ¿30 min? | Notas |
|---|---|---|---:|---:|---:|---:|---|---|
| Azure | `es-MX-JorgeNeural` | `neutral` | | | | | | |
| Azure | `es-MX-JorgeNeural` | `chat` | | | | | | |
| Azure | `es-MX-JorgeNeural` | `cheerful` | | | | | | |
| Azure | `es-MX-JorgeNeural` | `sad` | | | | | | |
| Azure | `es-MX-JorgeNeural` | `excited` | | | | | | |
| Azure | `es-MX-JorgeNeural` | `whispering` | | | | | | |

## Archivos Edge

- `out/bakeoff_latam/es-MX-JorgeNeural.mp3`
- `out/bakeoff_latam/es-MX-DaliaNeural.mp3`
- `out/bakeoff_latam/es-PY-MarioNeural.mp3`
- `out/bakeoff_latam/es-PY-TaniaNeural.mp3`

## Archivos Azure (opcionales)

- `out/bakeoff_latam/azure_es-MX-Jorge_neutral.mp3`
- `out/bakeoff_latam/azure_es-MX-Jorge_cheerful.mp3`
- `out/bakeoff_latam/azure_es-MX-Jorge_sad.mp3`
- `out/bakeoff_latam/azure_es-MX-Jorge_excited.mp3`
- `out/bakeoff_latam/azure_es-MX-Jorge_whispering.mp3`

## Histórico (descartado)

Estas muestras pertenecen al bake-off inicial con acento de España y Kokoro.
No compiten con las voces LatAm: Kokoro quedó descartado por lentitud en CPU y
por no dividir texto en español.

| Motor | Voz | Naturalidad | Emoción | Pronunciación | Ritmo/pausas | ¿30 min? | Notas |
|---|---|---:|---:|---:|---:|---|---|
| Edge TTS | `es-ES-AlvaroNeural` | | | | | | Histórico |
| Edge TTS | `es-ES-ElviraNeural` | | | | | | Histórico |
| Edge TTS | `es-ES-XimenaNeural` | | | | | | Histórico |
| Kokoro | `em_alex` | | | | | | Descartado |
| Chatterbox V3 | por definir | | | | | | Fuera de v0 |

## Criterio

1. Elegir la voz MX o PY con mejor naturalidad y ritmo en 30 minutos.
2. Si gana MX, el default sigue siendo `es-MX-JorgeNeural`.
3. Si gana PY, el default del CLI cambia a `es-PY-MarioNeural` o
   `es-PY-TaniaNeural`.
4. Si hay Azure, elegir estilo solo si mejora la emoción sin artefactos; Edge
   queda para borradores rápidos.
5. Documentar la decisión en este archivo y en `README.md`.
