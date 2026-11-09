# Rendimiento

Vibebook prioriza bajo consumo de recursos. Los presupuestos se miden antes y
después de cada cambio; un PR que los empeora debe justificarlo.

## Baseline v0.3.0 (Windows 11)

| Métrica | Valor |
|---|---|
| Sidecar onefile listo para health | ~4,4 s |
| Primer listado de 100 libros | ~550 ms |
| Listado de 100 libros en caliente | ~18 ms |
| Working set del sidecar | ~13 MB |
| JS inicial | ~472 KB raw |
| CSS inicial | ~46 KB raw |
| Instaladores NSIS/MSI | ~99 MB |
| ZIP portable | ~103 MB |

## Presupuestos actuales

- JS inicial: ≤ 550 KiB gzip.
- CSS inicial: ≤ 60 KiB gzip.
- Sidecar listo: ≤ 5,0 s.
- UI interactiva: ≤ 3,0 s.
- Listar 100 libros en caliente: ≤ 100 ms.
- Abrir lector: ≤ 1,5 s.
- Paginar un capítulo: ≤ 50 ms.
- Page-turn: 60 fps.
- Memoria del lector: ≤ 200 MB.
- Piper en CPU: ≥ 2× tiempo real.
- APK Android lector: ≤ 50 MB.

## N6 — arranque y lector (2026-11-09)

| Métrica | Antes | Después |
|---|---:|---:|
| JS inicial | 155,6 KiB gzip | **118,0 KiB gzip** |
| CSS inicial | 11,5 KiB gzip | **8,4 KiB gzip** |
| Chunk del lector | — | 17,4 KiB JS + 4,2 KiB CSS lazy |
| Chunk de epubjs | 104,8 KiB gzip | 104,8 KiB gzip, solo al abrir EPUB original |

- Las rutas de lector, estudio, detalle, importación y ajustes se cargan con
  `React.lazy` y `Suspense`; la biblioteca sigue siendo el chunk inicial.
- `reader.css` se carga con el chunk del lector, no con el arranque.
- `useBook` y el plan de re-segmentación tienen `staleTime` para evitar
  peticiones repetidas al volver a una pantalla.
- La API del lector cachea el manifiesto por ruta + mtime + tamaño (máx. 8) y
  evita parsear el JSON completo en cada cambio de capítulo.
- Índices SQLite para `created_at`, `title COLLATE NOCASE` y `duration_ms`.
- La paginación del lector ya estaba cacheada por capítulo, medidas y
  tipografía; no se recalcula al pasar páginas.

## Verificación local

```bash
cd web
npm run build
npm run check:bundle
```

El script lee `dist/index.html`, suma el JS/CSS inicial comprimido con gzip y
falla si supera el presupuesto. No cuenta chunks lazy que no se cargan en el
primer render.

## Reglas

- Animaciones solo con `transform`/`opacity`.
- Sin WebGL/Three.js para el libro.
- Rutas y dependencias pesadas en lazy chunks.
- No cargar modelos TTS al arrancar.
- Medir con `scripts/measure.py` para audio y con las DevTools para el lector.
- No agregar una dependencia pesada sin comparar contra una alternativa nativa.
