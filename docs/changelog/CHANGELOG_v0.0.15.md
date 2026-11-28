# OGR FEM2D v0.0.15

**Fase 1, octava parte: el cálculo y la interpretación en la interfaz** (spec 006, parte D). Sobre
las operaciones de la parte B y el modelador de la parte C, en la rama corta `dev/modelador`. Este
archivo cuenta lo que fue entrando, tarea a tarea.

## T30 — la ventana de cálculo (2026-11-27)

`ogr_fem2d/gui/compute_window.py`; Análisis > Calcular (F9) y Ventana > Cálculo (RF-9 a RF-12, RF-18;
D9; la guía, §4, §5 y §14).

- **La ventana va al lado del modelo, no delante**: el cálculo corre en el proceso hijo de
  `analysis_run`, así que la ventana del modelo sigue viva mientras tanto. La de cálculo lo sigue
  preguntando a `job_get` cada 100 ms. Medido con el modelo de tres fases de los tests: la ventana no
  se para nunca más de 0,25 s (lo vigila un test).
- **La cola** es la lista de trabajos del espacio de trabajo (`job_list`), con su modelo, su tipo
  (cálculo o mallado), su estado y su tiempo; el elegido es el que se sigue. **El núcleo corre un
  trabajo cada vez**: un segundo cálculo con otro en marcha se rechaza con su motivo (`Busy`), no se
  encola. Una cola que espera y arranca sola tomaría el modelo al arrancar, no al pedirlo, y eso es
  otra decisión; queda anotado por si se quiere.
- **El progreso**: la fase (de cuántas, con su nombre) y, de una fase resuelta, sus escalones y su
  última iteración (D9: en elasticidad, un escalón de una iteración).
- **Cancelar sigue D9**: entre dos fases dentro del plazo (las fases resueltas quedan escritas y los
  resultados dicen `cancelled`), o matando el árbol del proceso. El plazo (5 s) se espera fuera del
  hilo de la ventana, para que no se congele: Cancelar vuelve enseguida (un test lo mide, < 0,5 s).
- **El registro** dice cada fase al empezar y al terminar, y se guarda para cada trabajo de la sesión
  (RF-11). **Hallazgo**: el progreso se lee, no se escucha, y una fase que empieza y termina entre dos
  lecturas no se ve. El registro la escribe igual, con lo que se sabe de ella (resuelta); las que sí
  se ven llevan sus escalones e iteración. Un test comprueba que cada fase sale una vez, ni más ni
  menos.
- **El resumen al terminar** (guía §5), también en la barra de estado: lo resuelto y dónde está
  escrito; de una fase que no se pudo resolver, **cuál, por su número y su nombre, y lo que dijo el
  motor** (RF-11); de una cancelación, lo que quedó. El botón «ir a los resultados» llega con la
  interpretación (T31).
- **Un rechazo antes de empezar nombra el objeto**: «No calculado: material 'rock': Un material no
  tiene E o ν, que el cálculo necesita: Propiedades > Definir materiales.» Las reglas `mesh_stale` y
  `material_incomplete` de `to_engine` tienen ahora su frase en `gui/problems.py`.
- **Calcular solo se ofrece con la malla del modelo**, y si no, dice por qué (sin malla, o malla de
  otra geometría). **Un modelo sin guardar se guarda antes, si la persona lo dice**: los resultados se
  escriben junto al archivo, con su huella (diálogo «Guardar y calcular»).
- **Cerrar con un cálculo en marcha pregunta una vez** y, con un sí, lo para de verdad (sin plazo:
  el programa se va). Las dos preguntas (el cálculo y los cambios sin guardar) se hacen antes de
  hacer nada, para que un Cancelar deje todo como estaba.
- La versión pasa a 0.0.15.

- **Una ventana sobre una sesión que no es suya** (la de un agente, D8) no la apaga al cerrar: por eso
  para el cálculo ella misma. Lo encontró el barrido de mutaciones: con la sesión propia, el apagado
  del espacio de trabajo ya lo mataba, y quitar la parada no rompía ningún test.

Tests: `test_gui_compute_v0015.py`, 9 tests. Regla 7, 17 mutaciones (el hueco del registro, el
detalle de una fase, el plazo de Cancelar y su hilo, el botón, el resumen con su fase y las palabras
del motor, la pregunta y la parada al cerrar, la puerta de Calcular, guardar antes, el rechazo con su
objeto, el resumen en la barra de estado, la frase de la regla): todas cazadas, una después de añadir
el test de la sesión compartida.

## T31 — la ventana de interpretación (2026-11-27)

`ogr_fem2d/gui/interpret/` (`window.py`, `drawn.py`, `field_item.py`); Análisis > Interpretar (F10),
también en Ventana y en el botón «Interpretar» de la ventana de cálculo (guía §5) (RF-12, RF-19,
RF-20; D11, D15).

- **El selector es el catálogo** de la spec 005, en su orden y por tipos, con los nombres de la
  axisimetría en un modelo axisimétrico. Los nombres del catálogo tienen ya su español.
- **Una pestaña por fase de los resultados**; la fase vista es la que se dibuja y la que se consulta.
- **El campo**: los triángulos de `results_field`, contorneados con matplotlib (`tricontourf`) y
  pintados en un solo objeto del lienzo como caminos, de modo que ampliar o mover solo los vuelve a
  pintar. Material a material, como pide D11: se unen solo los vértices de un mismo material en un
  mismo sitio, y las bandas se cortan entre dos materiales.
- **La leyenda** dice la magnitud con la unidad mostrada, el convenio, la fase, la procedencia
  (recuperados en los nudos por SPR, o el campo de elementos finitos de los desplazamientos), el rango
  y si es el valor absoluto, y **pinta con los colores de los ajustes, los mismos que el lienzo**: un
  test comprueba en cientos de puntos que el color pintado es el que los ajustes dan al valor.
