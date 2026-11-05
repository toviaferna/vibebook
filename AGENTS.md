# Reglas del repo

## Ramas y PR

- Nunca commitear ni pushear directamente a `main`.
- Antes de empezar, revisar la rama actual y si ya existe un PR para ella.
- Si estás en `main`, la rama actual fue borrada o mezclada, o no tiene PR
  abierto, crear una rama nueva desde `main`.
- Usar prefijos según el cambio: `feat/`, `fix/`, `docs/`, `chore/` o
  `refactor/`.
- Si la rama actual ya tiene un PR abierto, seguir en ella, pushear y
  actualizar ese PR. No crear otro.
- Pushear siempre la rama y abrir un PR detallado contra `main`.
- El PR debe explicar qué cambia, por qué, archivos afectados, pruebas
  ejecutadas, riesgos y breaking changes.
- No abrir un PR vacío.
