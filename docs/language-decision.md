# Decisión de lenguaje y arquitectura

Fecha: 2026-11-10. Estado: **mantener Python + Tauri 2** para 0.6/0.7.

## Contexto

El plan original proponía evaluar una reescritura del backend o un núcleo en
Rust/PyO3 si el rendimiento no alcanzaba. Antes de mover código hay que comparar
el coste real contra los cuellos de botella medidos.

## Evidencia actual

| Dimensión | Valor |
|---|---|
| Cobertura backend | ~87 % (7110 statements) |
| Tests backend | 464 passed, 2 skipped |
| Tests web | 96 |
| E2E | 10 |
| JS inicial | 118,9 KiB gzip |
| CSS inicial | 8,4 KiB gzip |
| Sidecar onefile listo (Windows, v0.3) | ~4,4 s |
| Listado caliente de 100 libros | ~18 ms |
| Memoria del sidecar | ~13 MB |

El cuello de botella percibido está en el arranque del sidecar onefile y en la
síntesis TTS, no en el parseo de EPUB ni en la API. La UI ya está separada en
chunks y el lector no bloquea el hilo principal.

## Decisión

1. **No reescribir el backend ahora.** Python conserva `ebooklib`, `edge-tts`,
   Piper, eSpeak NG, `mutagen` y `ffmpeg`; una reescritura duplicaría el
   mantenimiento y rompería la compatibilidad de manifiestos.
2. **Mantener Tauri 2.** El shell es delgado; migrar a Electron aumentaría el
   peso y la superficie de ataque.
3. **Onedir antes que PyO3.** El spec `vibebook-sidecar-onedir.spec` permite
   medir arranque sin cambiar el lenguaje. Si onedir no alcanza, evaluar PyO3.
4. **Puente Android antes que on-device.** La app Android sigue siendo lector
   EPUB; la conversión on-device es experimental y no bloquea el release.

## Gate para reconsiderar PyO3

Solo se abre una prueba de PyO3 si se cumplen **dos o más** de estas condiciones
en una medición reproducible:

- arranque del sidecar > 5,0 s en un equipo de gama media;
- memoria del sidecar > 200 MB en una biblioteca de 100 libros;
- conversión de un capítulo > 20 % más lenta que el baseline;
- parseo de un EPUB de 50 MB > 2 s en el hilo de API.

La prueba debe incluir un prototipo acotado, benchmark antes/después y un
plan de rollback. No se acepta una reescritura completa sin esas métricas.

## Consecuencias

- Se prioriza onedir, imports perezosos y perfilado.
- Se documenta el estado de Flatpak/Android en `docs/linux.md` y
  `docs/android.md`.
- La decisión se revisa después de la ola 5 (Linux) y de una prueba Android en
  hardware real.
