# Plan de implementación — Spec 006, interfaz, operaciones y cálculo

> **Aprobado (2026-11-24)**, con D1–D18 de `spec.md`. Ninguna fórmula nueva: lo numérico es la
> vía completa dando los números de la 005. Las partes C y D se precisan (archivos y nombres) cuando
> estén etiquetadas las piezas comunes de D1: hasta entonces, su lista de archivos es la prevista.

## Enfoque

0. **T0 y T1, antes de programar.** El OK de D1–D18; ADR-0005, el plan de desarrollo, el
   `tech-stack.md` y el `AGENTS.md` al día; la guía de interfaz en la constitución (D16). Después,
   las dos peticiones de D1, por escrito, para que avancen mientras se hace la parte A.
1. **Parte A, v0.0.12: lo que falta sin Qt, sin esperar a nadie.** Las ediciones del modelo como
   funciones puras, con los cortes, los arcos y los círculos (RF-1 a RF-3); el progreso de
   `calculate` (D9); el informe (D17); los triángulos y niveles para dibujar un campo (D11).
2. **Parte B, v0.0.13: operaciones y transporte.** Con la versión de OGR-Core de D1 fijada: el
   catálogo de operaciones de este programa, el cálculo como trabajo en subproceso, la línea de
   órdenes y el servidor MCP. Las identidades de transporte y los casos 005 a 007 por las operaciones.
3. **Parte C, v0.0.14: el modelador.** Con `ogr-gui` fijado y las dependencias de D14: la ventana,
   los menús, el lienzo, la entrada de geometría y los diálogos de la fase 1. La identidad del dibujo
   (el caso 006 dibujado tiene la huella del guardado).
4. **Parte D, v0.0.15: cálculo e interpretación en la interfaz, y el cierre de la fase 1.** La ventana
   de cálculo, la de interpretación, las consultas con sus gráficos, el informe, el puente (D8), los
   casos por la interfaz, la ayuda y el congelado.

El motor no cambia (regla 11): `calculate` gana un aviso de progreso que no toca ningún número
(casos 003 a 007 bit a bit, como en la 005). Las partes A y B no tocan `rust/` ni la CI. **La C y la D
sí tocan la CI** (Qt sin pantalla en las tres plataformas, el congelado con la interfaz): para ellas
se propone una rama corta `dev/…`, que elige la propietaria (`AGENTS.md`).

## Lo que se reutiliza

| De dónde | Qué | Para qué |
|---|---|---|
| `ogr_fem2d/model/` | el modelo, `problems`, `history.Document`, `stages`, `ogr_file`, `fingerprint`, `translate`, `import_slip2d`, `import_dxf`, `conventions` | Todo lo que editan y guardan las operaciones; el único cambio de signo (RF-16) |
| `ogr_fem2d/mesh/` | `geometry` (`MeshSettings`, los segmentos con arco), `discretize`, `mesher` | Discretizar y mallar en dos pasos (RF-14); la intersección de segmentos para los cortes (RF-2) |
| `ogr_fem2d/results/` | `calculate`, `open_results` y sus estados, `quantities` (el catálogo), `recovery`, `queries`, `table`, `locate` | El subproceso, el selector, los contornos, las consultas y la exportación |
| `ogr_fem2d/engine/reference/` | `SHAPES` (las funciones de forma) | La interpolación del dibujo (D11) |
| `ogr_core` (v0.2.7) | `project.commands` (deshacer), `units`, `loads`, `dxf`, `progress`, `messages`, `testing.runner` y `testing.leaks` | Lo que ya usa este programa; el vigilante de fugas cubre el estado de Qt |
| `ogr_core` (la versión de D1 i) | registro de operaciones, errores, conversión de argumentos, trabajos en subproceso, protocolo del puente | Parte B y el puente de la D |
| `ogr-gui` (v0.1.0, D1 ii) | temas y colores por papel, iconos, leyenda, paletas y niveles, enganche, barra de estado, motivos de lo deshabilitado, tareas en hilo, preferencias, ayudas de diálogo, gráfico XY, `tr()` y las comprobaciones de las reglas 2 y 3 | Partes C y D |
| OGR Slip2D (solo lectura) | la forma de `MainWindow._mk`, de `inventory.py`, del lienzo con `scale(1, -1)`, del panel de asignación, de la ventana de interpretación | Como modelo de lo que se escribe aquí, sin copiarlo (D1: no es genérico) |