- **Las opciones mueven el dibujo**: los intervalos, la paleta y el modo (bandas, líneas, bandas con
  líneas, gradiente, apagado), del diálogo de opciones de contorno de OGR-GUI; el valor absoluto; el
  rango (esta fase, todas las fases o a mano), y el sistema de unidades del modelo. **El gradiente se
  dibuja como 96 bandas finas**: un lienzo de caminos no tiene gradiente sobre un triángulo, y a esa
  cuenta los escalones no se ven.
- **El diálogo de opciones, sin «Ajustar a los resultados»**: no se le dan valores, así que su
  percentil (que escondería el pico de una tensión, T19) nunca se usa. Su casilla de rango automático
  explicaba ese percentil; aquí lleva otra explicación (el rango elegido en la ventana, del menor al
  mayor valor). Lo del percentil ya está pedido a OGR-GUI.
- **El valor bajo el cursor es el de la consulta**, interpolado exacto y no leído de los colores
  (D11), en las unidades mostradas, con el material; fuera de la malla o en una región excavada, lo
  dice. Para eso, `results_query` tiene un tipo nuevo, **`at`**: el valor en (x, y) en una fase.
- **Unos resultados no válidos no se confunden con válidos**: obsoletos (de otro modelo), incompletos o
  cancelados se dicen en una franja sobre el lienzo, en la primera línea de la leyenda («NO VÁLIDOS») y
  en el título; de unos incompletos solo hay pestañas de las fases escritas. Una edición del modelo
  que deja obsoletos los resultados se ve al momento en la ventana abierta.
- Interpretar solo se ofrece con resultados, y si no, dice por qué. Toda acción de la ventana está en
  un menú (regla 3).

**D15 con la malla del caso 005, medido** (28 066 T6, 424 288 triángulos de dibujo):

| Qué | Medido | D15 |
|---|---|---|
| Ampliar, mover, el valor bajo el cursor | 0,011–0,017 s | ≤ 0,1 s |
| Otra magnitud o un desplazamiento, en la misma fase | 0,56 s | ≤ 1 s |
| **El primer dibujo de una fase** | **3,9 s** | ≤ 1 s |

**Hallazgo: el primer dibujo de una fase no cumple D15.** Lo que pesa es la recuperación de las
tensiones de la fase (SPR, `results/recovery.py`, 1,4 s, un bucle de Python por parche), la primera
importación de matplotlib (0,3 s) y abrir los resultados (0,2 s). Después, la recuperación queda
guardada y todo lo demás cumple. No se afloja el objetivo: el test lo deja vigilado (≤ 5 s) para que
no crezca. **Propuestas**, para que decida la propietaria: vectorizar la recuperación (es de la spec
005 y tiene que dar los mismos números, bit a bit), hacerla en el proceso hijo al calcular y guardarla
en el `.h5`, o hacerla en segundo plano al abrir la ventana.

**Mejoras de velocidad**, que no cambian ningún número (lo vigila la suite de
resultados, 92 tests):

- La huella del documento se calcula una vez por modelo (un modelo no cambia): con la malla del caso
  005 costaba 0,1 s, y la ventana y cada consulta la pedían.
- Los resultados abiertos se guardan mientras no cambian ni el modelo ni el `.h5` (su fecha y su
  tamaño); antes, cada pregunta los volvía a abrir y a comprobar su huella. Una consulta pasa de
  0,28 s a 0,002 s.
- El rango de un campo usa el campo ya dibujado y las fases ya recuperadas; antes lo dibujaba otra vez
  y, con «todas las fases», recuperaba cada fase en cada llamada. Un campo repetido pasa de 0,75 s a
  0,11 s.
- Y unir los vértices de un material (0,57 s con el caso 005) se hace una vez por fase, con un solo
  ordenamiento (0,09 s).

**Anomalía encontrada y no corregida** (regla 6): `results_query` de tipo `line` con dos puntos
seguidos iguales deja escapar un `ValueError` en vez de rechazarlo con un `InvalidArgument` que lo
nombre (RF-7). Se arreglará en la T32, con las consultas en la interfaz, si la propietaria está de
acuerdo.

**Encontrado y corregido en la propia tarea**: matplotlib deja sin pintar un valor que cae justo en el
nivel de arriba, y con el rango automático ese valor es el máximo del campo: el pico se quedaba en
blanco. Lo encontró el test de un rango estrecho (todo el modelo pintado, con el color de su extremo
fuera del rango); el valor se recorta ahora un pelo por debajo del nivel de arriba.

Tests: `test_gui_interpret_v0015.py`, 15 tests; en `test_gui_compute_v0015.py`, el botón de ir a los
resultados. Regla 7, 20 mutaciones (la unión por material, el recorte y su borde de arriba, los
colores de las bandas, las líneas, el gradiente, la franja, el aviso al editar, los nombres de la
axisimetría, las unidades, el valor absoluto, el rango a mano, el convenio de la leyenda, el valor del
cursor, el botón de ir a los resultados, la puerta de Interpretar, la huella guardada, la clave de los
resultados guardados, la consulta `at`): todas cazadas; cuatro después de reforzar sus tests (la unión
probaba sitios de un solo material; el valor absoluto, una fase sin desplazamientos; el recorte no
tenía test; el botón tenía una condición de más, quitada).

## Los dos errores de la T31, arreglados (2026-11-27)

La propietaria dijo «arregla los errores».

- **Una consulta que no se puede hacer se rechaza diciéndolo** (RF-7): una línea con dos puntos
  seguidos iguales, n < 2 o una distancia sobre un contorno sin su lado dejaban escapar un
  `ValueError`; ahora son un `InvalidArgument` («La consulta no se puede hacer así: …»), también por
  `results_table` (`test_api_queries_v0015.py`).
