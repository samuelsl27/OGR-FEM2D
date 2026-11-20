# OGR FEM2D v0.0.4 (2026-11-20)

**Fija `ogr-core` v0.2.2, el `.venv` desde la etiqueta, y la suite sale en verde también con
`--dev-core`** (paso 2 de la fase 4 de «un solo OGR-Core»). Ningún número del motor cambia: ni
`validacion/` ni `rust/` se tocan. Pasa por encima de la v0.2.1 del núcleo, que no pedía nada a este
programa; la v0.2.2 le pide lo de su §2.

## Resultado

- `pyproject.toml` fija `ogr-core @ git+https://github.com/samuelsl27/OGR-Core@v0.2.2` (etiqueta
  anotada `fde9cbc` → `96f0305`). El código de cálculo del núcleo es el de la 0.2.0: la 0.2.1 y la
  0.2.2 solo tocan `ogr_core/testing/` y el número.
- **El `.venv` deja de tener el núcleo en editable** desde `C:\Samuel\OGR_Suite\Core\OGR-Core`
  (2026-11-20): `pip install --no-deps --force-reinstall "ogr-core @ git+…@v0.2.2"`. `pip list`
  ya no da la ruta del árbol, en `site-packages` no queda ningún `.pth` del editable, y el runner,
  con la fijación todavía en la 0.2.0, se negó con código 2 nombrando
  `.venv\Lib\site-packages\ogr_core` 0.2.2. Ese árbol ya puede seguir al `main` del núcleo, y los
  dos programas fijar versiones distintas.
- `tests/test_project_setup_v001.py`: la corrida mide el núcleo al que su runner se sujetó (abajo).
- `tests/test_ci_actions_v004.py`, nuevo, y `.github/workflows/wheels.yml` con las acciones a su
  versión vigente (abajo).
- `tests/_runner.py`: la cabecera ya no describe el Python del sistema con Slip2D en editable, y dice
  cómo se corre contra un núcleo sin etiquetar; ninguna opción nueva.
- Documentación: `AGENTS.md` (el núcleo, el entorno, lo que es cierto hoy de Slip2D, y una sección
  nueva, «Un núcleo y varios programas»), `README.md`, `tech-stack.md`, `roadmap.md` (una nota en la
  fila 0b) y una nota fechada en ADR-0002.

## Lo que se encontró

- **Tres tests no podían salir en verde de una corrida con `--dev-core`, por construcción**
  (medido por la sesión de OGR-Core sobre `d2e6fca`: 186 de 189). Comparaban el núcleo importado con
  el fijado, esperaban la versión fijada en la cabecera, y el Python «sin núcleo» heredaba el
  `PYTHONPATH` de la corrida, que en una de desarrollo es justo lo que trae el núcleo: lo encontraba,
  lo aceptaba y devolvía 0. El invariante no cambia, *la corrida mide el núcleo al que el runner se
  sujetó*; lo que cambia es que ahora el test sabe en qué corrida está
  (`ogr_core.testing.runner.dev_core_run()`, desde la 0.2.2).
- **El Python del sistema ya no tiene ningún paquete OGR.** `AGENTS.md` y la cabecera del runner
  decían que tenía OGR Slip2D en editable, con su copia del núcleo o sin ella; no es así hoy.
- **Cuatro de las cinco acciones de la CI declaraban `node20`** en su propio `action.yml`, leído en
  cada etiqueta: `checkout@v4`, `setup-python@v5`, `upload-artifact@v4` y `download-artifact@v4`. La
  CI de la v0.0.3 salió en verde con ellas, y nada en este repositorio lo decía. Versiones vigentes
  el 2026-11-20, en sus repositorios: `checkout` v7.0.1, `setup-python` v7.1.0, `upload-artifact`
  v7.0.2 (`node24` desde la v6), `download-artifact` v8.0.2 (`node24` desde la v7) y
  `PyO3/maturin-action` v1.51.0, que no tiene otra mayor y ya declara `node24`.
  `download-artifact@v8` hace fallar un hash que no coincide (antes era un aviso) y no descomprime
  lo que no es un zip: aquí se descarga por nombre lo que `upload-artifact` subió comprimido.
- **Ningún test de este programa lee los totales de un runner relanzado.** El de la cabecera no
  selecciona nada y el runner vuelve con código 2 antes de imprimir las líneas `DEV CORE`: no había
  nada que adaptar por ese lado.
- **Para OGR-Core, pedido allí y no rodeado aquí**: su mensaje «WRONG SHARED TREE» termina con
  «check out its tag in the editable tree», que ya no es la recomendación. Ningún test de este
  programa depende de esa frase.
- **Un error propio, reportado antes de corregirlo**: los guiones con los que se editaron seis
  archivos (`wheels.yml`, `README.md`, ADR-0002, `roadmap.md`, `tech-stack.md` y
  `test_project_setup_v001.py`) los dejaron con fin de línea CRLF en la copia de trabajo, contra el
  `.gitattributes` (`eol=lf`). Visto con `git ls-files --eol`; el contenido es el mismo. Con el OK
  del propietario se reescribieron en LF y la corrida de publicar se repitió sobre ellos.
- **Otros 35 archivos rastreados tienen CRLF en la copia de trabajo de esta máquina**, de antes de
  esta versión (fechas del 2026-10-27 al 2026-11-02): parte del motor (`ogr_fem2d/engine/`),
  `rust/src/`, once tests, `validacion/casos/003` y `004`, `poc/resultados/` y
  `docs/motor/entrada.md`. En el índice están en LF, así que no salen como cambiados ni llegan al
  repositorio. Se anota y no se toca aquí.

## Los tests

`tests/test_project_setup_v001.py`:

