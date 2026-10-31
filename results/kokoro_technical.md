# Kokoro: comprobaciones técnicas

Muestra: `samples/excerpt.txt` (3.580 caracteres, 659 palabras).
Voz: `em_alex` (español, masculina).

- Audio: 203,7 s, WAV 24 kHz mono.
- Muro: 165,4 s (incluye arranque y carga del modelo); generación interna: 153,6 s.
- Factor tiempo real: 1,23x.
- Pico: -4,88 dB; RMS: -26,33 dB; loudness integrada: -26,2 LUFS.
- Sin silencios mayores de 1,5 s.
- El MP3 normalizado sube +4,9 dB para comparar con Edge al mismo volumen percibido.

## Nota importante

Kokoro no implementa chunking para idiomas distintos del inglés. Si se le pasa un párrafo largo, lo trunca. El primer intento produjo 84 s en vez de 204 s. `scripts/kokoro_direct.py` divide el texto en trozos de ≤400 caracteres y soluciona el problema.

## Lectura

El tiempo es viable: un libro de 10 h tardaría ~8 h en este CPU. La decisión depende de la escucha, no de estas métricas.
