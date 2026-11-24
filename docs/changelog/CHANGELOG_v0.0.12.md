# OGR FEM2D v0.0.12

**Fase 1, quinta parte: lo que falta sin Qt** (spec 006, parte A). Las ediciones del modelo como
funciones puras, los cortes entre contornos, los arcos y los círculos, el progreso del cálculo, el
informe y los triángulos para dibujar un campo. Nada de esto necesita la interfaz ni las piezas
comunes que se han pedido (ADR-0005). Este archivo cuenta lo que fue entrando, tarea a tarea.

## La spec, el plan y las tareas (2026-11-24)

Revisados contra el código, contra OGR Slip2D v0.1.486, OGR Data y el núcleo `v0.2.7`, y aprobados
con D1–D18 (`spec/features/006-interfaz-y-calculo/`). Lo que se encontró al revisarla:

- **Nadie había planeado extraer la interfaz**, y OGR Data ya copia a mano el aspecto, el `tr()` y
  el patrón de operaciones de Slip2D: la copia que diverge que P1 quería evitar ya existía.
- **Lo genérico de Slip2D es una parte pequeña**: unas 1 200 líneas sin Qt y unas 3 600 con él. La
  ventana, la interpretación y el lienzo (16 700 líneas entre los tres) mezclan el equilibrio límite
  con el `Project` del núcleo. Por eso el ADR-0005 lleva lo primero al núcleo y lo segundo a un
  paquete hermano, `ogr-gui`, y este programa escribe su ventana sobre esas piezas.
- **Slip2D no tiene entrada de arcos para los contornos**, y el modelo de aquí los tiene.
- **No había funciones para editar la geometría**: hasta ahora el modelo se construía entero.

La guía de interfaz (`spec/constitution/guia-de-interfaz.md`) entra en la constitución (D16). Las
dos peticiones de D1 están escritas fuera del repositorio (T1).

## T2 — las ediciones de los contornos y de sus vértices (2026-11-24)

`ogr_fem2d/model/edit.py`: añadir, borrar, renombrar, cambiar de tipo, cerrar o abrir, trasladar;
mover, insertar y borrar vértices; el arco y las divisiones de un segmento. Cada una es una función
pura, y por `Document.edit` es un paso de deshacer.

- **Un modelo a medio dibujar no es un modelo válido** (sin externo, una región sin material), y las
  ediciones no lo exigen: comprueban lo que reciben y lo que tocan, con las reglas del propio modelo,
  y dejan los problemas del conjunto a `model.problems`, que la interfaz listará. Las ediciones de
  fases de la spec 004 sí validan el modelo entero; se dejan como están.
- **La geometría compartida sigue compartida.** Un vértice se comparte por tener las mismas
  coordenadas (spec 004, D15). Moverlo lo mueve en todos los contornos que lo tienen, y con él los
  extremos de los tramos, las condiciones en vértice y las cargas puntuales que lo nombran. Insertar
  un vértice en un lado lo inserta en todos los contornos que tienen ese lado. Lo que separaría la
  geometría (trasladar un contorno que comparte un vértice, borrar un vértice junto a un lado
  compartido) se rechaza nombrando el otro contorno.
- **Nada cambia de forma ni desaparece sin pedirlo.** Mover o borrar el extremo de un arco se
  rechaza (habría que quitar antes el arco); un lado con divisiones forzadas no se parte; borrar un
  contorno o un vértice del que dependen condiciones o cargas se rechaza, salvo que se borre el
  contorno con sus dependientes, que es una opción con su test (regla 7).
- **Un arco se comprueba al ponerlo**: fuera de su circunferencia o con el centro sobre la cuerda,
  con la tolerancia de la regla `arc` del modelo.
- **La malla se queda**: una edición de la geometría la deja como malla de otra geometría, y
  calcular lo rechaza diciéndolo (spec 004, RF-11). La referencia la borraba (P10).