## Archivos que se tocan

**T0 (documentación)**

| Archivo | Qué |
|---|---|
| `docs/decisiones/ADR-0005-interfaz-comun.md` (nuevo) | D1: qué va al núcleo, qué a `ogr-gui`, qué se queda aquí, y por qué |
| `spec/constitution/plan_de_desarrollo.md` | P1 con los tamaños medidos; la «Spec 006» en cuatro partes |
| `spec/constitution/tech-stack.md` | `ogr-gui` y las dependencias de D14 |
| `spec/constitution/guia-de-interfaz.md` | aprobada (D16) |
| `AGENTS.md` | «Stack»: `ogr-gui`; «Antes de nada»: el enlace a la guía de interfaz |

**Parte A (v0.0.12)**

| Archivo | Qué es | RF |
|---|---|---|
| `ogr_fem2d/model/edit.py` (nuevo) | las ediciones puras: contornos, vértices, materiales, asignaciones, campo, condiciones, cargas, malla, ajustes; cada una valida y nombra el argumento | RF-1, RF-7 |
| `ogr_fem2d/model/cuts.py` (nuevo) | la intersección de un contorno con los demás y el vértice añadido en los dos, con los arcos | RF-2 |
| `ogr_fem2d/model/shapes.py` (nuevo) | el arco por tres puntos o por inicio, centro y fin, partido si pasa de 180°; el círculo de cuatro arcos | RF-3, D10 |
| `ogr_fem2d/results/calculate.py` | `progress(event)`, opcional: fase, escalón, iteración, estado | RF-9, D9 |
| `ogr_fem2d/report/info.py` (nuevo) | el informe, en texto y HTML | RF-4, D17 |
| `ogr_fem2d/results/drawing.py` (nuevo) | la subdivisión, los valores en los subvértices, material a material, y los niveles | RF-5, D11 |
| `docs/interfaz/edicion.md` (nuevo) | las ediciones y los cortes, para quien escribe un script | RF-1–3 |

**Parte B (v0.0.13)**

| Archivo | Qué es | RF |
|---|---|---|
| `pyproject.toml` | la fijación del núcleo de D1 i (commit propio); el extra `[mcp]` | D1, D14 |
| `ogr_fem2d/api/__init__.py`, `api/workspace.py` (nuevos) | los modelos abiertos por identificador, cada uno con su `Document` y su ruta | RF-6, RF-8 |
| `ogr_fem2d/api/ops/project.py`, `model.py`, `mesh.py`, `analysis.py`, `results.py`, `history.py` (nuevos) | las operaciones, sobre el registro del núcleo | RF-6–8, RF-12 |
| `ogr_fem2d/api/worker.py` (nuevo) | el proceso hijo: abre el modelo, llama a `calculate` con `should_stop` y `progress` | RF-9–11 |
| `ogr_fem2d/cli/__main__.py` (nuevo) | `python -m ogr_fem2d.cli`: abrir, mallar, calcular, consultar, exportar, informe | RF-6 |
| `ogr_fem2d/mcp/server.py`, `mcp/__main__.py` (nuevos) | una herramienta por operación, generada del catálogo | RF-6 |
| `docs/operaciones/catalogo.md` (nuevo) | cada operación, sus argumentos y sus errores | RF-6, RF-7 |

**Parte C (v0.0.14)**, prevista

| Archivo | Qué es | RF |
|---|---|---|
| `pyproject.toml` | `ogr-gui` fijado; PySide6, qtawesome, matplotlib (D14) | — |
| `ogr_fem2d/__main__.py`, `gui/app.py` | arrancar la interfaz | — |
| `ogr_fem2d/gui/main_window.py`, `gui/actions.py`, `gui/menus.py` | la ventana, el registro de acciones y los menús en su orden; los de fases futuras (D4) | RF-13 |
| `ogr_fem2d/gui/i18n/` | el diccionario por áreas (D3) | RF-21 |
| `ogr_fem2d/gui/inventory.py` | cada acción con su operación o su motivo (D13) | RF-6 |
| `ogr_fem2d/gui/canvas/` | la vista, los objetos dibujados (contornos por tipo, regiones, malla, bloque del campo, condiciones, cargas), las herramientas de dibujo y de selección | RF-15, D10 |
| `ogr_fem2d/gui/dialogs/` | ajustes del proyecto, fases, campo, malla, materiales, panel de asignación, condiciones, cargas, informe de la importación | RF-14, RF-16, RF-17 |

