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