21 tests; 17 mutaciones, 17 cazadas (una, que aceptaba un punto de la recta fuera del segmento, se
escapaba al principio: el test lo pedía solo en un extremo, y ahora también más allá).

## T3 — los cortes entre contornos (2026-11-24)

`ogr_fem2d/model/cuts.py`: `cut(modelo, contorno)` pone un vértice donde el contorno se encuentra con
otro lejos de un vértice que compartan, en los dos, y devuelve cuáles ha puesto (RF-2; spec 004, D15).
Recto con recto, recto con arco y arco con arco; un arco cortado queda en dos arcos con el mismo
centro.

- **Un punto de encuentro junto a un vértice es ese vértice** (dentro de la tolerancia del mallador):
  en una T, el extremo exacto entra en el otro contorno; un cruce por un vértice que los dos ya tienen
  no pone nada. Así un corte nunca deja dos vértices casi juntos.
- **Un tramo en común se rechaza** nombrando los dos segmentos, como decía el plan; el mismo lado en
  dos contornos no es un tramo en común. **Propuesta para más adelante**: se podría resolver metiendo
  los extremos de cada uno en el otro, y quedaría un lado compartido, que el modelo ya admite. No se ha
  hecho sin preguntarlo.
- **Un lado con divisiones forzadas no se corta**: el error es el de `insert_vertex`, que nombra el
  contorno y sus divisiones.
- La aritmética es geometría analítica elemental (recta con recta, con circunferencia; dos
  circunferencias), sin fuente que citar: los tests la comprueban con la identidad de que cada punto
  está en los dos segmentos, también con dos circunferencias de radios distintos (con radios iguales
  un error de signo en la cuerda común no se veía).

9 tests; 10 mutaciones, 10 cazadas.

## T4 — arcos y círculos (2026-11-24)

`ogr_fem2d/model/shapes.py`: el arco por tres puntos, por inicio, centro y fin (en el sentido que se
pida) o por inicio, centro y ángulo; el círculo por centro y radio o por centro y punto; y `Drawn`, que
junta rectas y arcos en un contorno que se está dibujando (RF-3, D10).

- **Medio círculo o más son dos segmentos**, partidos por su punto medio, porque el segmento guarda el
  arco menor (spec 003, D4). Se parte desde un micro-radián por debajo de 180°, para que el centro quede
  bien lejos de la cuerda y la regla `arc` del modelo no lo rechace por redondeo.
- **El círculo son cuatro arcos de 90°**; con el inicio por defecto (desde +x) sus vértices son
  exactos, los del hueco del caso 005.
- **Un cuarto o media vuelta pone su vértice donde se dibuja**: cos(π/2) vale 6·10⁻¹⁷ en coma
  flotante, y un coseno o un seno a menos de 10⁻¹⁵ de 0 se toma como 0. Sin eso, la bóveda de un túnel
  dejaba su clave en (6·10⁻¹⁷, 1).
- Geometría analítica elemental, sin fuente que citar. Los tests la comprueban con identidades: cada
  vértice está en su circunferencia, y el área de un círculo de cuatro arcos, medida con las áreas de
  región del propio modelo, es π r² (y la de un túnel de suelo, hastiales y bóveda, 2 + π/2). Una
  mutación que movía un vértice del círculo sin sacarlo de la circunferencia se escapaba al área, que
  no cambia: ahora se miran también los ángulos de los vértices.

11 tests; 12 mutaciones, 12 cazadas.

## T5 — las ediciones de materiales, campo, condiciones, cargas y ajustes (2026-11-24)

En `ogr_fem2d/model/edit.py`: añadir, cambiar y borrar materiales; el campo; añadir, cambiar y borrar
condiciones y cargas; la condición por defecto del externo; los ajustes de la malla; el tipo de
análisis, las unidades y el resumen; los identificadores libres de lo nuevo (RF-1, RF-7).

