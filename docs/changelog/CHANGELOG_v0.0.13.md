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
