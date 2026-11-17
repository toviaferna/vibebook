# ADR-0003 — Drift + SQLite como persistencia

- **Estado:** Propuesto.
- **Fecha:** 2026-11-17.

## Contexto

La app necesita biblioteca, jobs, estados de lectura, bookmarks, settings,
assets de ambience y búsqueda. Los datos son relacionales y deben migrarse
desde SQLite actual.

## Decisión

Usar **Drift 2.35** sobre SQLite 3.x, con tablas, DAOs, migraciones versionadas
y FTS5. `sqlite3` 3.x incorpora SQLite; no se usa `sqlite3_flutter_libs` (EOL).

## Alternativas

- **Isar 3.1:** última release 2023, Dart 2; `isar_community` con baja
  adopción.
- **ObjectBox 5.3:** NoSQL, dependencia binaria/comercial; no ideal para joins.
- **Sembast/Hive:** key-value/NoSQL; sin SQL/FTS/migraciones relacionales.
- **sqflite:** sin Windows/Linux.

## Consecuencias

- DB en isolate para queries pesadas.
- Migraciones testeadas con schema exports.
- La biblioteca en disco sigue siendo la fuente de verdad; Drift indexa.
- Se importa `library.db` legacy una vez.

## Criterios de revisión

- Migración legacy idempotente.
- Query de 10k libros <50 ms.
- Tests de migración desde cada versión.