- `test_the_core_is_the_one_the_run_was_held_to` (antes `…_is_the_pinned_distribution`) pasa por
  `_problems(origins, dev)`, que es `shared_problems(origins, pinned(), dev_core=dev)`, con
  `dev = dev_core_run()`. La comprobación de la ruta se queda: el núcleo instalado en `.venv` vive
  dentro de la carpeta del programa, pero no en `<repositorio>/ogr_core`, así que no se toma por
  una copia.
- `test_the_banner_names_both_trees` espera `shared: ogr_core {ogr_core.__version__} `.
- `test_a_python_without_the_core_is_refused` arranca el Python con `-S` **sin el `PYTHONPATH`** de
  la corrida, dos veces, sin `OGR_DEV_CORE` y con `OGR_DEV_CORE=1`: código 2 y la razón en las dos.
- Nuevos: `test_and_given_back_the_core_of_the_run_it_runs` (el control del anterior: el mismo
  Python, con la carpeta del núcleo de la corrida y su variable, corre y da 0), y
  `test_the_child_starts_without_the_run_s_pythonpath`.
- `TestWhatTheRunIsHeldTo`, nueva: `_problems` con núcleos inventados (una carpeta cuyo `ogr_core`
  declara una versión; el runner la lee del código y nunca lo ejecuta), contra la fijación `0.2.2`.
  En una corrida normal pasa `0.2.2` y fallan `0.2.3`, `0.2.3.dev0`, `0.2.2.dev0` y `0.2.1`; en una
  de desarrollo pasan `0.2.3.dev0` y `0.2.2` y fallan `0.2.1`, `0.2.2.dev0` (anterior a la fijada),
  `0.2.3rc1`, `0.2.3+local` y `0.2.3`; un núcleo que no resuelve falla en las dos. Las dos listas
  salieron a la primera como se esperaba del runner de la 0.2.2.

`tests/test_ci_actions_v004.py`: la regla de `tests/test_ci_actions_v10.py` de OGR-Core. Cada
acción en uso tiene un suelo declarado con su motivo, y está en él o por encima: `checkout` y
`setup-python` 7 (el de la suite), `upload-artifact` 6 y `download-artifact` 7 (la primera mayor con
`node24`), `PyO3/maturin-action` 1 (la única). El escáner demuestra que ve antes de juzgar, y el
workflow de la v0.0.3 sale con sus cuatro acciones por debajo.

**Dientes**: diez errores metidos a propósito, de uno en uno, y mueren los diez.

| Error metido | Dónde se corrió | Lo caza |
|---|---|---|
| `_problems` con `dev_core=True` siempre | normal | `test_an_ordinary_run_takes_the_pin_and_nothing_else` |
| `_problems` con `dev_core=False` siempre | normal | `test_a_development_run_takes_a_later_dev_and_the_pin_only` |
| El control sin núcleo | normal | `test_and_given_back_the_core_of_the_run_it_runs` |
| El hijo no quita el `PYTHONPATH` | normal | `test_the_child_starts_without_the_run_s_pythonpath` |
| La cabecera espera la versión fijada | desarrollo | `test_the_banner_names_both_trees` |
| El hijo hereda el `PYTHONPATH` de la corrida | desarrollo | `test_a_python_without_the_core_is_refused` y el anterior |
| El test real no pregunta en qué corrida está | desarrollo | `test_the_core_is_the_one_the_run_was_held_to` |
| `checkout` de vuelta a `@v4` | normal | `test_every_action_meets_its_floor` |
| Una acción sin suelo en el workflow | normal | `test_every_action_in_use_has_a_floor` |
| `maturin-action` fuera de la tabla de suelos | normal | `test_every_action_in_use_has_a_floor` |

«Normal» es contra la etiqueta instalada; «desarrollo», con
`PYTHONPATH=C:\Samuel\OGR_Suite\Core\OGR-Core` (`main` en `b804724`, `0.2.3.dev0`) y `--dev-core`,
solo el archivo de tests. Los tres de desarrollo no pueden morir en una corrida normal, donde el
núcleo importado es el fijado. Un mutante del plan se descartó: que el Python sin núcleo pruebe un
solo caso de la variable en vez de los dos. Con el runner correcto los dos casos dan lo mismo, así
que ningún test lo mata; lo que el doble caso caza es un error del runner, que es del núcleo.

## Pruebas

Windows, Python del `.venv`, de una en una, sobre los cambios de esta versión sin commit todavía
(la línea `tree:` dice `@ d2e6fca`, el commit de partida).

| Corrida | Resultado |
|---|---|
| Suite entera, contra la etiqueta instalada | `shared: ogr_core 0.2.2  …\OGR-FEM2D\.venv\Lib\site-packages\ogr_core  (installed, no git tree)`; **202 de 202** (189 de antes y 13 nuevos), código 0, **ninguna fuga** |
| La misma, repetida con los seis archivos ya en LF | la misma línea `shared:`; **202 de 202**, código 0, **ninguna fuga** |
| Suite entera, `PYTHONPATH=C:\Samuel\OGR_Suite\Core\OGR-Core` y `--dev-core` | `shared: ogr_core 0.2.3.dev0  C:\Samuel\OGR_Suite\Core\OGR-Core\ogr_core  @ b804724`; **202 de 202**, código 0, **ninguna fuga**, y `DEV CORE — ogr_core 0.2.3.dev0 runs in place of the pinned 0.2.2 — NOT evidence for a release` antes y después de los totales. Sobre el árbol con los seis archivos aún en CRLF; no se repitió |

### Sin probar

- La CI con las acciones nuevas: corre con el primer push.
- `docs/consumidores.md` de OGR-Core todavía dice que este programa fija `v0.2.0`: se corrige
  allí, en la sesión de OGR-Core.
