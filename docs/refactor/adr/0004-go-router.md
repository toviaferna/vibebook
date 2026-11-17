# ADR-0004 — go_router para navegación

- **Estado:** Propuesto.
- **Fecha:** 2026-11-17.

## Contexto

La app tiene rutas anidadas (biblioteca, detalle, estudio, lector, ajustes),
shells distintos para desktop/mobile, deep links y necesidad de typed routes.

## Decisión

Usar **go_router 18.1 + go_router_builder 4.5** con `StatefulShellRoute` para
los shells y rutas tipadas generadas.

## Alternativas

- **auto_route 11.2:** potente, pero menos oficial y otro generador.
- **Navigator 1/2 directo:** más control, más errores y duplicación.

## Consecuencias

- Rutas declarativas y deep links.
- Shells desktop/mobile.
- Guards de onboarding/libro inexistente.
- Tests de navegación con `MemoryRouter`/fakes.

## Criterios de revisión

- Deep link a lector funciona en Android/iOS/desktop.
- Back/forward del navegador en Web.
- Sin rutas hardcodeadas en widgets.