**Parte D (v0.0.15)**, prevista

| Archivo | Qué es | RF |
|---|---|---|
| `ogr_fem2d/gui/compute_window.py` | la cola, el progreso, Cancelar, el registro, el resumen | RF-18 |
| `ogr_fem2d/gui/interpret/` | la ventana, el campo dibujado, el selector, las pestañas, las opciones del contorno y de la vista, el valor bajo el cursor, las consultas y sus gráficos | RF-19, RF-20 |
| `ogr_fem2d/gui/info_window.py` | el informe, guardable en HTML y en texto | RF-4 |
| `ogr_fem2d/gui/agent_bridge.py` | el puente, si llega (D8) | — |
| `ogr_fem2d/gui/help/` | la ayuda adaptada, con los casos | RF-21 |
| `poc/freeze/` y `.github/workflows/` | el congelado con la interfaz; Qt sin pantalla en la CI | — |
| `docs/changelog/CHANGELOG_v0.0.12.md` … `v0.0.15.md` | uno por parte | — |

## Decisiones de diseño

- **Capas** (`tech-stack.md`, «Separaciones»): `engine` no importa nada de `model`, `results`, `api`
  ni `gui` (regla 11); `model`, `results`, `report`, `api` y `cli` **no importan Qt**; `api` no importa
  `mcp`; solo `gui` importa PySide6 y `ogr-gui`. Lo vigila un test que lee el código y mira
  `sys.modules`, como el del núcleo.
- **Una edición es una función pura más un paso de deshacer.** `model/edit.py` da `modelo → modelo`
  y valida; la operación la aplica con `Document.edit(cambio, descripción)`, que es el único sitio
  donde se crea un paso. La interfaz llama a la operación, nunca al modelo directamente: así H5 sale
  sola, y el inventario lo comprueba.
- **Los cortes (RF-2).** Al añadir o mover un contorno se calculan sus intersecciones con los
  segmentos de los demás (recto con recto, recto con arco, arco con arco), con la tolerancia
  geométrica del mallador (spec 003). En cada intersección que no es ya un vértice se añade uno en los
  dos contornos; un arco partido conserva su centro en las dos mitades. Un tramo común a lo largo
  (segmentos solapados) es un error que nombra los dos contornos (004, D15), no un corte. La respuesta
  lista los vértices añadidos.
- **Arcos y círculos (RF-3).** Tres puntos dan el centro (la circunferencia que pasa por ellos;
  colineales, error); inicio, centro y fin, el arco en el sentido pedido. Un arco de más de 180° se
  parte en su punto medio, porque el segmento guarda el arco menor (spec 003, D3 y D4). El círculo,
  cuatro arcos de 90° con vértices a 0°, 90°, 180° y 270° desde el centro.
- **El progreso (D9).** `calculate(…, progress=None)` llama a `progress` al empezar y al terminar cada
  fase con `{stage, stages, step, steps, iteration, state}`; en elástico, `step = steps = iteration = 1`.
  El trabajo en subproceso lo escribe en su archivo de progreso (el mecanismo del núcleo). Cancelar:
  `should_stop` lee una marca del trabajo; si el hijo no termina en el plazo, el padre mata su árbol.
- **El dibujo de un campo (D11).** Para cada elemento activo, su material y sus valores recuperados
  por (elemento, nudo local) (005, D5): una subdivisión regular en coordenadas de área de nivel k
  (4ᵏ subtriángulos), con el valor de cada subvértice por las funciones de forma del elemento
  (`SHAPES`) y su posición por la misma transformación (los lados curvos se dibujan curvos). La
  salida son arrays (posiciones, triángulos, valores, material) que pinta la interfaz. Los niveles:
  `auto_stage`, `auto_all` o `custom`, con N intervalos; el rango de todas las fases lee el `.h5` de
  forma perezosa (005, RF-4).
