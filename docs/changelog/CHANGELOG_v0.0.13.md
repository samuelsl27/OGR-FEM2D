# OGR FEM2D v0.0.13

**Fase 1, sexta parte: operaciones y transporte** (spec 006, parte B). El catálogo de operaciones de
este programa, sin Qt, sobre el armazón del núcleo (`ogr_core.api`, ADR-0005); el cálculo como trabajo
en subproceso; la línea de órdenes y el servidor MCP. Este archivo cuenta lo que fue entrando, tarea a
tarea.

## T10 — la fijación sube a OGR-Core v0.2.9 (2026-11-24)

En su propio commit (`AGENTS.md`, «Un núcleo y varios programas»): `pyproject.toml` a `@v0.2.9`, el
`.venv` reinstalado desde la etiqueta con `--no-deps --force-reinstall`, y los tests de la fijación con
sus listas de versiones movidas. La versión del programa pasa a 0.0.13.

La v0.2.9 trae `ogr_core.api`, lo que se pidió en la T1 de la spec 006: `Registry`, los errores con
código (`OgrApiError` y los suyos, `did_you_mean`), `Workspace` con `WorkspaceNames`, los trabajos en
subproceso (`JobContext`, `JobCancelled`, `JobHooks`, `cancel_grace_s`), el puente (`BridgeConfig`,
`BridgeSession`) y sus mensajes codificados (`API_MESSAGES`, que la interfaz traduce con
`ogr_core.messages.render`). Su §2 no pide nada obligatorio a este programa; la sesión del núcleo ya
había corrido esta suite contra él con `--dev-core` (660 de 660).

## T11 — el espacio de trabajo y las operaciones de proyecto y de historia (2026-11-24)

`ogr_fem2d/api/`: el registro de este programa (`OPERATIONS`, un `Registry` del núcleo), el espacio de
trabajo (`api.workspace()`, un `Workspace` del núcleo) y `api.call(ws, nombre, **argumentos)`, por
donde llamarán la interfaz, la línea de órdenes y el servidor MCP (RF-6). Las operaciones:
`project_new`, `project_open`, `project_save`, `project_close`, `project_list`, `project_summary`,
`project_validate`, `project_settings` y `project_history`, con los nombres de Slip2D donde hacen lo
mismo.

- **El modelo es un valor, y el espacio de trabajo del núcleo lo cambia en sitio.** Se resuelve con lo
  que el núcleo ofrece para eso (`undo_step`, `document_hash`): el asa guarda una caja (`Held`) con el
  modelo del momento, y el paso de deshacer (`Step`) guarda el modelo de antes y el de después; deshacer
  y rehacer devuelven los mismos objetos. Una edición que falla a medias deja el modelo como estaba. La
  huella que dice «sin guardar» es la del documento (spec 004, D12).
- **Nada desconocido pasa en silencio** (RF-7): una operación, un argumento que la operación no toma
  (lo comprueba `api.call` contra su firma, con los más cercanos), un valor fuera de sus opciones o de
  otro tipo. Un `ModelError` sale como `InvalidArgument` con todos los problemas en sus detalles, cada
  uno con su regla, que es la clave por la que la interfaz los traducirá.
- **Los textos van codificados** (regla 2), como los del núcleo: `api/messages.py`, `FEM_MESSAGES`,
  con el nombre de cada paso de deshacer.
- **Abrir convierte un `.ogr` de Slip2D o un `.dxf`** en un modelo nuevo sin archivo, con su informe.
  Guardar nunca reemplaza otro archivo sin que se pida; cerrar con cambios sin guardar se rechaza sin
  que se pida.

7 tests; 14 mutaciones, 14 cazadas (la del «todo o nada» se escapaba: las operaciones de hoy calculan el
modelo nuevo antes de ponerlo, y ahora un test lo prueba directamente con una edición que falla a
medias).

### Anomalía encontrada, sin corregir (regla 6): un modelo a medio dibujar no se puede guardar

