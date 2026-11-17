# Git sin sorpresas

Este documento describe el flujo que usa el repo. La regla principal es simple:
**no reescribir trabajo compartido**. Un rebase o un `push --force` puede borrar
commits de otra persona aunque Git los muestre como “locales”.

## Antes de tocar una rama

```powershell
git fetch origin --prune
git status --short
git branch --show-current
git worktree list
uv run python scripts/git_preflight.py
```

- Si estás en `main`, creá una rama desde `origin/main`.
- Si la rama ya tiene PR abierto, seguí en ella.
- Si el PR fue mergeado o la rama remota desapareció, creá una rama nueva; no
  reutilices una rama “gone”.
- Un worktree puede tener `main` ocupado. En ese caso no fuerces el checkout:
  creá la rama con `git switch -c <rama> origin/main`.

## Integrar main en una rama compartida

Para una rama que ya está pusheada y tiene PR, usá merge, no rebase:

```powershell
git fetch origin
git merge --no-ff origin/main
# resolver conflictos, revisar el diff y ejecutar tests
git add <archivos resueltos>
git commit
git push
```

No uses `git push --force` ni `--force-with-lease` en una rama con PR abierto.
Si el historial local se desordenó, primero guardá una copia:

```powershell
git branch backup/<rama>-$(Get-Date -Format yyyyMMddHHmm)
```

## Conflictos recurrentes

Los archivos que más conflictos generan son:

- `CHANGELOG.md`: todas las ramas agregan viñetas al inicio. Revisá que no se
  pierda ninguna entrada y que no queden secciones duplicadas.
- Versiones y lockfiles: `pyproject.toml`, `package.json`,
  `web/package.json`, `src-tauri/tauri.conf.json`, `uv.lock`, `Cargo.lock` y
  `package-lock.json`. Se regeneran con las herramientas, no a mano.
- `web/src/styles/*.css` y `web/src/api/types.ts`: varios cambios pueden tocar
  la misma zona. Resolvé por comportamiento, no por “elegir un lado”.
- Archivos generados (`dist/`, `build/`, `out/`, `portable/`, `src-tauri/target/`):
  nunca se commitean. Si aparecen, están fuera de `.gitignore` por error.

Después de resolver:

```powershell
git diff --check
git diff --stat
uv run python scripts/git_preflight.py
```

## Reglas de seguridad

- No uses `git reset --hard` ni `git clean -fdx` sin inspeccionar primero
  `git status` y `git stash list`. Pueden borrar EPUBs, portadas o cambios sin
  commit.
- No resuelvas un conflicto copiando un archivo entero sin leer el diff.
- No mergees sin ejecutar al menos los tests del área afectada.
- No crees tags, releases ni instaladores definitivos sin aprobación explícita
  del usuario (ver `AGENTS.md`).
- Habilitá `rerere` localmente si resolvés los mismos conflictos seguido:
  `git config rerere.enabled true`.

## Texto y finales de línea

`.gitattributes` fija `eol=lf` para el código y `crlf` solo para scripts de
Windows. `.editorconfig` mantiene UTF-8 y espacios. Si Git avisa que convertirá
LF a CRLF en un archivo de código, revisá que `.gitattributes` esté presente
antes de commitear; no normalices archivos completos en un PR ajeno.
