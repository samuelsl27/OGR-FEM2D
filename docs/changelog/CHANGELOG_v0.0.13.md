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
