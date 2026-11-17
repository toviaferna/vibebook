# ADR-0007 — Biblioteca en disco como fuente de verdad

- **Estado:** Propuesto; pendiente G5.
- **Fecha:** 2026-11-17.

## Contexto

La app actual guarda cada libro en `<library>/<slug>-<sha8>/` con
`manifest.json`, audio, timings, portada, EPUB y M4B. SQLite es un índice. Los
usuarios ya tienen bibliotecas y no se pueden perder.

## Decisión

Conservar el **layout y el manifiesto** como fuente de verdad. Drift indexa y
guarda estado/jobs/bookmarks/settings. La app Flutter lee/escribe el mismo
formato y migra la DB legacy una vez, con backup.

## Alternativas

- Nuevo formato + migración irreversible: riesgo alto; descartado.
- Empezar de cero: pierde biblioteca; descartado.
- DB como fuente de verdad: rompe portabilidad y recuperación manual.

## Consecuencias

- `LibraryRepository` escanea manifiestos y reconcilia con Drift.
- Escrituras atómicas (tmp + rename).
- Migración importa `library.db` y estados; no mueve libros.
- Rollback a Tauri posible durante la beta.
- Tests con biblioteca real anonimizada.

## Criterios de revisión

- Migración idempotente y reversible.
- Sin pérdida de títulos, audio, timings, bookmarks ni posiciones.
- `.books/` intacto si algo falla.