- **El primer dibujo de una fase, de 3,9 s a 1,3 s** con el caso 005, sin cambiar ningún número:
  - la recuperación hace los mismos ajustes y las mismas sumas en el mismo orden, con las cuentas en
    enteros de Python y los valores recogidos de una vez: 1,15 s → 0,6 s. **Un test la compara bit a
    bit con la de la v0.0.14**, guardada para eso en `tests/_recovery_v0014.py`, en mallas de tres y
    seis nudos, con dos materiales, un material de un elemento de grueso y elementos inactivos
    (`test_results_recovery_v0015.py`);
  - el localizador de la malla de una vista se hace la primera vez que se pregunta un punto, no al
    hacer la vista (0,24 s que dibujar un campo no necesita); la ventana lo prepara en cuanto ha
    dibujado, para que el cursor no espere;
  - el programa importa al arrancar, fuera del hilo de la ventana, lo que el contorneo necesita de
    matplotlib (1 s la primera vez).
- **Sigue sin llegar a 1 s** (1,3 s): lo que queda es sobre todo la recuperación. Llegar a 1 s
  pediría ajustar los parches todos a la vez (vectorizar), y eso cambiaría los últimos bits de los
  valores recuperados: es un cambio de números de la spec 005, y queda para que lo decida la
  propietaria. Las otras dos salidas siguen ahí: recuperar al calcular y guardarlo en el `.h5`, o
  en segundo plano. El test vigila ahora ≤ 4 s: 1,3 s es lo medido con el equipo libre, y con otro
  programa ocupándolo (un servidor de OGR Slip2D en marcha) sale cerca de 3 s.

## T32 — las consultas en la interfaz (2026-11-27)

`ogr_fem2d/gui/interpret/queries.py`; el menú Consulta de la ventana de interpretación (RF-19, RF-20;
spec 005, RF-11 a RF-15).

- **Las consultas de la 005, desde la ventana**: una línea (dos clics) o una polilínea (clics y clic
  derecho o Intro), con N puntos o en sus vértices; un contorno, sobre él o a una distancia de un
  lado (dentro o fuera de uno cerrado; izquierda o derecha, según su sentido, de uno abierto), con N
  puntos por tramo o en sus vértices; todos los nudos; y un punto fase a fase. Esc cancela.
- **Cada consulta es la de su operación** (`results_query`): la ventana enseña sus filas tal como
  vienen, en las unidades del modelo, con el material y la procedencia de cada valor (recuperado por
  SPR, el campo de su elemento, el campo de elementos finitos) o por qué no lo tiene.
- **Lo que decidió las filas se dice con ellas** (regla 12): la fase, el método (SPR material a
  material, o las funciones de forma) y los ajustes, también los que se quedaron por defecto (en los
  vértices, sobre él, el lado).
- **El gráfico es el de esas filas** (`ogr_ui.xy_chart`, en una ventana no modal): frente a la
  distancia a lo largo de la consulta o frente a la fase, con una serie por material donde hay dos
  (un contacto). De todos los nudos no hay gráfico, y el botón dice por qué.
- **La tabla es la de `results_table`**, en las unidades del modelo (spec 005, D15): un test comprueba
  que lo que escribe la ventana y lo que escribe la operación son el mismo archivo, byte a byte.
- **Las consultas se dibujan en el lienzo** y se borran con Consulta > Borrar las consultas dibujadas.
- Una historia (un punto fase a fase) ya no recupera todas las fases en cada llamada: usa las vistas
  guardadas, como el campo. No cambia ningún número.

Tests: `test_gui_queries_v0015.py`, 9 tests. Regla 7: los puntos de una línea, los de cada tramo de un
contorno, la distancia y el lado, la fase y el sistema de unidades mueven el número; 13 mutaciones,
todas cazadas.

## T33 — el informe, y lo que decidió el resultado a la vista (2026-11-27)

`ogr_fem2d/gui/info_window.py`; Análisis > Informe (F11), también en el menú Resultados de la
interpretación (RF-4, RF-20; D17; regla 12).

- **El informe de la ventana es el de la operación** (`results_report`, que ahora también da sus
  secciones): en inglés, su texto y su HTML son los de la operación, carácter a carácter (un test lo
  compara). Se guarda como HTML o como texto, tal como se ve.
- **Cada línea del informe lleva su código** (`model/report_messages.py`), como se decidió el
  2026-11-25 para el informe de una conversión: la ventana lo dice entero en el idioma del lector, y
  lo que el usuario escribió, los identificadores y los números quedan como están. **El inglés no
  cambió**: el texto y el HTML del informe de los modelos de los tests son los de antes, carácter a
  carácter (comprobado antes del cambio y con `test_report_info_v0012.py`), y lo que el `.h5` guarda
  de lo que decide el resultado, también (lo que decide el resultado se escribe con código, pero es
  el mismo texto).
- **Lo que decidió el campo, al lado del campo** (RF-20), en la interpretación: el estado de los
  resultados, quién los escribió y con qué motor; la malla (la cota B, los ángulos, lo que anotó el
  mallador); **lo que decide el resultado tal como se escribió con los resultados**, así que unos
  resultados obsoletos enseñan sus valores y no los del modelo editado; y los ajustes del dibujo (la
  subdivisión, el rango, los intervalos, la paleta), que se mueven con ellos. Para eso `results_open`
  da también lo que decidió los resultados.
- **Los nudos del eje que restringe el motor** (spec 002, D1 bis) están ahora en el informe, en la
  malla, en un modelo axisimétrico: un valor que decide el resultado y no se dibuja (RF-20). Un test
  los compara con los que el motor restringe.

Tests: `test_gui_report_v0015.py`, 8 tests. Regla 7, 11 mutaciones (cada línea dicha, guardar en HTML o
en texto, los nudos del eje, el sí y el no, lo que decidió los resultados, su traducción, el estado, los
intervalos del dibujo y que el panel se vuelva a escribir): todas cazadas.