- **Una edición se juzga por lo que rompe** (`model.refuse_new_problems`): se rechaza cuando añade un
  problema al modelo, no porque el modelo ya tuviera alguno. Así se edita un modelo a medio dibujar.
  **Las ediciones de fases y de asignaciones de la spec 004 pedían el modelo entero válido**, y en la
  interfaz no se habría podido, por ejemplo, insertar una fase antes de asignar todas las regiones:
  ahora usan la misma regla. Sus 15 tests siguen igual.
- **Un argumento que no existe se rechaza por su nombre** (un campo de un material, de una condición,
  de una carga, de los ajustes de la malla o del resumen), igual que un índice o un identificador que
  no existe.
- **Un material nuevo no tiene E ni ν hasta que se dan** (spec 004, D16). Lo nuevo que depende de las
  fases se escribe para todas: una restricción activa, un desplazamiento impuesto o una carga con
  factor 1. Un material que tiene una región no se borra.
- **Los ajustes de la malla se comprueban con las reglas del mallador**, y cambiarlos deja la malla,
  que pasa a ser de otros ajustes: calcular lo dice.

12 tests; 12 mutaciones, 12 cazadas (la del identificador libre de una fase se escapaba: con las fases
«1» y «2» las dos reglas dan «3»; ahora se prueba también con un hueco en la numeración).

### Anomalía encontrada, sin corregir (regla 6): asignar un material con la geometría a medias

`stages.assign_material` busca la región del punto con `regions.build`, que exige el modelo entero
válido. **Si la geometría tiene cualquier problema** (una región todavía sin material, un cruce), la
búsqueda falla, la función lo toma por «la región no tiene asignación» y **añade una asignación nueva
en el mismo punto**, en vez de cambiar la que hay. El modelo queda con dos asignaciones en una región
(`region_twice`). Viene de la spec 004 y ya pasaba antes de esta tarea; aquí se ve porque la interfaz
asigna regiones una a una.

Se propone: buscar la región con las caras del grafo, sin el paso de las asignaciones (una función
nueva de `regions`), y, si la geometría no deja encontrar las regiones (un cruce), rechazar la
asignación diciendo por qué, en vez de añadirla a ciegas.

**Corregida con el OK de la propietaria (2026-11-24).** Antes se miró si OGR Slip2D lo había
resuelto, porque allí también se asignan regiones: **allí no es un fallo, por diseño**. El núcleo
(`Project.assign_material_at`) añade cada clic a una historia, con la huella de la región en ese
momento; gana el último clic que cae dentro de una región, y una región sin ninguno toma el primer
material. Aquí la spec 004 (D15) decidió una asignación por región y ninguna por defecto, así que la
corrección es propia:

- `regions.region_of(modelo, punto)` busca la región con la geometría sola (los pasos 1 a 5 de
  `regions`, sin el de las asignaciones). Reasignar una región cambia su asignación, aunque otra siga
  sin material; una región sin asignación toma una nueva.
- **Se rechaza, diciendo por qué**: un punto sobre un contorno (también sobre un arco), que por la
  regla del número de vueltas caería de un lado sin que se vea; un punto fuera del modelo; una
  geometría en la que no se pueden encontrar las regiones (sin externo, con un cruce); una región que
  ya tiene dos asignaciones. Nunca una asignación a ciegas que cuente más tarde.
- Lo que Slip2D hace al partir una región ya asignada (las dos partes heredan el material de la
  huella) aquí no se hace: la parte nueva queda sin material y el modelo lo dice (D15).

6 tests; 7 mutaciones, 7 cazadas.

## T6 — lo que `calculate` cuenta mientras calcula (2026-11-24)

`calculate(…, progress=…)` avisa de cada paso: una fase empezada, terminada o fallida, y el final, con
el estado y las fases escritas (`results/calculate.py`, `Progress`; RF-9, D9). Es lo que el trabajo en
subproceso de la parte B escribirá en su archivo de progreso.

