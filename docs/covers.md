# Portadas

Cada libro importado tiene portada.

## Orden de resolución

1. Si el EPUB declara una portada (`ITEM_COVER` o una imagen con `cover` en el
   nombre), se extrae y se guarda como `cover.<ext>`.
2. Si no hay arte, se genera un `cover.svg` determinista con el título, el autor,
   una paleta derivada de un hash y un motivo editorial. No usa servicios ni
   fuentes externas.
3. Desde el detalle del libro, **Buscar portada** consulta Open Library y Google
   Books con título y autor.

## Búsqueda

- Open Library: `https://openlibrary.org/search.json` y
  `https://covers.openlibrary.org/b/id/<id>-L.jpg`.
- Google Books: `https://www.googleapis.com/books/v1/volumes`.
- Una coincidencia debe superar una similitud de título de 0.82 (normalizando
  acentos y puntuación); el autor suma, pero no alcanza por sí solo.
- Las miniaturas se piden a través del backend (`/cover/search/preview`) para
  respetar la CSP y no exponer el WebView a hosts arbitrarios.
- Al aplicar, solo se descargan hosts permitidos, se valida la imagen con Pillow
  y se normaliza a JPEG de hasta 1600 px. Se reemplaza la portada anterior y se
  actualiza el manifiesto.

## Privacidad

La búsqueda es opcional y requiere red. La generación local y la lectura no
dependen de Internet. No se envían el EPUB ni el texto del libro.