## T34 — el puente entre el servidor MCP y la ventana abierta (2026-11-27)

`ogr_fem2d/api/bridge.py`, `ogr_fem2d/gui/agent_bridge.py`; Herramientas > Puente con el agente
(MCP) (D8).

- **Lo que había**: el núcleo fijado (v0.2.9) trae el protocolo del puente, el lado que contesta sin Qt
  (`BridgeSession`) y el encaminador (`WindowRouter`); `ogr-gui` v0.1.0 no trae una pieza de Qt para
  él. No hace falta: el núcleo deja el socket a la ventana, y el de este programa es un `QTcpServer`
  en 127.0.0.1, en el bucle de la ventana, con una sesión del núcleo por conexión. Nada se copia del
  núcleo; aquí solo está lo que nombra el puente de este programa (`ogr-fem2d-bridge/1`, su carpeta
  de anuncios), para que una ventana de OGR Slip2D y una de OGR FEM2D no se confundan.
- **Lo que hace un agente es de la ventana**: cada llamada pasa por la sesión de la ventana, como la de
  un menú, así que se dibuja al momento y es un paso de su historia, que se deshace con Edición >
  Deshacer.
- **El servidor MCP va a la ventana** cuando una tiene el puente encendido (el `WindowRouter` del
  núcleo, como lo hace `build_server`), y a sus propios modelos si no; una llamada que nombra un
  modelo o un trabajo suyo se queda con él. `--attach` trabaja solo sobre una ventana y, sin ella,
  dice qué abrir.
- **Con un cálculo en marcha, una edición responde `Busy`**: los resultados que se están escribiendo
  son del modelo tal como estaba al empezar, y un agente que siguiera editando los dejaría obsoletos
  sin saberlo. Preguntar, seguir el trabajo (`job_get`, `job_list`) y pararlo (`job_cancel`) sí se
  puede.
- El anuncio (el puerto y la clave, en un archivo que solo lee el usuario) se retira al apagar el
  puente y al cerrar la ventana; una clave equivocada no entra.
- El menú Herramientas deja de ser de una fase futura: tiene el puente y, deshabilitada con su motivo,
  la entrada de las herramientas de dibujo que llegan después (`menus.SOON`).

Tests: `test_gui_bridge_v0015.py`, 4 tests (el cliente en su propio hilo mientras el bucle de la ventana
contesta, como el servidor MCP desde su proceso). Regla 7, 8 mutaciones (el Busy y lo que deja
preguntar, la sesión de la ventana, el anuncio retirado al apagar y al cerrar, el encaminador del
servidor y `--attach`, la puerta cerrada tras una clave equivocada): todas cazadas; tres después de
reforzar los tests (una pregunta durante el cálculo, la herramienta MCP de verdad en vez de su
encaminador, el socket cerrado). El barrido encontró también que construir el servidor MCP cambia el
`logging` del proceso: el test lo deja como estaba (`root_logging_kept`, como los de la T16).

## T35 — los casos 005, 006 y 007 por la interfaz (2026-11-27)

`tests/test_gui_cases_v0015.py` (RF-22): cada caso se abre en la ventana, se calcula con Análisis >
Calcular (la ventana del cálculo, el proceso aparte), se abre en Análisis > Interpretar y se consulta
como dice su `comparaciones_consulta`.

- **Los números de la ventana son los de las operaciones**: cada consulta da, fila a fila y bit a bit, lo
  que da `results_query` en un espacio de trabajo aparte sobre el mismo `modelo.h5`, y lo que leen las
  consultas del `.h5` que escribió la ventana.
- **Son los del caso**: cada fila, dentro de la tolerancia que su `esperado.json` fijó antes de medir,
  contra su solución cerrada. Los peores errores son los de la spec 005: 005, σθ 0.0022 p0 en el radio y
  0.0035 p0 en la pared; 006, σ3 0.0045 q en el eje; 007, σR 0.0015 P0 en el radio y σt 0.0015 P0 en el
  arco.
- **La gráfica es de esas filas**, contra la distancia, en las unidades que se muestran (MPa: los casos
  están escritos en MPa).
- **Los contornos dicen la solución cerrada**: en los centros de los triángulos de la zona donde la forma
  cerrada es la del caso (cerca del hueco, bajo la faja, cerca de la cavidad), el color pintado es el de
  la leyenda para el valor exacto, salvo donde está a menos de la tolerancia del caso de un límite de
  banda: unos 500 puntos por magnitud, todos.
- Las soluciones cerradas de las consultas pasan a `tests/_query_references.py`, que usan este test y el
  de la spec 005 (`test_validation_queries_v0011.py`, la misma aritmética, cambiada de sitio).
- Las fichas VER-STR-01, VER-STR-04 y VER-STR-09 tienen su «Seguimiento»: el dibujo de la línea y de los
  contornos.
- Barrido de mutaciones (6: el factor de unidades del dibujo y de las filas, el eje de la gráfica, los
  puntos de la línea, la consulta dibujada en el lienzo, la fase de la consulta): 5 cazadas. La de la
  fase es equivalente en estos casos, que tienen una sola fase; la cazan los tests de la T32.

## Los dos rojos de la CI de la T34 (2026-11-27)

La CI de la rama (Linux en verde; Windows en las tres versiones de Python y macOS 3.13, 828/829)
encontró dos fallos de los tests de la T30, no del cálculo:

- **macOS: el resumen vacío tras la espera.** `ComputeWindow.wait()` (la usan los tests) leía los
  trabajos (`poll`) y después preguntaba si quedaba alguno (`running`): si el trabajo acababa entre las
  dos, la espera salía sin haber dicho su final. Ahora lee una vez más al salir. En el programa no
  pasaba: el temporizador vuelve a leer. Un test reproduce el hueco (el trabajo acaba justo después de
  una lectura) y falla sin el arreglo.