`ogr_file.write` (spec 004) valida el modelo entero antes de escribir. Un modelo sin contorno externo,
o con una región todavía sin material, no se puede guardar: `project_save` lo rechaza ahora con un
error que nombra cada problema, pero **en la interfaz el ingeniero no podrá guardar su trabajo hasta
terminar el modelo**. Slip2D guarda cualquier modelo. La lectura (`ogr_file.read`) también valida, así
que un archivo a medias tampoco se podría abrir.

Se propone: que el archivo admita un modelo **válido como estructura** (tipos, identificadores,
referencias, una tabla por fase) aunque tenga problemas de geometría o de asignación (sin externo,
cruces, regiones sin material), y que los diga al abrirlo; calcular sigue exigiendo el modelo entero
válido. Toca la spec 004 (D1, ADR-0004): espera el OK de la propietaria.

**Corregida con el OK de la propietaria (2026-11-24).** `model.validate_document` deja pasar lo que un
modelo a medio dibujar todavía puede romper (`model.DRAWING_RULES`: sin externo o con dos, y las reglas
geométricas de `regions`); lo demás sigue siendo obligatorio. `ogr_file` escribe y lee con ella; el motor
sigue con `validate`. `project_open` devuelve los problemas del modelo abierto, para que la interfaz diga
qué falta. Corregidos la spec 004 (RF-13 y «Lo que se encontró»), el ADR-0004 y `docs/modelo/formato.md`.
Test nuevo (`test_model_file_drawing_v0013.py`): un modelo vacío, uno sin externo, uno con un cruce y uno
con una región sin material van al archivo y vuelven iguales, con los mismos bytes; un material con
ν = 0,7, una asignación a un material que no existe y una carga en un contorno que no existe se siguen
rechazando al escribir y al leer; ninguno de los cuatro llega al motor. 3 tests; 5 mutaciones, 5
cazadas.

## T12 — las operaciones que editan el modelo y su malla (2026-11-24)

`ogr_fem2d/api/ops/model.py` y `mesh.py`: `boundary_add`, `boundary_circle`, `boundary_edit` (borrar,
renombrar, cambiar de tipo, cerrar o abrir, trasladar, mover, insertar o borrar un vértice, el arco o las
divisiones de un segmento), `material_set`, `material_delete`, `material_assign`, `region_excavate`,
`stage_add`, `stage_delete`, `stage_rename`, `field_set`, `condition_set`, `condition_delete`,
`condition_stage`, `condition_default`, `load_set`, `load_delete`, `load_stage`, `mesh_settings`,
`mesh_discretize`, `mesh_generate` y `mesh_reset` (RF-6, RF-12). Con los nombres de Slip2D donde hacen lo
mismo; 31 operaciones en total.

- **El caso 006, construido desde cero por las operaciones**, dibujado, con su material, sus
  condiciones, su carga y sus ajustes de malla, y mallado, es el modelo de su `modelo.ogrfem2d`: la misma
  huella del modelo, que incluye la malla, y los mismos nombres. Es la identidad que la T29 pedirá a la
  interfaz, ya cumplida por debajo de ella.
- **Cada edición de `model/edit.py` y de `stages.py` tiene su operación**, y un test lo cuenta contra los
  módulos: una edición nueva sin operación lo pone en rojo.
- **Dibujar con sus cortes es un paso de deshacer**, y la respuesta lista los vértices puestos; deshacer
  los quita de los dos contornos. `cut=false` dibuja sin cortar.
- **La malla se queda y se dice vieja** tras una edición de la geometría o de los ajustes; el primer paso
  (`mesh_discretize`) da los nudos de cada segmento sin tocar el modelo.

6 tests; 14 mutaciones, 14 cazadas (tres se escapaban al principio: la huella del modelo no mira los
nombres, cambiar un material no se probaba, y una carga puntual con contorno y vértice a la vez no se
pedía).

## T13 — calcular como trabajo en subproceso (2026-11-24)

`ogr_fem2d/api/worker.py` y `api/ops/analysis.py`: `analysis_run`, `job_get`, `job_cancel` y `job_list`,
sobre los trabajos del núcleo (`ogr_core.api.jobs`), con los nombres de Slip2D (RF-9 a RF-12; D9).

