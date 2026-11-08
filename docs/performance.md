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
