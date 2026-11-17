# ADR-0002 — Riverpod para estado e inyección de dependencias

- **Estado:** Propuesto.
- **Fecha:** 2026-11-17.

## Contexto

La app tiene consultas async (biblioteca, jobs, lector, providers), estado
efímero de UI, servicios nativos y necesidad de tests con fakes. La app actual
usa TanStack Query + React context implícito; Flutter necesita una solución
equivalente.

## Decisión

Usar **Riverpod 3.5 + riverpod_generator 4.0** para estado y DI. No se usa
`get_it`, `injectable` ni un service locator paralelo.

## Alternativas

- **Bloc 9.1:** explícito y testeable, pero más boilerplate para consultas
  async y DI separada.
- **Provider:** simple, pero sin caching async/auto-dispose ni DI robusta.
- **get_it + ChangeNotifier:** service locator global; difícil de testear.

## Consecuencias

- `ProviderScope` + overrides en tests.
- `AsyncNotifier` para listas/consultas; `Notifier` para UI; streams para jobs.
- `riverpod_lint` y `custom_lint` en CI.
- Curva de aprendizaje; se documenta en `docs/refactor/03-architecture.md`.

## Criterios de revisión

- Tests de ViewModels sin widgets.
- Sin estado global mutable fuera de providers.
- No se mezcla con Bloc/get_it.