- **Windows: la ruta del `.h5` en el resumen.** La carpeta temporal del runner se llama corta
  (`RUNNER~1`) y el núcleo resuelve la ruta del proyecto a la larga, que es la que dice el resumen. El
  test compara con la ruta resuelta.

## El primer dibujo de una fase, dentro de D15 (2026-11-27)

La propietaria eligió guardar la recuperación al calcular. Al ir a hacerlo apareció que chocaba con
la spec 005, D6 («No van los valores recuperados, que dependen de un método»); se le dijo antes de
tocar nada, y modificó D6: **una fase puede llevar los valores recuperados, marcados con su método y
su versión**, y un lector solo los usa si la marca es la de su método. Se cumple el motivo de D6 (un
método mejor se sigue viendo en los resultados viejos).

- `calculate` recupera la tensión y la deformación de cada fase al escribirla y las guarda en
  `recovered/<tensor>`, con `recovery.METHOD` (`"spr-by-material/1"`). Son **los mismos bits** que se
  recuperarían al leer: un test lo comprueba en todas las fases, con elementos excavados, y las
  consultas dan las mismas filas con ellas y sin ellas.
- **Una vez por nudo y material**: una tabla y, por nudo de elemento, su fila. Caso 005: el `.h5`
  pasa de 6.1 MB a 8.9 MB (12.6 MB si se guardaran por nudo de elemento); calcular, de 11.2 a 13.0 s.
  Leerlas, 0.015 s; recuperarlas, 0.86 s.
- Con otra marca, o sin ellas (un archivo de antes), se recuperan al leer como hasta ahora. Un
  grupo que no está como se escribió es un archivo dañado, dicho al abrir. No cambia
  `format_version`: son opcionales.
- **La huella del modelo**, más rápida (0.42 → 0.19 s con el caso 005, las dos huellas): su paso a
  valores planos preguntaba a cada número de la malla si era una clase de datos. Las mismas huellas
  de los casos 005, 006 y 007, comprobado antes y después.
- **D15 con el caso 005**: el primer dibujo de una fase pasa de 1.3 s a 0.6 s, medido en esta
  máquina sin carga. El test vuelve a pedir el 1 s de D15 (con el margen de la CI), en vez de los
  4 s con los que se sostenía el hallazgo de la T32.

## Un tercer rojo de la CI: la cancelación que acaba antes de su respuesta (2026-11-27)

Con los dos arreglos de arriba, la CI siguiente dio verde en Linux y Windows y un rojo en macOS (3.12
y 3.13): el resumen de una cancelación decía solo «Cancelled.». **Este sí es del programa**: el
trabajo acababa cancelado antes de que `job_cancel` contestara si había tenido que parar el proceso,
y la ventana lo decía sin esa respuesta. Ahora espera a la respuesta para decir el final, con el
temporizador en marcha. Un test hace llegar la respuesta tarde y falla sin el arreglo.

## ogr-gui de v0.1.0 a v0.1.3 (2026-11-27)

OGR GUI publicó lo que este programa le pidió el 24 y el 25 (v0.1.1, v0.1.2 y v0.1.3). La propietaria
decidió subir la fijación, en un commit propio (`41a6c5d`): con solo eso, la suite entera da
840/840. Después, lo que cada changelog pide a un programa:

- **El percentil (0.1.1)**: el campo del diálogo de contornos declara `fit_percentile=1`, el rango
  entero, y «Fit to results» vuelve a estar (la T19 lo había escondido, porque su percentil 98
  habría escondido el pico de una tensión). El dibujo no ajusta con `fit_to`: su rango es el entero
  de `value_range`; un test comprueba que el ajuste del diálogo da exactamente ese rango, en las
  unidades que se muestran y también con el valor absoluto.
- **El español del núcleo (0.1.2)**: `say()` busca el código en todos los catálogos del núcleo que
  un mensaje dicho aquí puede traer (las operaciones, el mallador, los archivos, la geometría, el DXF,
  los pasos de la historia) además de los de este programa; antes, un mensaje del mallador salía en
  inglés. Las plantillas del español de `ogr_ui` son las del núcleo v0.2.12, y este programa fija la
  v0.2.9: **un test comprueba que cada plantilla con palabras de esos catálogos, en la v0.2.9, tiene
  su español** (todas lo tienen). La entrada «Edit boundary ({op})» se quita de este diccionario: la
  de `ogr_ui` es la misma.
- **La entrada X,Y (0.1.3)**: se quita el rodeo de la ventana (`_typed_points` y `_typed`, que quitaban
  el validador y ponían su propia lectura) y la lectura de este programa (`canvas/tools.parse_point`):
  la del campo es ahora la de `ogr_ui.point_entry.read_point`, hecha a partir de ella. Las
  herramientas le dan el punto de referencia (el último vértice, o el centro del círculo) en las
  unidades que se muestran, cada vez que puede cambiar, y reciben el punto absoluto. Los tests de la
  lectura quedan como contrato de lo que este programa usa (D10, D12), y uno nuevo comprueba que la
  referencia sigue al dibujo. La tabla de coordenadas tiene su propia lectura, que no cambia.

## T36 — la ayuda, el congelado con la interfaz y la CI (2026-11-27)

**La ayuda** (`gui/help/`, RF-21): Ayuda > Temas de ayuda (F1) abre una ventana con ocho páginas
escritas en el programa, en inglés y en español (`i18n/es_help.py`): el trabajo en orden, dibujar,
mallar, calcular, interpretar, los convenios y lo que decidió un resultado (reglas 10 y 12), el
puente y los casos. Cada frase se comprobó contra el programa (los menús, sus teclas, lo que hace
cada diálogo), y los nombres en español son los de los menús.

