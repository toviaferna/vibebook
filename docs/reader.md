# Lector sincronizado

El lector vive en `#/books/<id>/read` y funciona tanto en el navegador como en
la app de escritorio. Carga el manifest, el capítulo y su timing; muestra el
texto limpio del EPUB y sincroniza el audio con el párrafo y la palabra actuales.

El índice respeta la estructura real del EPUB: partes, capítulos y títulos
exactos. Si un capítulo se llama “La casa de los relojes”, eso es lo que se
muestra; si el TOC solo trae un número, la UI lo presenta como “Capítulo N”.

## Leer sin audio

Un libro importado se puede abrir en el lector sin convertirlo. El capítulo
llega con `timing: null` y el lector:

- muestra el texto y el índice;
- oculta el reproductor y los marcadores de audio;
- mantiene búsqueda, tipografía y vista Original;
- ofrece un acceso directo para convertir el libro a audiolibro.

Cuando la conversión termina, el mismo libro muestra el player y el karaoke.

## Ilustraciones

Al importar, el manifiesto guarda `images` con:

- `alt` y `caption` del EPUB;
- capítulo y párrafo de anclaje;
- posición (`before`/`after`);
- dimensiones y rol;
- ruta optimizada dentro de la biblioteca.

La imagen se sirve con `GET /api/books/{id}/images/{image_id}`. En **Libro** se
inserta como figura que no se parte entre páginas; en **Texto** aparece entre
los párrafos; en **Original** se conserva la maquetación del EPUB. **Álbum** es
una variante de Libro que da más altura a las figuras para libros ilustrados.

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

## Modo Libro

El toggle **Libro / Texto / Original** agrega una vista paginada:

- doble página en escritorio y una página en mobile;
- paginación medida contra el ancho/alto real y cacheada por capítulo,
  tipografía y tamaño;
- navegación por botones y número de página;
- page-turn CSS 3D con una sola hoja;
- flechas y PageUp/PageDown para pasar página;
- cinta lateral para guardar la página actual;
- marcadores de lectura con nota, listado y salto a capítulo/página;
- `prefers-reduced-motion` desactiva la animación;
- los libros importados abren en Libro por defecto; los que tienen audio abren
  en Texto para conservar el karaoke.

La posición de Libro se guarda en `reading-state` con capítulo, offset de
carácter, página, total y porcentaje, independiente del estado de audio.

## Persistencia

Se guardan `position_ms`, `chapter_index` y `playback_rate` en
`PUT /api/books/<id>/state`. El guardado se hace con debounce al pausar o
cambiar de posición y cada 5 s mientras reproduce. Al volver a abrir el libro se
restaura la posición sin autoplay.

La lectura usa `PUT /api/books/<id>/reading-state` y no pisa la posición del
audio.

## Búsqueda y marcadores

- La búsqueda recorre todos los capítulos y segmentos del manifest. Ignora
  mayúsculas y acentos (`lazaro` encuentra `Lázaro`) y devuelve capítulo,
  segmento, posición y extracto.
- Al elegir un resultado, el lector salta al capítulo y a la posición del audio.
- Los marcadores guardan capítulo, posición y una nota opcional. Se pueden
  abrir o eliminar desde el panel de marcadores.
- Ambos paneles están en la barra superior del lector.

## Vista EPUB original

El toggle **Texto / Original** de la barra superior alterna entre el texto limpio
sincronizado y el EPUB original renderizado con `epubjs` en un iframe aislado.

- El original conserva imágenes y maquetación.
- La sincronización es por capítulo y ancla del índice, no por palabra.
- Los scripts, formularios, iframes, objetos y URLs externas se eliminan antes de
  mostrar el contenido; además se aplica una CSP restrictiva y el iframe queda
  sin `allow-scripts`.
- El karaoke sigue usando la vista limpia.

## Ajustes

Tema claro/sepia/noche, tipografía editorial/sans/Atkinson Hyperlegible, tamaño
de texto y seguimiento automático. Los ajustes se comparten con la API de
settings del Studio.

## Diagnóstico de sincronización

Antes de tocar offsets, medí el libro:

```bash
uv run python scripts/sync_report.py out/libro
uv run python scripts/sync_report.py out/libro --json
uv run python scripts/sync_report.py out/libro --strict --max-drift-ms 100
```

El pipeline arma cada capítulo desde PCM: decodifica los segmentos a mono
24 kHz, mide frames exactos, concatena y codifica una sola vez. El timing usa
los offsets de frames; no se vuelve a escalar el capítulo entero.

El delay del encoder se mide con un impulso sintético, se codifica/decodifica
con los mismos parámetros y se guarda como `timing_offset_ms` en el timing. El
lector resta ese offset al reloj antes de buscar segmento/palabra. En los
encoders medidos hasta ahora el contenido no se desplaza, así que el offset es
0 ms; si una plataforma introduce delay, queda corregida sin offsets mágicos.

Para reparar un libro viejo que ya tiene segmentos pero un timing escalado:

```bash
uv run vibebook repair-sync out/libro
```

El comando reconstruye el audio del capítulo desde `audio/segments`, vuelve a
medir offsets y reescribe `timings/chapter_XXX.json` y el manifiesto. Si un
capítulo no tiene segmentos, lo omite en vez de romper el libro.

El reporte compara:

- duración del timing contra el audio del capítulo;
- suma de segmentos contra el audio concatenado;
- huecos, solapes, palabras inválidas y palabras fuera del segmento;
- silencio inicial/final y delta de audio por segmento.

En desarrollo, abrí el lector con `?sync=1` para ver un overlay con tiempo
actual, segmento, palabra, precisión, FPS de render y velocidad. El overlay no
se muestra en producción ni afecta la reproducción.

El resaltado mantiene la palabra anterior durante huecos de hasta 1 segundo y
la quita en silencios más largos. El tiempo se actualiza con
`requestAnimationFrame` cada ~60 ms, solo si cambió al menos 10 ms; el seek
sincroniza de inmediato y cambiar la velocidad no reescala los timings. El
contenido del lector está memoizado para no re-renderizar el capítulo completo
en cada frame.

## Limitaciones

- La vista original no resalta palabras ni párrafos; solo sincroniza capítulo y
  ancla del índice.
- El resaltado por palabra depende de los timings generados por el motor TTS.
- Azure sin el extra `azure-sdk` usa REST y no entrega word boundaries; esos
  capítulos usan resaltado por segmento. Instalá `uv sync --extra azure-sdk`
  para obtener timings por palabra.
