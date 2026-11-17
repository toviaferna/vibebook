# Samples

`lector-de-prueba.epub` es un EPUB editorial original de cinco capítulos, con
portada, página de título, índice, diálogos, párrafos largos y una ilustración
interna. Sirve para probar importación, portada, imágenes, paginación, karaoke,
conversión y lector sin depender de un libro externo.

Se regenera con:

```bash
uv run python scripts/make-sample-epub.py
```

Para probarlo:

```bash
uv run vibebook convert samples/lector-de-prueba.epub \
  --engine fake \
  --voice es-MX-JorgeNeural \
  --out .tmp/sample
```

En el Studio, importá el EPUB y elegí el motor `Fake` para una conversión
rápida sin red. La portada y la ilustración se generan en el script para que el
fixture sea reproducible y no dependa de recursos externos.