- **Se cuenta, no decide nada**: los resultados con `progress` son los del motor bit a bit, en un
  túnel de tres fases y en el caso 007 abierto desde su `modelo.ogrfem2d`. Los casos 005 y 006 pasan
  por el mismo bucle en sus tests de la spec 005, que siguen dentro de su tolerancia. Los 003 y 004 no
  pasan por `calculate`.
- **Una fase terminada dice si se resolvió**, sus escalones y su última iteración, los de su resultado.
  Al escribir el test se vio que **una fase que no cambia nada no se resuelve** (spec 002): la primera
  del túnel, que es la tensión de campo en equilibrio, y una que repite la anterior; dan un escalón y
  ninguna iteración. Por eso el aviso lleva `solved`, y la interfaz podrá decir «sin cambios» en vez
  de «resuelta».
- Iteración a iteración, mientras una fase avanza, llega con la spec 007, cuando haya escalones.

6 tests; 8 mutaciones, 8 cazadas.

## T7 — el informe del modelo y de sus resultados (2026-11-24)

`ogr_fem2d/report/info.py`: `report(modelo, abiertos)` da sus secciones, y `to_text` y `to_html` las
escriben (RF-4, D17). Lo usarán la ventana del informe (parte D), la línea de órdenes y el servidor MCP
(parte B).

- Las secciones: el resumen, el análisis y las fases, el campo, los contornos, los materiales y sus
  asignaciones, las condiciones y las cargas fase a fase, la malla, **lo que decide el resultado** (todos
  los `deciding_values`, con su porqué, regla 12) y los resultados.
- **Dice el estado de lo que cuenta**: sin malla, malla de otra geometría o de otros ajustes, resultados
  que faltan, obsoletos o incompletos. Con resultados que no son válidos no da las reacciones por
  contorno: la malla puede ser otra.
- De la malla, además de sus ajustes: los nudos y los elementos, la cota B y el ángulo que garantiza, los
  peores ángulos, los nudos que el mallador añadió en cada segmento, si su terminación con arcos está
  probada y sus avisos. De cada fase: si se resolvió, el mayor desplazamiento, los extremos de σ1 y σ3 en
  los puntos y en los nudos, y las reacciones, en total y por contorno (spec 005, D14).
- Los valores, en las unidades que se muestran; los títulos, las etiquetas y las palabras fijas son el
  texto inglés que la interfaz pasará por `tr()` (regla 2).
- **Sus números se comprueban contra algo externo** (regla 1): en una columna de dos estratos con los
  lados en rodillos y una carga uniforme, la mayor tensión vertical es q + Σγh = 100 + 18·4 + 24·6 = 316
  kPa, en los puntos y en los nudos (el campo es lineal en cada estrato, y el T6 lo representa exacto); y
  las reacciones por contorno suman la total, 6320 kN por metro, que es el peso más la carga.

7 tests; 9 mutaciones, 9 cazadas.

## T8 — un campo listo para dibujar (2026-11-24)

`ogr_fem2d/results/drawing.py`: `field(vista, magnitud, nivel)` subdivide cada elemento activo en
triángulos y da a cada vértice nuevo su posición y su valor con las funciones de forma del propio
elemento (Z&T ec. 14.27, como las consultas de la 005); `value_range` da el rango de la leyenda
(RF-5, D11).

- **Subdivisión regular en coordenadas de área**: 2^nivel partes por lado, 4^nivel triángulos por
  elemento; nivel 2 por defecto (16). La posición pasa por la transformación isoparamétrica: la pared
  del hueco se dibuja sobre el lado cuadrático del T6, a menos de 10⁻⁵ del arco (dibujada recta, sus
  tramos de 10° entrarían hasta cos 5° = 0,9962).
