# Reglas del repo

## Releases y aprobación

- **Prohibido** crear tags, versiones, releases o publicar paquetes definitivos
  sin que el usuario haya probado los cambios y haya dado aprobación explícita.
- El flujo obligatorio es: analizar → implementar → probar → revisar → generar
  un instalador de prueba si corresponde → esperar la prueba del usuario →
  recibir aprobación → recién entonces tag/versionar/publicar.
- Que el proyecto compile o que los tests pasen no autoriza una publicación.
- No volver a publicar todos los paquetes sin una revisión previa de los
  problemas reportados.
- Esta regla tiene prioridad sobre cualquier otra instrucción del repo.

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
