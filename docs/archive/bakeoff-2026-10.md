# Bake-off de voces, octubre de 2026

Primera ronda de pruebas para elegir motor y acento. Conserva los datos que
llevaron a Edge TTS como base y a Kokoro como descartado. No es una evaluación
vigente: el scorecard actual está en
[`results/listening-scorecard.md`](../../results/listening-scorecard.md).

## Muestra

- Texto: `samples/excerpt.txt`, 3.580 caracteres y 659 palabras.
- Medición: `scripts/measure.py`.
- Audio: mono, 24 kHz.

## Edge TTS, acento de España

| Voz | Audio | Muro | Factor tiempo real | Salida |
|---|---:|---:|---:|---|
| `es-ES-AlvaroNeural` | 214,0 s | 36,8 s | 5,82x | MP3 48 kbps, 1.284.048 bytes |
| `es-ES-ElviraNeural` | 211,4 s | 34,4 s | 6,14x | MP3 48 kbps |
| `es-ES-XimenaNeural` | 220,2 s | 31,5 s | 6,98x | MP3 48 kbps |

Comprobaciones:

- Pico de Alvaro: -3,19 dB; RMS: -21,46 dB.
- Sin silencios mayores de 1,5 s.
- El SRT de Alvaro tiene 659 palabras, así que no se perdió texto.
- Niveles dentro del rango habitual de audiolibro.

Estas voces se descartaron por el acento, no por calidad técnica. La evaluación
siguió con las voces LatAm.

## Kokoro

| Voz | Audio | Muro | Factor tiempo real | Salida |
|---|---:|---:|---:|---|
| `em_alex` | 203,7 s | 165,4 s | 1,23x | WAV 24 kHz, 9.776.444 bytes |

Comprobaciones:

- Pico: -4,88 dB; RMS: -26,33 dB; loudness integrada: -26,2 LUFS.
- Sin silencios mayores de 1,5 s.
- El MP3 normalizado sube +4,9 dB para comparar con Edge al mismo volumen.

Kokoro no divide texto en idiomas distintos del inglés. Con un párrafo largo
truncaba la salida: el primer intento produjo 84 s en vez de 204 s. El script
`scripts/kokoro_direct.py` lo partía en trozos de 400 caracteres, pero se
eliminó al migrar a `uv`.

El tiempo era viable en CPU, unas 8 h para un libro de 10 h. Se descartó porque
la voz no convenció en la escucha y porque el chunking en español dependía de
código propio.

## Decisión

- Edge TTS como motor por defecto, con voces `es-MX` y `es-PY`.
- Rate por defecto `-6%`.
- Azure Speech como opción para estilos en `es-MX`.
- Kokoro fuera del proyecto.
- Las voces de España quedan solo como referencia histórica.

## Datos

- [`edge_es_alvaro.json`](edge_es_alvaro.json)
- [`edge_es_elvira.json`](edge_es_elvira.json)
- [`edge_es_ximena.json`](edge_es_ximena.json)
- [`edge_technical.md`](edge_technical.md)
- [`kokoro_es_alex.json`](kokoro_es_alex.json)
- [`kokoro_technical.md`](kokoro_technical.md)
