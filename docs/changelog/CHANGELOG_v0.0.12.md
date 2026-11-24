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
