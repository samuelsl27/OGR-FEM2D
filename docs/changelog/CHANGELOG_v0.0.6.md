# OGR FEM2D v0.0.6 (2026-11-20)

**Una sola rama que vive, `main`.** La propietaria decidió que cada repositorio de la suite tenga
solo `main`. Ningún número del motor cambia: ni `validacion/` ni `rust/` ni `ogr_fem2d/engine/` se
tocan. Sigue fijado `ogr-core` v0.2.2.

## Resultado

- `AGENTS.md`, «Un núcleo y varios programas», tiene una regla nueva debajo de «Un solo `main`»:
  una rama se borra cuando su PR se fusiona, en GitHub y en local. Una rama sin fusionar no se
  borra sin el OK de la propietaria. Si lleva algo que `main` no tiene y hay que conservarlo, antes
  se archiva con una etiqueta `archivo/<nombre>`.
- Se borraron `dev/ogr-core-0.2.2` y `dev/censo-carpetas-ocultas`, en local con `git branch -d`
  (se niega si la rama no está fusionada) y en GitHub con `git push origin --delete`.
- `dev/regla-ramas`, la rama de esta versión, es la primera que sigue la regla: se borra al
  fusionar su PR.
- `pyproject.toml` y `ogr_fem2d.__version__` pasan a `0.0.6`.

## Lo que se encontró

Medido el 2026-11-20, antes de borrar nada:

| Rama | Punta (local = GitHub) | Commits que `main` no tiene | PR |
|---|---|---|---|
| `dev/ogr-core-0.2.2` | `5bd33c0` | 0 | #1, fusionado en `86c88e3` |
| `dev/censo-carpetas-ocultas` | `7de973a` | 0 | #2, fusionado en `a4965b7` |

- `git branch -a --no-merged main` no devolvía nada. No había etiquetas ni otros worktrees, así que
  no hubo nada que archivar. Cada PR conserva su historia y el botón de restaurar la rama.
- El ajuste «Automatically delete head branches» del repositorio estaba **desactivado**
  (`delete_branch_on_merge: false`). Ese ajuste lo decide la propietaria y aquí no se cambió.

## Pruebas

Windows, Python del `.venv`.

| Corrida | Resultado |
|---|---|
| Suite entera, contra la etiqueta instalada (`shared: ogr_core 0.2.2 … (installed, no git tree)`) **205 de 205**, código 0 |

### Sin probar

- La corrida con `--dev-core`: no cambia nada que dependa del núcleo. La corre la CI de OGR-Core
  sobre este `main`.