- **El destino del trabajo** (`worker.run_calculation`) llama a `calculate` con el aviso de progreso de
  la T6 convertido en el progreso del trabajo (fase a fase, con el evento, la fase, sus escalones y su
  iteración), y con `should_stop` leyendo el archivo de parada del núcleo.
- **Cancelar es en dos tiempos** (D9): con el plazo (`CANCEL_GRACE_S`, 5 s, que no mueve ningún número),
  el cálculo para entre dos fases y el `.h5` dice `cancelled` con las fases resueltas; si no para a
  tiempo, o sin plazo, se mata el árbol del proceso y queda el `.h5` anterior, intacto, sin temporal.
- **Lo que fallaría enseguida se rechaza antes de lanzar un proceso**, diciendo por qué: un modelo sin
  archivo, o con cambios que no están en el archivo (los resultados van junto a él, con su huella, y
  nacerían obsoletos), sin malla, con malla de otra geometría o con un material sin E o ν. Un segundo
  trabajo mientras corre uno, también.
- **Una fase que no se resuelve se dice**: el trabajo acaba `done`, con los resultados `incomplete`, la
  fase y el error del motor.
- **Los resultados del proceso hijo son los del motor, bit a bit**, y cancelar y volver a calcular es
  calcular una vez. Un trabajo de tres fases del túnel tarda 1,2 s, casi todo el arranque del proceso.
- **Cambia lo previsto**: el plan pedía probar el estado `queued`. El gestor del núcleo no encola, sino
  que rechaza un trabajo de más (`Busy`), y es lo que se prueba.

8 tests; 11 mutaciones, 11 cazadas (tres se escapaban al principio: el plazo por defecto, la limpieza
del temporal y el progreso de cada fase; ahora el destino y su limpieza se prueban también en el
proceso del test).

## T14 — las operaciones de resultados (2026-11-24)

`ogr_fem2d/api/ops/results.py`: `results_open` (el estado del `.h5`), `results_query` (por línea, por
contorno a una distancia, en todos los nudos, en todos los puntos y en un punto a lo largo de las
fases), `results_summary`, `results_table`, `results_report` y `results_field` (el campo listo para
dibujar de la T8) (RF-6; spec 005). 41 operaciones en total.

- **Cada consulta de la spec 005 da sus mismos números bit a bit** por su operación, y la tabla, el
  informe y el campo, el mismo texto y los mismos arreglos.
- **Unos resultados que no son válidos solo se leen pidiéndolo** (`allow_invalid`), y entonces cada
  respuesta dice su estado; con resultados obsoletos el resumen no da las reacciones por contorno (la
  malla puede ser otra).
- Los valores, en las unidades que guardan los resultados y en el convenio del usuario, con su unidad,
  su convenio y sus ajustes en cada respuesta (regla 12); la tabla, en las que muestra el modelo (spec
  005, D15).
- **Lo recuperado en los nudos se calcula una vez por fase** y se guarda con los resultados mientras ni
  el modelo ni el archivo de resultados cambien (su fecha entra en la clave): en el caso 005 es lo que
  cuesta 1,1 s por fase (T8).

4 tests; 11 mutaciones, 11 cazadas (dos se escapaban: la tabla en las unidades del modelo, con un modelo
en kPa, y la caché que no se renovaba, sin una consulta antes del cambio; ahora el modelo de la prueba se
muestra en MPa y se consulta antes de cambiarlo).

## T15 — la línea de órdenes (2026-11-24)

`ogr_fem2d/cli/` (`python -m ogr_fem2d.cli`, y `ogr-fem2d` para quien instale la rueda): `call OP` (una
operación, con sus argumentos en `--json` y `--arg nombre=valor`, y `--open` para abrir un modelo antes),
`run FILE` (una lista de pasos `{"op", "kwargs"}` sobre un espacio de trabajo), `info FILE` (el informe) y
`calculate FILE` (abrir, calcular en el subproceso y esperar). JSON a la salida; un error de una operación,
JSON con su código en la salida de error y estado 2 (RF-6).

