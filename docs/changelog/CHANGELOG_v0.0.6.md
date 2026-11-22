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
| Suite entera, contra la etiqueta instalada (`shared: ogr_core 0.2.2 … (installed, no git tree)`) | **205 de 205**, código 0 |

### Sin probar

- La corrida con `--dev-core`: no cambia nada que dependa del núcleo. La corre la CI de OGR-Core
  sobre este `main`.

## Después de la versión: la sección «Desarrollo» del `README.md` (2026-11-21)

Solo documentación: ni la versión ni una línea de código cambian. Sale de escribir la guía para
montar la suite en un PC nuevo (`DESARROLLO.md`, en la carpeta de trabajo `OGR_Suite`) y de
ensayarla.

- `README.md`, «Desarrollo»: dice qué hace falta antes de la receta (Python 3.11 o posterior, git,
  Rust estable y, en Windows, las Build Tools de Visual Studio con C++), da la misma receta en
  PowerShell además de en Git Bash, dice que el programa no se instala en su entorno, cómo se
  instala PyInstaller para el congelado (`pyinstaller==6.22.3`, la versión de la CI) y dónde está
  la guía de la suite entera.

### Lo que se encontró

- **La receta del README funciona en un clon nuevo.** Ensayo del 2026-11-21 en una carpeta
  temporal: clon de GitHub (`487b4f5`), `.venv` nuevo de Python 3.14.7, las cuatro órdenes
  tecleadas en PowerShell. maturin compila el motor en 45 s y deja `ogr_fem2d/_engine.pyd` en el
  árbol.
- **maturin 1.16.0 no necesita `VIRTUAL_ENV`** cuando se lanza con el Python del entorno
  (`.venv/Scripts/python -m maturin develop …`): sin la variable hace lo mismo. La receta la
  conserva, porque no estorba y otras versiones de maturin la piden.
- **El congelado no estaba en el README**: PyInstaller solo se nombraba en la spec 001 y en la CI.

### Pruebas

Windows, clon nuevo, `.venv` nuevo de Python 3.14.7, dependencias de hoy (numpy 2.5.5, scipy
1.18.1, maturin 1.16.0).

| Corrida | Resultado |
|---|---|
| Suite entera, entorno montado por el script de la suite | **205 de 205**, código 0 |
| Suite entera, entorno montado tecleando la receta del README en PowerShell | **205 de 205**, código 0 |
| `poc/freeze/build.py` | `ALL 4 CASES PASS`, `FROZEN PROGRAM OK`, código 0 |

En las dos, `shared: ogr_core 0.2.2 … (installed, no git tree)`.

### Sin probar

- La receta en Linux y macOS (`.venv/bin/python`): la cubre la CI, con la rueda.
- Instalar Rust y las Build Tools desde cero: el ensayo se hizo en un PC que ya las tenía.