- **El informe (D17).** Una lista de secciones (título, filas), que se vuelca a texto o a HTML; los
  textos son claves de `tr()` en la interfaz y el inglés en la línea de órdenes.
- **Las operaciones (B).** Nombres en inglés, con el verbo al final como en Slip2D (`project_new`,
  `boundary_add`, `mesh_generate`, `analysis_run`, `job_get`, `results_query`…), y **el mismo nombre
  que en Slip2D cuando hacen lo mismo**: un agente que conoce uno conoce el otro. Argumentos en las
  unidades guardadas (m, kN, kPa) y en el convenio del usuario, como el archivo. Cada respuesta es un
  diccionario serializable; un error, el del núcleo, con su código, su argumento y una pista.
- **El servidor MCP (B).** Por la entrada estándar, sobre archivos de una carpeta de trabajo, sin
  OAuth en la fase 1 (D1). Las herramientas salen del catálogo; un test comprueba que no falta ni
  sobra ninguna.
- **La interfaz (C y D).** La estética de Slip2D por `ogr-gui` (temas, colores por papel, iconos,
  barra de estado). Un registro de acciones como el `_mk` de Slip2D, que exige menú, `tr()` y
  operación. El lienzo, un `QGraphicsView` con y hacia arriba; la malla y los campos, **un solo objeto
  dibujado** que pinta todos los triángulos de una vez en una imagen guardada por escala (no un objeto
  por elemento: 28 066 T6 subdivididos son unos 450 000 triángulos). Las herramientas de dibujo, una
  máquina de estados por modo, como `tool_mode.py` de Slip2D.

## Formulación

| Qué | Fuente | Dónde | Estado |
|---|---|---|---|
| Interpolación de los valores recuperados dentro del elemento | Zienkiewicz y Taylor (2000), 5.ª ed., vol. 1 | ec. (14.27), pág. 376 (PDF 392) | **Leído** (spec 005) |
| Funciones de forma del T3 y del T6 y su transformación | Z&T (2000) | cap. 8 (spec 001 y 002) | **Leído**; en el código, `engine/reference/` |
| Intersección de segmentos y de arcos; circunferencia por tres puntos | — (geometría analítica elemental) | — | Sin fuente que citar; se prueba con identidades (el punto está en los dos) |

**Convenio**: las operaciones y la interfaz, en el del usuario (compresión positiva, la normal de
la carga hacia el terreno), como el `.ogrfem2d`; el cambio de signo, solo en `model/conventions.py`.

## Anomalías que se vigilan (regla 6)

- Que el aviso de progreso cambie algún número: los casos 003 a 007, bit a bit (como la T3 de la 005).
- Que un corte cree una región minúscula que el mallador no pueda llenar: el error tiene que nombrar
  los contornos.
- Que un arco partido en su punto medio no dé la misma malla que el arco entero dibujado en dos: si
  pasa, es de la discretización de la spec 003, y se reporta.
- Que el dibujo subdividido se aparte de la consulta en un nudo: no debe (los dos interpolan lo
  mismo); si pasa, es un error del dibujo.
- Que el caso 006 dibujado desde cero no tenga la huella del guardado: puede ser legítimo (el orden de
  los vértices, el sentido de un anillo); se reporta antes de tocar la huella o el caso.

## Estrategia de pruebas