- **La línea de órdenes son las operaciones**: los mismos pasos dados por ella en otro proceso responden
  lo mismo que aquí, los números de una consulta bit a bit (JSON conserva el `repr` de un float).

3 tests; 6 mutaciones, 6 cazadas (la que leía `--arg` como texto se escapaba: un número como texto lo
acepta la conversión del núcleo; ahora se pasa una lista).

## T16 — el servidor MCP (2026-11-24)

`ogr_fem2d/mcp/` (`python -m ogr_fem2d.mcp --workdir <carpeta>`, y `ogr-fem2d-mcp` para quien instale la
rueda con el extra `[mcp]`): una herramienta por operación, por la entrada y la salida estándar, sobre los
modelos de una carpeta, sin OAuth (RF-6; D1, D14). El SDK (`mcp` 2.3.0, MIT, el de Slip2D) se instaló en
el `.venv` con el OK de la propietaria, con sus dependencias (no toca `ogr-core`, NumPy ni SciPy), y se
declara como extra opcional.

- **Las herramientas salen del registro**, no se escriben a mano como en Slip2D: cada una toma los
  parámetros de su operación, con sus tipos, y su descripción es la de la operación. Un test comprueba que
  son exactamente las operaciones, con sus parámetros y los obligatorios. Tres operaciones no tenían
  descripción y ahora la tienen.
- **Un agente sabe qué toca cada herramienta**: la que edita un modelo, escribe un archivo o para un
  proceso no es de solo lectura; las demás, sí.
- **El SDK descartaba en silencio un argumento que no conoce**: `project_new` con `nmae` creaba un modelo
  sin nombre, sin avisar. Ahora el servidor lo rechaza por su nombre, con «Did you mean 'name'?», como
  `api.call` (RF-7).
- **Las capas, vigiladas**: un test en un intérprete limpio comprueba que las operaciones y la línea de
  órdenes no cargan Qt ni el SDK de MCP, y que el motor no carga nada del modelo, de los resultados, de las
  operaciones ni de la interfaz (regla 11).
- **La CI todavía no instala el extra `[mcp]`**: sus tests dicen que no pueden correr allí (`skip`) en vez
  de fallar. Para que corran hace falta una línea en `.github/workflows/wheels.yml`; queda para la
  propietaria, que decide si va en una rama corta.

4 tests; 8 mutaciones, 8 cazadas.

## T17 — la identidad de transporte y los casos por las operaciones (2026-11-24)

`tests/test_transport_v0013.py` (RF-6, RF-22; D13):

- **Identidad de transporte**: una lista de pasos que dibuja un modelo desde cero (dos estratos partidos
  por un contorno de material, gravedad, rodillos y una carga en la superficie), lo malla, lo guarda y lo
  calcula, dada en Python (`api.call`), a la línea de órdenes en otro proceso y al servidor MCP, da el
  mismo modelo (la huella del archivo) y los mismos resultados (todos los campos de todas las fases del
  `.h5`, bit a bit).
- **Los casos 005, 006 y 007 por las operaciones**: abiertos, calculados en el subproceso y consultados
  como dice su `esperado.json`, dan bit a bit lo que da la spec 005 en el proceso del test: el mismo
  archivo de resultados, campo a campo, y las mismas filas de cada consulta. Ese camino es el que
  `test_validation_queries_v0011.py` compara con Kirsch, Michell y Lamé dentro de las tolerancias fijadas
  antes de medir: así que estos cumplen las mismas, con los mismos números. 1 min 39 s los cuatro tests.

4 tests; 4 mutaciones, 2 cazadas y 2 equivalentes, descartadas: el nivel de gzip del hijo no cambia los
datos, y la distancia de una consulta sobre un contorno es 0 en los tres casos (ya la prueba la T14).
Añadida una que hace calcular al hijo otro modelo (ν = 0,31): cazada en los cuatro tests.

## T18 — el cierre de la parte B (2026-11-24)

- `docs/operaciones/catalogo.md`: las 41 operaciones por grupos, con su descripción y sus argumentos,
  escrito desde el registro (`api/catalog.py`); un test comprueba que la página es la del código.