- **Sin red**: los enlaces solo van a otra página, a un caso o a la ficha de un caso; el navegador de
  la ventana no carga ningún recurso que no se le dé, y un enlace de otra clase se dice y no se
  sigue. Un test muestra todas las páginas y sigue todos los enlaces sin que se abra ningún socket.
- **Los casos** se leen de `validacion/casos` (en el árbol, o dentro del programa congelado): cada uno
  con su ficha, su fuente y su tolerancia como las dice su `esperado.json`. Los que tienen modelo
  (005, 006 y 007) se abren **como copia**, en la carpeta que se elige: el archivo del caso no se toca
  nunca. Sin la carpeta (una rueda instalada), la página dice dónde están.

**El congelado con la interfaz** (`poc/freeze/gui.py`, `build.py`): un segundo ejecutable,
`ogr-fem2d`, con ventana, los casos dentro y las soluciones cerradas de su autoprueba. Su
comprobación lo corre fuera del árbol y sin pantalla con `--self-test`: abre una copia del caso 007,
**lo malla otra vez** con Malla > Discretizar y mallar (la misma malla que la del caso, bit a bit),
lo calcula con Análisis > Calcular y lo consulta en la interpretación como dice su
`comparaciones_consulta`, contra la esfera hueca de Lamé. En Windows, en esta máquina: lo mismo que
desde las fuentes (σR 0.0015 P0 en el radio, el peor), en 49 s; **la carpeta, 315 MB**.

- **Lo que hizo falta**: los trabajos del núcleo lanzan su hijo como `sys.executable -m
  ogr_core.api.jobs.worker CARPETA`, y un programa congelado no entiende `-m`. El ejecutable toma
  esa orden al empezar y llama al trabajador del núcleo tal cual; nada del núcleo se copia ni se
  cambia. Se le propone al núcleo que lo resuelva él (abajo, «Para OGR-Core»).
- **La CI**: el trabajo `freeze` instala las bibliotecas de Qt en Linux y construye y comprueba los
  dos programas en las tres plataformas.
  En la CI (run 46061178931, `85a428b`) los dos pasan en las tres. La autoprueba del congelado con
  la interfaz, y el tamaño de su carpeta:

  | Plataforma | Autoprueba | Carpeta de `ogr-fem2d` | La de `ogr-fem2d-casos` |
  |---|---|---|---|
  | Windows | 34 s | 291 MB | 249 MB |
  | macOS | 47 s | 340 MB | 116 MB |
  | Linux | 26 s | 602 MB | 519 MB |

  El de los casos, sin interfaz, pesa en la CI mucho más que su último congelado en esta máquina
  (120 MB, con NumPy y SciPy y sin Qt): no se ha mirado qué arrastra allí. Un congelado más
  pequeño es de la distribución (spec 032).

### Para OGR-Core

Un programa congelado no puede ser el hijo de un trabajo: `_spawn` lanza `sys.executable -m
ogr_core.api.jobs.worker`. Una función del núcleo que un programa llame al empezar (como
`multiprocessing.freeze_support`), o que el núcleo lance el hijo de otra manera cuando
`sys.frozen`, evitaría que cada programa lo resuelva en su punto de entrada.

## Dos arreglos tras la T36 (2026-11-27)

- **Una fase, en singular.** La autoprueba del congelado dijo «Complete: the 1 stages are solved»: la
  ventana del cálculo pegaba el número a una frase en plural. Ahora una fase tiene su frase entera
  (el empiece, el final completo y el incompleto), cada una con su español, como los mensajes con
  código del núcleo. El test de la fase que no se puede resolver comprobaba, sin verlo, el plural
  equivocado («the 1 stages before it»); se corrige con él.
- **`test_project_setup_v001` con `--dev-core`** (lo encontró el changelog 0.2.13 de OGR-Core): el
  test relanza el runner en un Python desnudo con `PYTHONPATH` en la carpeta del núcleo de la
  corrida, y con `--dev-core` esa carpeta es un árbol de OGR-Core, sin `ogr_ui`, que el runner
  necesita. Ahora se le da también la carpeta de `ogr_ui`, detrás de la del núcleo; pasa con el núcleo
  fijado y con el árbol de OGR-Core (`0.2.13.dev0`).

## La fijación sube a OGR-Core v0.2.13 (2026-11-28)

Decidido por la propietaria al empezar la T37. Los changelogs del núcleo de la 0.2.10 a la 0.2.13 dicen
de este programa «nada»: los lectores y el informe que cambian no se usan aquí. Cambian el
`pyproject.toml`, el entorno (instalado desde la etiqueta con `--no-deps`), `AGENTS.md` y las listas de
versiones de `test_project_setup_v001`, que se escriben para la fijación. La suite entera, con el núcleo
nuevo: 850 de 850 (`shared: ogr_core 0.2.13 … (installed, no git tree)`). La fila de este programa en
`docs/consumidores.md` de OGR-Core la corrige su sesión.

## T37 — el cierre de la spec 006 y de la fase 1 (2026-11-28)

### Los casos 001 a 007, bit a bit

Desde el cierre de la spec 005 (`9c366ff`) no ha cambiado nada en `ogr_fem2d/engine/` ni en `rust/`.
Sí han cambiado el camino del cálculo y el de la lectura: la recuperación guardada al calcular, la
recuperación más rápida y la huella. Así que se compararon los números, no el código. Un guion
calculó los siete casos en `9c366ff` (un worktree, con el mismo `.venv` y el mismo motor compilado)
y en este árbol, e hizo la huella SHA-256 de todo lo que sale:

- 001 a 004: los resultados del motor, tal como los usan sus tests;
- 005 a 007, con el motor de referencia y con el de Rust: los conjuntos de datos del `.h5` (sin el
  grupo `recovered`, que antes no existía), los valores recuperados en los nudos y su procedencia,
  cada magnitud del catálogo en los nudos y en los puntos de integración, y el valor en tres puntos
  por fase.

