# Benchmarks

Guardar aquí los resultados de rendimiento por fase, con este formato:

```text
# <fecha> — <fase>

## Entorno
- OS:
- CPU/GPU:
- RAM:
- Dispositivo/emulador:
- Build: profile/release
- Versión:

## Resultados
| Métrica | Valor | Presupuesto | Estado |
|---|---:|---:|---|
| Primer frame | | ≤2,0 s desktop / ≤2,5 s mobile | |
| UI interactiva | | ≤2,5 s / ≤3,0 s | |
| Query 100 libros | | ≤50 ms | |
| Scroll 10k libros | | 60 fps | |
| Abrir lector | | ≤1,5 s | |
| Page-turn | | 60 fps | |
| Piper RTF | | ≤2× | |
| Memoria lector | | ≤300 MB | |
| Tamaño instalador | | ≤180 MB | |

## Notas
- Comando usado:
- Comparación con baseline:
- Regresiones/justificación:
```

No inventar valores. Si no se midió, dejar “pendiente”.
