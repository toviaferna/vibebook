# Samples

`lector-de-prueba.epub` es un EPUB original de tres capítulos cortos, pensado
para probar importación, conversión y lector sin depender de un libro externo.

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
rápida sin red.