**Las diez huellas son iguales**. Los valores recuperados que ahora se leen del `.h5` son los que la
v0.0.11 recuperaba al leer. Los casos siguen dentro de su tolerancia en sus tests (spec 005, partes
B y D).

### Lo que se encontró en el barrido (regla 6), y lo decidido

La propietaria vio los cuatro hallazgos antes de que se tocara nada, y dijo que sí a los cuatro.

1. **«Todos los nudos» de una tensión era cuadrático** (spec 005, `queries.all_nodes`): buscaba los
   materiales de cada nudo entre todas las claves. Tardaba 23 s con el caso 006 y 56 s con el 005,
   con la ventana quieta todo ese tiempo, igual que la línea de órdenes y MCP. Ahora se agrupan una
   vez, y el 006 tarda 0,10 s. Las filas son las mismas, bit a bit y en el mismo orden, que las de
   la forma anterior, escrita en el test como oráculo (`test_results_all_nodes_v0015.py`). Los tests
   de la interfaz usaban el túnel pequeño y no lo vieron.
2. **La paleta por defecto no era la de D5**: `ContourSettings.automatic` de OGR GUI da «Hot to
   cold», que es divergente y clara en el centro. Ahora todo contorno empieza con Viridis. Un test
   mide L\* (CIELAB, CIE 15:2004) y comprueba que crece con el valor en cada magnitud del catálogo, y
   que en la paleta que sustituye no crece. El panel «Lo que lo decidió» dice la paleta.
3. **Los números en pantalla no seguían D12.** La interpretación escribía siempre con punto: el valor
   bajo el cursor, las cifras de la leyenda, el rango y las consultas. Las casillas numéricas seguían
   la configuración regional de la máquina, no el idioma del programa, también en los diálogos de la
   parte C. Con la de España, una casilla de Qt mostraba coma y tomaba «2.5» como 25.

   Se puso primero la coma en español (`ad5aa34`), como pedía D12. **La propietaria modificó D12 el
   mismo día**: el separador decimal es siempre el punto, en inglés y en español, en pantalla y al
   escribir, porque la coma se presta a confusión y a errores. Una coma en un número se rechaza.
   Así queda:
   - `gui/units.py`, `number`, es el único sitio donde se escribe un número de pantalla, siempre
     con punto.
   - `DecimalBox` tiene el locale C y no tiene separador de miles («1.000» es 1). Muestra el punto
     en cualquier idioma y en cualquier máquina, y una coma no se deja escribir.
   - Las tablas de números (coordenadas, estratos, ventanas de la malla y factores por fase)
     rechazan una coma, diciendo la fila.
   - En español se ven las mismas cifras que en inglés, y la tabla CSV es la misma en los dos.

   En `ogr_ui` quedan dos cosas, que la propietaria corrige allí
   (`../Promts_desarrollo/2026_11_28_peticion_ogr_gui_coma_decimal.md`): el punto escrito de la
   barra de estado acepta la coma decimal, y las casillas del diálogo de contornos siguen la
   configuración de la máquina. Los tests de `read_point` de este programa son el contrato de la
   v0.1.3 y aceptan la coma. Cambiarán cuando suba la fijación.
4. **Las cifras de la tabla de una consulta iban a la izquierda**: ahora van a la derecha, y el
   texto a la izquierda.

Lo decidido de D15: el primer dibujo se mide en tres ventanas abiertas sobre los mismos resultados, y
vale el menor. El límite sigue en 1 s. Medido en esta máquina: [0,52; 0,50; 0,49] s, otra magnitud
0,33 s, un desplazamiento 0,33 s y moverse por debajo de 0,01 s. Una sola apertura llegaba a 1,1 a
1,3 s cuando otro programa cargaba la máquina; el changelog 0.2.13 de OGR-Core cuenta que una de
esas corridas era la de su sesión con la de este programa a la vez.

### La regla 7, opción a opción (parte D)

| Ventana o diálogo | Opciones | Test |
|---|---|---|
| Cálculo | calcular, cancelar (entre fases y matando el proceso), cerrar con un cálculo en marcha (no / sí), guardar antes, ir a los resultados | `test_gui_compute_v0015` |
| Interpretación: magnitud y fase | el selector del catálogo, las pestañas | `test_gui_interpret_v0015`, `test_the_catalogue_and_the_tabs`; `test_gui_cases_v0015` |
| Rango | esta fase, todas las fases, a mano; ajustar a los resultados | `test_the_range_and_the_absolute_value`, `test_fit_to_results_is_the_drawings_range` |
| Opciones de contorno | intervalos, paleta, modo (bandas, líneas, apagado, continuo) | `test_the_options` |
| Opciones de contorno (T37) | invertir, decimales, científico, opacidad | `test_reverse_decimals_scientific_opacity_and_the_mesh` |
| Valor absoluto, Vista > Malla | el campo y la leyenda; la malla encima | los dos de arriba |
| Unidades mostradas | el rango, la leyenda, las filas | `test_the_units_shown` (interpretación y consultas) |
| Consultas | línea y polilínea (n o sus vértices), contorno (n, distancia, lado), todos los nudos, por fases en un punto, gráfico, tabla, borrar las dibujadas | `test_gui_queries_v0015` |
| Informe | HTML, texto, leer otra vez | `test_gui_report_v0015` |
| Ayuda | página, caso (copiado y abierto), ficha | `test_gui_help_v0015` |
| Puente | token, apagarlo, Busy con un cálculo | `test_gui_bridge_v0015` |
| Idioma (D12, modificada) | el punto en pantalla en los dos idiomas, las casillas y las tablas rechazan la coma | `test_gui_decimal_v0015`; `test_gui_field_v0014` (un estrato con coma) |

