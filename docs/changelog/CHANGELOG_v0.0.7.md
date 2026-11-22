# OGR FEM2D v0.0.7 (2026-11-22)

**Fija `ogr-core` v0.2.3.** Decisión D1 de la spec 003 (la malla): la fijación sube antes de
empezar la spec, en una versión propia. Ningún número del motor cambia: ni `validacion/` ni `rust/`
ni `ogr_fem2d/engine/` se tocan.

## Resultado

- `pyproject.toml` fija `ogr-core @ git+https://github.com/samuelsl27/OGR-Core@v0.2.3` (etiqueta
  anotada → `6f48e53`). La v0.2.3 es compatible y su §2 no pide nada a los programas. El código de
  cálculo del núcleo es el mismo: `git diff v0.2.2 v0.2.3 -- ogr_core` solo toca
  `ogr_core/testing/runner.py` y el número.
- Lo que trae del runner: pone la carpeta de cada archivo de test en la ruta de importación mientras
  ese archivo carga y corre (lo que la v0.0.5 dejó pendiente en el núcleo: 17 tests de aquí importan
  módulos de `tests/`), y su consejo ante «WRONG SHARED TREE» ya no nombra el árbol en editable.
- El `.venv`: `pip install --no-deps --force-reinstall "ogr-core @ git+…@v0.2.3"`; `pip list` da
  `ogr-core 0.2.3`, instalado en `site-packages`.
- `tests/test_project_setup_v001.py`: `_PIN` y las listas de versiones de `TestWhatTheRunIsHeldTo`
  se mueven con la fijación, como dice su comentario.
- La fijación de hoy, en `AGENTS.md`, `README.md` (las dos recetas), `tech-stack.md` y una nota
  fechada en `roadmap.md`. La nota de ADR-0002 del 2026-11-20 cuenta lo que era cierto entonces y no
  se toca; tampoco el docstring de `test_ci_actions_v004.py`, que cita la regla del núcleo en la
  etiqueta en que se leyó.
- `pyproject.toml` y `ogr_fem2d.__version__` pasan a `0.0.7`.

## Lo que se encontró

- **La fila de este programa en `docs/consumidores.md` de OGR-Core** sigue diciendo `v0.2.2`. Se
  corrige allí, en su sesión: hasta entonces, cuando esta versión llegue a GitHub, el trabajo `pins`
  de la CI de OGR-Core sale en rojo. Es el aviso, no un fallo. `suite.toml` (en `OGR_Suite`), igual:
  no se escribe desde aquí.
- **El escrito con que se pidió esta subida** (`Promts_desarrollo/2026_11_20_subir_a_ogr_core_0.2.3.md`)
  tiene reglas que ya no valen desde el 2026-11-22: nombra `C:\Samuel\OGR_Suite`, dice «nunca dos
  corridas a la vez» y «commit solo cuando la propietaria lo diga». Se siguieron las de `AGENTS.md`
  de hoy.
- **Una orden de esta sesión resolvió una ruta relativa en el directorio equivocado**: un `sed` sobre
  `pyproject.toml` apuntó al de OGR-Core, que era el directorio de trabajo en ese momento. La regla
  `deny` de `.claude/settings.local.json` lo bloqueó antes de escribir nada; se repitió con rutas
  absolutas. Las reglas que protegen OGR-Core funcionan con las rutas de este PC.

## Pruebas

Windows, Python del `.venv`.

| Corrida | Resultado |
|---|---|
| Suite entera, contra la etiqueta instalada | `shared: ogr_core 0.2.3  …\OGR-FEM2D\.venv\Lib\site-packages\ogr_core  (installed, no git tree)`; **205 de 205**, código 0, ninguna fuga |
| Suite entera, `PYTHONPATH=../../Core/OGR-Core` y `--dev-core` | `shared: ogr_core 0.2.4.dev0  C:\Desarrollo\OGR_Suite\Core\OGR-Core\ogr_core  @ 0a44098`; **205 de 205**, código 0, ninguna fuga, y `DEV CORE — ogr_core 0.2.4.dev0 runs in place of the pinned 0.2.3 — NOT evidence for a release` antes y después de los totales |

Las dos sobre los cambios de esta versión sin commit todavía (`tree: … @ bac4aa2`). El árbol de
OGR-Core tenía cambios sin commit de su sesión en `AGENTS.md` y en su changelog, ninguno en
`ogr_core/`.

**Dientes** de los tests que se movieron con la fijación, de uno en uno y restaurando el archivo:

| Error metido | Lo caza |
|---|---|
| `_PIN` de vuelta a `0.2.2` | `test_the_versions_are_written_for_the_pin` y `test_the_pin_is_read_from_pyproject` |
| La lista de la corrida normal acepta `0.2.4` en vez de `0.2.3` | `test_an_ordinary_run_takes_the_pin_and_nothing_else` |
