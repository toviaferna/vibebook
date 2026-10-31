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
El capítulo de prueba es el **Tratado Primero** (~25k caracteres).

```bash
./scripts/fetch_sample.sh
python3 scripts/prepare_sample.py
```

Genera:

- `samples/tratado_primero.txt` — texto limpio del capítulo.
- `samples/tratado_primero.epub` — EPUB de un solo capítulo para el bake-off.

## Bake-off

| Test | Motor | Comando base | Qué mide |
|---|---|---|---|
| A | Kokoro (Audiblez) | `audiblez samples/tratado_primero.epub -v em_alex` | Calidad base, tiempo CPU |
| B | Chatterbox V3 | `epub2tts-chatterbox` en Colab/Kaggle | Emoción, naturalidad, GPU |
| C | Edge TTS | `edge-tts` con voz española | Velocidad, calidad gratis |

Criterio de aceptación: el capítulo se escucha completo, sin frases perdidas ni clics, y la calidad es al menos 3/5. Si Kokoro pasa, no se añade GPU.

## Estado

- [x] Entorno inspeccionado (WSL2, 4 núcleos, 5.8 GB RAM, 31 GB libres).
- [x] EPUB de dominio público descargado.
- [ ] Audiblez instalado y probado.
- [ ] Muestra Kokoro generada y medida.
- [ ] Muestra Edge TTS generada y medida.
- [ ] Muestra Chatterbox generada y medida.
- [ ] Motor por defecto elegido.