Mutaciones en la T37: 14, todas cazadas. Fueron 6 en las opciones de contorno, con la del rango
dicho; 2 en «todos los nudos» (el orden, y la forma anterior, que cae por tiempo); la paleta
anterior; y 5 en D12, ya con el punto. Una sexta, quitar el separador de miles, era equivalente
con el locale C, y esa línea se quitó. Al principio escapó el mutante del rango: el test buscaba una «e» y la
encontraba en «stage». Ahora compara la cifra.

**Regla 12**: junto a lo dibujado van el estado de los resultados, quién los escribió y el motor;
también la cota B y las notas del mallador, lo que decide el resultado tal como se escribió y la
subdivisión, el rango, los intervalos y la paleta. Una consulta lleva su método y sus ajustes, con
los valores por defecto incluidos.

### La lista de la guía, componente a componente (parte D)

- **Acciones**: todas en un menú, con `tr()` y su español (los censos de las reglas 2 y 3 sobre
  las tres ventanas). Calcular e Interpretar se deshabilitan con su porqué: sin malla, malla de
  otra geometría, sin resultados.
- **Diálogos** (opciones de contorno, consulta en un contorno, número de puntos): el título dice qué
  se pide, la distancia va con su unidad, y el lado solo está habilitado con una distancia y dice
  por qué. Se prueban sin `exec()`.
- **Lienzo de resultados**: con el caso 005, el cursor y el zum por debajo de 0,01 s. El color de un
  punto es el de la leyenda, y las consultas se dibujan encima.
- **Proceso largo** (calcular): fase, escalón e iteración; Cancelar en dos tiempos (D9); la ventana
  nunca se queda quieta más de 0,25 s; un final con su resumen (en singular con una fase); un fallo
  que nombra la fase o el objeto del modelo.
- **Resultado**: la leyenda dice magnitud, unidad, convenio, fase, procedencia y rango, con Viridis
  por defecto. Lo que lo decidió va a la vista. Lo obsoleto, incompleto o cancelado se dice arriba,
  en la leyenda y en el título. Las tablas llevan cabecera, unidades y cifras a la derecha, y se
  exportan como la operación.
- **Mensajes**: los rechazos de las operaciones, con su código y en el idioma del lector. Un estado
  vacío dice qué hacer: «Sin resultados que mostrar…», «Analysis > Compute».
- *Pendiente, en `ogr_ui`*: el punto escrito y las casillas del diálogo de contornos, que aún
  aceptan la coma (arriba).

### Lo que se encontró en la parte D, en resumen

1. El progreso se lee, no se escucha: una fase que empieza y acaba entre dos lecturas se cuenta igual
   (T30).
2. El primer dibujo de una fase pasó de 3,9 s a 0,5 s sin cambiar ningún número. Fue en tres pasos:
   la recuperación más rápida (T31), la recuperación guardada al calcular, con la D6 de la 005
   modificada por la propietaria, y la huella más rápida (T36).
3. Una consulta que no se puede hacer se rechaza diciéndolo (T31, RF-7).
4. matplotlib dejaba sin pintar el máximo de un campo con el rango automático (T31).
5. Tres rojos de la CI que eran carreras entre leer el trabajo y su final, dos de los tests y uno
   del programa: la cancelación que acaba antes de su respuesta (tras la T34).
6. El congelado no podía ser el hijo de un trabajo: lo resuelve su punto de entrada, y hay una
   propuesta a OGR-Core (T36).
7. En la T37: «todos los nudos», cuadrático; la paleta de D5; los números de D12, siempre con
   punto; las cifras alineadas.

### Para otras sesiones, por la propietaria

- **OGR Slip2D**: dos propuestas, la paleta por defecto (D5) y los puntos relativos, polares y con
  coma (D10), en `../Promts_desarrollo/2026_11_28_propuestas_slip2d_paleta_y_puntos.md`.
- **OGR GUI**: la coma decimal en sus piezas (arriba). También la fila de este programa en su
  `docs/consumidores.md`, que pasa a v0.1.3.
- **OGR-Core**: la fila de este programa en su `docs/consumidores.md`, que pasa a v0.2.13, y la
  propuesta del congelado (T36).

**La CI** de `3ec4fc8` (run 46127528558), en verde: las ruedas, el congelado con la interfaz y la
suite con Python 3.11, 3.12 y 3.13 en Windows, macOS y Linux. La spec 006 y la fase 1 quedan
cerradas.

## El motor de Rust, por defecto (2026-11-28)

La propietaria preguntó por qué casi todo el código es Python si el motor iba en Rust. **Hallazgo**:
`analysis_run` tenía `variant="reference"` por defecto, y la ventana no le pasaba otro. La ventana,
la línea de órdenes y un agente calculaban con el motor de referencia en Python. El de Rust solo se
usaba si se pedía, como en los tests.

- Ahora el motor por defecto es Rust (`api/ops/analysis.py`, `DEFAULT_VARIANT`), también en el
  proceso hijo y en la línea de órdenes. El de referencia sigue a mano (`variant="reference"`,
  `--variant reference`) para comprobarlo. Los resultados dicen qué motor los escribió, en el `.h5`,
  en `results_open` y en el panel «Lo que lo decidió».
- Se comprueba que el cálculo de la ventana, el de la línea de órdenes y el de la operación sin
  argumentos los escribe Rust. Con la referencia pedida, los números son los mismos hasta el redondeo.
- Los casos 005 a 007 dan por las operaciones lo mismo, bit a bit, que `calculate` con el mismo
  motor. El test lo comparaba con el de referencia, y el 007 lo vio.
- Lo que tarda un cálculo entero con su `.h5`: el caso 005, 17.8 s → 13.2 s; el 006, 11.4 s → 8.3 s;
  el 007, 16.2 s → 5.0 s. El resto se va en lo que sigue en Python (ensamblar, factorizar, recuperar,
  escribir). Que eso pase a Rust es P4: queda en la fase 2, con la spec 011 y su medida A/B,
  confirmado por la propietaria y anotado allí y en el plan.
