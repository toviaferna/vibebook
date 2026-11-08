# Lector sincronizado

El lector vive en `#/books/<id>/read` y funciona tanto en el navegador como en
la app de escritorio. Carga el manifest, el capítulo y su timing; muestra el
texto limpio del EPUB y sincroniza el audio con el párrafo y la palabra actuales.

## Resaltado

- El segmento activo se resalta siempre.
- La palabra activa se resalta solo si el timing es `exact` y la alineación
  texto↔palabra supera el 80 % de cobertura.
- Si el timing es `estimated`, falta o tiene baja cobertura, se cae a resaltado
  por segmento sin romper el layout.
- Un clic en una palabra o segmento hace seek y reproduce.
- El texto se puede seleccionar; si hay una selección activa, el clic no salta.

## Controles

- Play/pausa, ±15 s, capítulo anterior/siguiente.
- Velocidad (0,75× a 2×), volumen, mute y temporizador.
- Media Session para controles del sistema.
- Autoavance al terminar un capítulo.
- El auto-scroll se pausa 5 s al scrollear manualmente y se reactiva con
  “Volver al texto”.

## Atajos

| Tecla | Acción |
|---|---|
| `Espacio` | Reproducir o pausar |
| `←` / `→` | Retroceder o adelantar 15 s |
| `J` / `K` | Capítulo anterior / siguiente |
| `+` / `-` | Cambiar velocidad |
| `T` | Abrir el índice |
| `F` | Pantalla completa |
| `?` | Mostrar la ayuda |

## Persistencia

Se guardan `position_ms`, `chapter_index` y `playback_rate` en
`PUT /api/books/<id>/state`. El guardado se hace con debounce al pausar o
cambiar de posición y cada 5 s mientras reproduce. Al volver a abrir el libro se
restaura la posición sin autoplay.

## Búsqueda y marcadores

- La búsqueda recorre todos los capítulos y segmentos del manifest. Ignora
  mayúsculas y acentos (`lazaro` encuentra `Lázaro`) y devuelve capítulo,
  segmento, posición y extracto.
- Al elegir un resultado, el lector salta al capítulo y a la posición del audio.
- Los marcadores guardan capítulo, posición y una nota opcional. Se pueden
  abrir o eliminar desde el panel de marcadores.
- Ambos paneles están en la barra superior del lector.

## Ajustes

Tema claro/sepia/noche, tipografía editorial/sans/Atkinson Hyperlegible, tamaño
de texto y seguimiento automático. Los ajustes se comparten con la API de
settings del Studio.

## Limitaciones

- La vista del EPUB original queda para T30.
- El resaltado por palabra depende de los timings generados por el motor TTS.
- Azure sin el extra `azure-sdk` usa REST y no entrega word boundaries; esos
  capítulos usan resaltado por segmento. Instalá `uv sync --extra azure-sdk`
  para obtener timings por palabra.