- **El barrido de las reglas 7 y 12** sobre las operaciones (`test_api_rules_v0013.py`, 4 tests; 3
  mutaciones, 3 cazadas). Cada opción, con el test que demuestra que mueve lo que dice:

| Opción | Qué mueve | Test |
|---|---|---|
| `boundary_add(cut)` | con cortes, contornos que comparten vértices y un modelo válido; sin ellos, un cruce | `test_api_rules_v0013`, `test_cut` |
| `boundary_edit(with_dependents)`, `delete_boundary` | borrar o no las condiciones y cargas del contorno | `test_model_edit_v0012`, `test_the_option_moves_the_result` |
| `material_assign`, `region_excavate`, `condition_stage`, `load_stage` (`stage`, `this_stage_only`) | la tabla fase a fase | `test_api_model_v0013`, `TestStages`; `test_model_stages_v009` |
| `mesh_settings` (cada ajuste) | la malla, que queda vieja | `test_api_model_v0013`, `TestTheMesh`; spec 003 |
| `project_settings(units)` | las unidades de la tabla y del informe, no los valores | `test_api_results_v0013` (la tabla en MPa), `test_model_edit_rest_v0012` |
| `analysis_run(variant)` | el motor que escribe los resultados, dicho en el `.h5` y en el informe; los números, iguales a redondeo | `test_api_rules_v0013`, `test_variant` |
| `job_cancel(grace_s)` | parar entre fases (`cancelled`, fases escritas) o matar el árbol (el `.h5` anterior) | `test_api_analysis_v0013`, `TestCancel` |
| `results_query` (`kind`, `n`, `boundary`, `distance`, `side`, `stage`) | los puntos y los valores, como la spec 005 | `test_api_results_v0013`; spec 005, T17 |
| `results_field` (`level`, `absolute`, `range_mode`) | los triángulos, el valor absoluto, el rango de la leyenda | `test_api_rules_v0013`, `test_field_options` |
| `allow_invalid` | leer o no unos resultados que no son válidos, y decir su estado | `test_api_results_v0013`, `TestNotValid` |
| `overwrite` | reemplazar o no otro archivo | `test_api_project_v0013`, `test_open_save_close` |
| `wait` | cuánto espera la llamada; ningún número | — (no es un ajuste del resultado) |

  **Regla 12**: los resultados llevan lo que los decidió (`deciding_values`, spec 005), el motor y las
  versiones; una consulta devuelve su unidad, su convenio y sus ajustes, valores por defecto incluidos; un
  trabajo, su procedencia.

### Lo que se encontró en la parte B, en resumen

1. **Un modelo a medio dibujar no se podía guardar** (spec 004): corregido con el OK de la propietaria;
   el archivo guarda un modelo válido como documento (T11).
2. El espacio de trabajo del núcleo cambia el modelo en sitio; aquí es un valor, y se resuelve con los
   ganchos que el núcleo ofrece (`undo_step`, `document_hash`) (T11).
3. El gestor de trabajos del núcleo no encola: rechaza un segundo trabajo (`Busy`) (T13).
4. **El SDK de MCP descartaba en silencio un argumento desconocido**: ahora se rechaza por su nombre
   (T16).
5. La CI no instala el extra `[mcp]`: sus tests se saltan allí, a falta de una línea en el flujo, que
   decide la propietaria (T16).
6. El caso 006 construido desde cero por las operaciones tiene la huella de su archivo, y los casos 005 a
   007 por las operaciones dan bit a bit los números de la spec 005 (T12, T17).

## Después del cierre: la línea de órdenes, en UTF-8 (2026-11-25)

**La CI se puso en rojo en Windows** (Python 3.11, 3.12 y 3.13) con el push del cierre: dos tests de la
línea de órdenes leían su salida como UTF-8, y en Windows la salida de un proceso por una tubería va en la
codificación de la consola (cp1252). Una «ó» del informe la rompía. En este equipo no se veía porque los
tests la heredaban en el modo UTF-8. Ahora la línea de órdenes escribe siempre en UTF-8, y su test le da
un modelo con acentos y la codificación de la consola, como la CI. 1 mutación (sin el arreglo), cazada.