| Parte | Test | Invariante |
|---|---|---|
| A | Cada edición: el modelo nuevo es válido o el error nombra el argumento; deshacer la devuelve | RF-1, RF-7, RF-8 |
| A | Cortes: recto con recto, con arco, por un vértice existente (sin vértice nuevo), solapado (error); el vértice añadido está en los dos; las regiones resultantes | RF-2 |
| A | Arcos: tres puntos sobre una circunferencia conocida dan su centro; colineales, error; 270° se parte en dos; el círculo pasa por sus cuatro vértices | RF-3 |
| A | Progreso: los eventos en orden, uno por fase, también en el cancelado y en el incompleto; los casos 003 a 007, bit a bit con y sin `progress` | D9 |
| A | Informe: cada sección aparece; los `deciding_values` están todos; sin resultados, lo dice; con obsoletos, lo dice | D17, regla 12 |
| A | Dibujo: el valor en los nudos es el recuperado; un campo lineal (T3) y cuadrático (T6) se dibujan exactos en los subvértices; dos materiales no se mezclan; los niveles automáticos cubren el rango; los de todas las fases, el de todas | D11 |
| B | Cada operación: argumento desconocido o de tipo inválido, error con su nombre; cada edición, un paso de deshacer | RF-6–8 |
| B | Trabajo: estados `queued`, `running`, `done`, `failed`, `cancelled`; cancelar entre fases deja `cancelled`; matar el árbol deja el `.h5` anterior; un fallo nombra el objeto | RF-9–11 |
| B | Sin malla, malla de otra geometría, resultados obsoletos: calcular o consultar se niega y dice por qué | RF-12 |
| B | Transporte: la misma secuencia por Python, la línea de órdenes y el servidor MCP da la misma huella y los mismos campos del `.h5` | identidad |
| B | Casos 005 a 007 por las operaciones: bit a bit con la consulta directa de la 005 y dentro de su tolerancia | RF-22 |
| C | Censos: todo texto por `tr()` con traducción; toda acción en un menú; toda acción con su operación o su motivo; toda entrada deshabilitada con su motivo | reglas 2 y 3, D4, D13 |
| C | Capas: nada fuera de `gui` importa Qt | capas |
| C | Cada diálogo: sus datos salen del modelo; aplicar llama a su operación; cada opción mueve el número (regla 7); sin `exec()` en el test | RF-14, regla 7 |
| C | El lienzo: clic, X, Y absoluto, relativo y polar, tabla, círculo y arco dan los vértices esperados; un clic en vacío lo dice; los cortes se ven | D10 |
| C | El caso 006 dibujado desde cero por las acciones tiene la huella del guardado | identidad |
| C, D | Rendimiento con la malla del 005: los tiempos de D15 | D15 |
| D | Ventana de cálculo: progreso por fase, Cancelar, cerrar con un cálculo en marcha | RF-18 |
| D | Interpretación: el selector es el catálogo (con los nombres de la axisimetría); la leyenda dice magnitud, unidad, convenio, fase y procedencia, y pinta con la función del lienzo; cada opción del contorno mueve el dibujo | RF-19, RF-20 |
| D | Casos 005 a 007 por la interfaz (sin pantalla): los mismos números que por las operaciones | RF-22 |
| D | El congelado abre, malla, calcula y consulta un caso en las tres plataformas | — |

Cada test lleva su cabecera (qué invariante protege) y tiene dientes: una mutación sistemática por
invariante (`{etiqueta: (archivo, texto, sustituto)}`), anotada en `tasks.md`.

## Riesgos

| Riesgo | Cómo se detecta o se acota |
|---|---|
| Las piezas de D1 tardan (otras sesiones, un repositorio nuevo) | La parte A no las necesita. Si al cerrar la A no están, se dice a la propietaria; aquí no se copian ni se rodean (`AGENTS.md`) |
| OGR-Core no acepta el armazón de operaciones | Se vuelve a la propietaria con la alternativa (todo en `ogr-gui`, con su subpaquete sin Qt), no se escribe uno propio |
| PySide6 para Python 3.14 (el del `.venv`) y en la CI con 3.11–3.13 | Se comprueba al instalar (T19); Slip2D excluye la 6.12.0 por debajo de 3.12 |
| Qt sin pantalla en la CI de Linux y macOS | La CI de Slip2D ya lo resuelve; se mira su flujo en la rama corta |
| El lienzo con 450 000 triángulos | Un solo objeto que pinta en una imagen guardada; se mide con D15. Si no llega, se propone (nivel de subdivisión según la escala), no se decide solo |
| El tamaño del congelado con Qt | Se mide en la parte D y se anota |
| Que un test de la interfaz deje estado (idioma, tema, ventanas) | El vigilante de fugas del núcleo, con la lista de permitidos explicada, como en Slip2D |
