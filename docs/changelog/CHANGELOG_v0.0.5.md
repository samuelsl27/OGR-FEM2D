# OGR FEM2D v0.0.5 (2026-11-20)

**El censo de las cabeceras de licencia entra en las carpetas ocultas que llevan código.** Ningún
número del motor cambia: ni `validacion/` ni `rust/` ni `ogr_fem2d/engine/` se tocan. Sigue fijado
`ogr-core` v0.2.2.

## Resultado

- `tests/test_project_setup_v001.py`, `TestLicenceHeaders`: dos listas declaradas. La primera,
  `_HIDDEN_WITH_CODE = (".github",)`, son las carpetas ocultas con código del programa, y el censo
  las recorre. La segunda, `_HIDDEN_NOT_OURS`, son las que no son del programa, cada una con su
  porqué: `.git`, `.venv` y `.claude`. Tres tests nuevos (abajo).
- `pyproject.toml` y `ogr_fem2d.__version__` pasan a `0.0.5`.

## Lo que se encontró

- **El censo no miraba `.github/scripts/wheel_check.py`.** Buscaba con
  `glob.glob("**/*.py", recursive=True)`, que no entra en las carpetas cuyo nombre empieza por
  punto. El archivo lleva su cabecera SPDX y su copyright, pero ningún test lo habría detectado si
  la perdiera (regla 4). Lo avisó la sesión de OGR-Core, que encontró el mismo patrón en su
  repositorio y lo arregló en su PR 7. Aquí se arregla con el mismo criterio: no se usa
  `include_hidden=True`, que entraría en el `.venv`, ni `git ls-files`, que no ve un archivo hasta
  que se añade.
- Las carpetas ocultas de la raíz el 2026-11-20 son `.claude` (sin `.py`), `.git` (sin `.py`),
  `.github` (1 `.py`) y `.venv` (4645 `.py`).
- **Visto y no cambiado**: 17 tests importan módulos de `tests/` (`_blocks`, `_hole`,
  `test_validation_cases_v002`…). Eso solo funciona si `tests/` está en la ruta de importación. El
  único test que vuelve a lanzar el runner lo hace con `python -S tests/_runner.py`, que la pone
  la primera. El `runpy` de `test_benchmark_v001.py` lanza `poc/benchmark.py`, que no importa
  tests. Que el runner compartido lo garantice está pendiente en el núcleo, hacia la 0.2.3.
- Si la lista de carpetas ocultas acaba en el núcleo (está en «Cambios en curso» de
  `docs/consumidores.md` de OGR-Core), la de aquí se retira cuando se suba la fijación.

## Los tests

- `test_every_hidden_folder_with_python_is_declared`: falla si una carpeta oculta con algún `.py`
  no está en ninguna de las dos listas. La busca con `os.walk`, no con `glob`.
- `test_the_hidden_folder_scan_sees_what_glob_does_not`: es el control del anterior. En una carpeta
  temporal con `.tools/deep/x.py`, una `.empty` sin nada y un `.git/hook.py`, `glob` no ve nada y el
  escáner devuelve `[".tools"]`.
- `test_the_census_sees_the_hidden_code`: el censo incluye `.github/scripts/wheel_check.py`.

**Dientes**: tres errores metidos a propósito, de uno en uno, y los tres se detectan.

| Error metido | Lo caza |
|---|---|
| `wheel_check.py` sin la línea SPDX | `test_every_source_file_has_the_spdx_line_near_the_top` |
| Una carpeta `.tools/` nueva con un `.py` | `test_every_hidden_folder_with_python_is_declared` |
| `_HIDDEN_WITH_CODE` vacía, es decir, el censo de antes | el anterior y `test_the_census_sees_the_hidden_code` |

## Pruebas

Windows, Python del `.venv`.

| Corrida | Resultado |
|---|---|
| Suite entera, contra la etiqueta instalada `shared: ogr_core 0.2.2  …\OGR-FEM2D\.venv\Lib\site-packages\ogr_core  (installed, no git tree)`; **205 de 205** (202 de antes y 3 nuevos), código 0 |

### Sin probar

- La corrida con `--dev-core`: ningún test nuevo depende del núcleo. La corre la CI de OGR-Core
  sobre este `main`.