- **Cada elemento con sus vértices**: el dibujo es continuo dentro de un material y conserva el salto
  en un contacto. Comprobado contra la solución cerrada (regla 1) en la columna de dos estratos con
  carga q: σyy = q + Σγh en todos los vértices, y σxx = K·(campo) + ν/(1 − ν)·q a cada lado del
  contacto, 86,06 arriba y 69,33 abajo.
- **El rango de la leyenda es el rango entero**, con los extremos: el de la fase, el de todas o el que
  se dé. **Cambia lo previsto en el plan**: el plan ponía aquí también los N intervalos, pero las
  bandas, la paleta y sus colores son de `ContourSettings` de Slip2D, que va a `ogr-gui` (ADR-0005);
  repetirlos aquí sería otra copia. Y **no se recorta a un percentil**, como hace Slip2D con sus
  factores de seguridad (el 98 %): aquí el pico de tensión en la pared de un túnel es justo lo que se
  busca. La interfaz tendrá que usar este rango, no el ajuste de `ContourSettings`.
- **Tiempos, caso 005** (26 518 T6 activos, nivel 2: 424 288 triángulos y 397 770 vértices): el primer
  campo de tensión de una fase, 1,12 s, casi todo la recuperación por parches, que se hace una vez por
  fase y tipo; los siguientes, 0,06 s; un desplazamiento, 0,05 s; el nivel 3 (1,7 millones de
  triángulos), 0,18 s. **El objetivo de D15 (cambiar de magnitud o de fase en 1 s) queda justo en la
  primera tensión de cada fase**; se vuelve a medir con la interfaz (T31).

10 tests; 11 mutaciones, 11 cazadas (una que desordenaba los índices de los triángulos se escapaba: no
había test que dibujara con ellos; ahora los triángulos tienen que cubrir el modelo una vez, 200 m²).

## T9 — el cierre de la parte A (2026-11-24)

- `docs/modelo/edicion.md`: las ediciones, los cortes, los arcos y lo que se rechaza, con un ejemplo que
  un test ejecuta para que la página no se aparte del código. (El plan la ponía en `docs/interfaz/`; va
  junto al formato del modelo, que es lo que edita.) **Al escribir el ejemplo se vio que una malla
  graduada no tiene número de nudos por defecto** (spec 003 no lo decidió, y la referencia usa 75): el
  diálogo de la malla (T25) tendrá que pedirlo, sin inventarlo.
- **Los casos 001 a 007, como estaban**: desde el cierre de la spec 005 (`9c366ff`) no ha cambiado nada
  en `ogr_fem2d/engine/` ni en `rust/`. El único cambio en el camino del cálculo es el bucle de
  `calculate` (T6), que da los números del motor bit a bit (túnel de tres fases y caso 007), y los casos
  005 a 007 siguen dentro de su tolerancia en sus tests de la spec 005.
- Las peticiones de la T1 (a OGR-Core y a la suite) están entregadas por la propietaria. La parte B
  empieza cuando la versión de OGR-Core esté etiquetada.

### Lo que se encontró en la parte A, en resumen

1. Las ediciones de fases de la spec 004 pedían el modelo entero válido: ahora se juzgan por lo que
   rompen (T5).
2. **`assign_material` con la geometría a medias añadía una asignación duplicada** (spec 004): reportada
   y corregida con el OK de la propietaria; Slip2D no la tiene, por otro diseño (T5).
3. Una fase que no cambia nada no se resuelve, y el aviso de progreso lo dice (T6).
4. Los intervalos y los colores de la leyenda son de `ogr-gui`; el rango, aquí y entero, sin el
   percentil de Slip2D (T8).
5. La primera tensión de cada fase del caso 005 tarda 1,1 s en dibujarse, casi todo la recuperación:
   justo en el objetivo de D15 (T8).
6. Un tramo en común entre dos contornos se rechaza; la alternativa del lado compartido queda propuesta
   (T3).
7. Una malla graduada no tiene número de nudos por defecto (T9).
