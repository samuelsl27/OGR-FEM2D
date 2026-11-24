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
asignación diciendo por qué, en vez de añadirla a ciegas. Espera el OK de la propietaria.
