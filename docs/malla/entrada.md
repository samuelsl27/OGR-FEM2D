# Entrada del mallador

> Spec 003, RF-1. Código: `ogr_fem2d/mesh/geometry.py`; tests: `tests/test_mesh_input_v008.py`. Es
> lo que el modelo (spec 004) tiene que entregar al mallador. La salida se documentará aquí cuando
> exista (T9 y T12).

El mallador recibe una **geometría** (puntos, regiones de material, atributos de los segmentos) y los
**ajustes de la malla**. No sabe de menús ni de unidades de usuario: las longitudes llegan en las
unidades coherentes que elija quien llama, las mismas del motor (`docs/motor/entrada.md`).

## Convenios

| Qué | Convenio | De dónde |
|---|---|---|
| Puntos | se comparten por índice: dos regiones que se tocan usan el mismo punto, y el lado entre dos puntos es un solo segmento de las dos | conformidad de la malla |
| Contorno de una región | en sentido **antihorario**; sus huecos, en sentido **horario** | el de `MaterialRegion` de `ogr_core` |
| Segmento | el lado entre dos puntos consecutivos de un anillo | — |
| Segmentos que se tocan | **solo en un extremo que compartan** | Shewchuk (2002a), §1, pág. 1: la definición del grafo plano (PSLG) que malla el refinado de Delaunay |
| Arco | el **arco menor** de la circunferencia de centro dado que pasa por los dos puntos del segmento: el del lado de la cuerda opuesto al centro, de menos de 180° | spec 003, D3 y D4 |
| Excavación | una región como las demás, que se malla; sus segmentos se marcan como de excavación para la malla graduada | spec 003, D5; el programa de referencia malla siempre el interior de las excavaciones |
| Axisimetría | el eje es x = 0 y el modelo está en x ≥ 0, arcos incluidos | spec 002, D1 |

## La entrada: `MeshInput`

| Campo | Qué es |
|---|---|
| `analysis` | `"plane_strain"` o `"axisymmetric"` |
| `points` | coordenadas (x, y) de cada punto; el índice es el número del punto. Un punto que no está en ningún anillo es un **punto suelto**: tiene que caer dentro de una región y será un nudo de la malla |
| `regions` | `Region(outline, holes, material)`: el contorno y los huecos como tuplas de índices de puntos, y el índice del material, que pasa a todos sus elementos |
| `segments` | `SegmentSpec(a, b, arc, divisions, excavation)`, solo para los segmentos que tienen algún atributo: `Arc(centre)`, un número de divisiones forzado (D10) y si limita una excavación |
| `settings` | `MeshSettings`, abajo |

## Los ajustes: `MeshSettings`

Todos **cambian la malla**, y la malla dirá con cuáles se hizo (regla 12). Un ajuste que no sirve
para el tipo de malla elegido se rechaza, no se ignora (regla 7).

| Campo | Por defecto | Qué es |
|---|---|---|
| `kind` | `"graded"` | `"graded"` (graduada) o `"uniform"` (uniforme). La malla radial (D8) no sale de una geometría y tiene sus propios ajustes |
| `nodes_per_element` | 6 | 3 o 6 |
| `quality_bound` | √2 | la cota B del cociente circunradio / lado más corto de cada triángulo. Con √2, ningún ángulo menor de 20.7° (Shewchuk 2002a, §2, pág. 5); el refinado termina con B ≥ √2 (teorema 4, pág. 16); por debajo, se rechaza. La graduación solo está garantizada con B > √2 (teorema 8, pág. 23; spec 003, RF-5) |
| `boundary_nodes` | — | graduada: los nudos que se reparten entre los segmentos de excavación, o entre los del contorno exterior si no hay excavación (D5). Los segmentos con divisiones forzadas no entran en el reparto |
| `max_size` | sin cota | graduada: cota opcional de la longitud de cualquier lado |
| `size` | — | uniforme: cota de la longitud de cualquier lado |
| `elements` | — | uniforme: número aproximado de elementos, del que sale `size` (D5); uno de los dos |
| `windows` | ninguna | `Window(polygon, size)`: zonas, de cualquier polígono, cuyos elementos no pasan de `size` (D9) |

## Lo que se deriva de una entrada válida

- `segments(m)`: cada segmento una vez, en el orden en que aparece recorriendo los anillos (región a
  región, contorno y después huecos), con sus atributos y los anillos que lo usan. Un segmento de un
  solo anillo está en el contorno exterior del dominio mallado. La misma entrada da el mismo orden
  (D11).
- `graded_targets(segmentos)`: los segmentos que reciben `boundary_nodes`.
- `region_area(m, r)`: el área exacta de una región, con sus arcos y sus huecos.

## El paso 1: la discretización

`discretize(m)` (`ogr_fem2d/mesh/discretize.py`) valida la entrada y devuelve los nudos de cada
segmento, que se pueden ver antes de mallar (RF-2). El refinado los conserva todos y puede añadir
más en un segmento cuando lo necesita (RF-3, D10).

| Caso | Divisiones de un segmento |
|---|---|
| Divisiones forzadas (`SegmentSpec.divisions`) | esas (D10) |
| Malla graduada, segmentos de excavación (o del contorno exterior si no hay excavación) | `boundary_nodes` repartidas en proporción a la longitud (la del arco en los arcos): cada uno recibe la parte entera de lo suyo, al menos una, y las que quedan van a los mayores restos, con los empates al primero; la suma es exacta (D5) |
| Malla graduada, los demás segmentos | una: entran con sus extremos y el refinado gradúa |
| Malla uniforme | ⌈L/h⌉, la menor con la que ningún trozo pasa de h; con `elements` = N, h² = 4A/(√3 N), el área A del dominio cubierta por N triángulos equiláteros (D5) |

Los nudos de un segmento recto están a distancias iguales; los de un arco, a ángulos iguales del
arco menor, sobre la circunferencia. Los extremos son los puntos de la entrada, compartidos con los
segmentos que llegan a ellos, y los nudos nuevos se numeran después de los puntos de la entrada,
segmento a segmento en el orden de `segments(m)`: la misma entrada da los mismos nudos (D11). Las
ventanas no se miran aquí: son cotas del refinado. La h de una malla uniforme va con el resultado
(`Discretization.size`, regla 12).

## Reglas de validación

`validate()` lanza `MeshInputError` con **todos** los problemas a la vez; cada uno (`Problem`, el
mismo del motor) dice la regla, el sitio (punto, región y anillo, segmento, ventana o ajustes) y por
qué. Los segmentos rectos se comprueban con aritmética exacta (un número de coma flotante es un
racional); los arcos, de forma analítica, con una tolerancia relativa de 10⁻⁹ por la diagonal del
modelo. Si hay errores de índices, de puntos o de atributos, no se miran la orientación ni los
cruces; si dos segmentos se cortan, no se miran huecos, solapes ni puntos sueltos, que dependen de que
no se corten.

| Regla | Qué rechaza | Por qué |
|---|---|---|
| `analysis` | un tipo de análisis que no es deformación plana ni axisimetría | el motor solo tiene esos dos |
| `points` | menos de tres puntos, o uno que no son dos números finitos | — |
| `duplicate_point` | dos puntos en el mismo sitio | dos regiones que se tocan allí no compartirían el punto y la malla no sería conforme |
| `left_of_axis` | en axisimetría, un punto con x < 0 o un arco que llega a x < 0 aunque sus extremos no | el eje es x = 0 |
| `no_region` | ninguna región | — |
| `ring` | un anillo de menos de tres puntos, con puntos que no existen o con un punto repetido | — |
| `material` | un material que no es un índice ≥ 0 | — |
| `shared_edge` | un segmento en más de dos anillos, o en dos que lo recorren en el mismo sentido | dos regiones que se tocan lo recorren en sentidos opuestos; en el mismo, se solapan |
| `unknown_segment` | atributos de un par de puntos que no es lado de ningún anillo | — |
| `segment_twice` | atributos del mismo segmento dados dos veces | ¿cuál vale? |
| `divisions` | un número de divisiones que no es un entero ≥ 1 | — |
| `arc` | un centro no finito, puntos a distinta distancia del centro, o el centro sobre la cuerda (medio círculo o más) | el arco es el menor; uno de 180° o más se parte con un punto (D4) |
| `orientation` | un contorno que no va en sentido antihorario o un hueco que no va en sentido horario (por el área exacta, arcos incluidos) | el convenio de `ogr_core`; sin él no se sabe de qué lado está la región |
| `crossing` | dos segmentos rectos que se cortan, se solapan, o un punto de uno en el interior de otro (una unión en T) | Shewchuk (2002a), §1 |
| `arc_crossing` | un arco que corta o toca otro segmento lejos de sus extremos compartidos | lo mismo, con el arco como arco y no como su cuerda |
| `hole` | un hueco fuera de su contorno o que se solapa con otro hueco de la misma región | — |
| `overlap` | un segmento de una región dentro de otra (una región dentro de otra sin ser su hueco, o solapadas) | cada punto del dominio, en una sola región |
| `loose_point` | un punto suelto fuera de toda región, o sobre un segmento | sobre un segmento sería una unión en T |
| `element_kind` | elementos que no son de 3 ni de 6 nudos | los del motor |
| `mesh_kind` | un tipo de malla que no es graduada ni uniforme | — |
| `quality_bound` | B < √2 o no finita | sin garantía de que el refinado termine (RF-9) |
| `graded_nodes` | graduada sin `boundary_nodes`, con menos nudos que segmentos que los reciben, o con `boundary_nodes` cuando todos tienen sus divisiones forzadas; uniforme con `boundary_nodes` | cada segmento necesita al menos una división; un valor que no hace nada se rechaza (regla 7) |
| `max_size` | una cota que no es una longitud > 0, o una cota máxima en una malla uniforme | regla 7 |
| `uniform_size` | uniforme sin `size` ni `elements`, con los dos, o con un valor no válido; graduada con alguno de ellos | regla 7 |
| `window` | una ventana de menos de tres puntos, sin área, que se corta a sí misma o con un tamaño no válido | — |

## Cómo se decide si un punto está dentro

El número de vueltas del anillo alrededor del punto: el de las cuerdas (regla de cruces de Sunday,
exacta para cualquier polígono), corregido por cada arco cuyo segmento circular contiene el punto.
El lazo «arco de a a b, cuerda de b a a» rodea ese segmento en sentido antihorario si el arco se
abomba a la derecha de a → b, y suma +1; en sentido horario si se abomba a la izquierda, y resta 1.
Por eso un punto entre un arco que entra en la región y su cuerda queda fuera, aunque esté dentro
del polígono de las cuerdas. Con la misma cuenta, el área de un anillo es la de las cuerdas más o
menos R²/2 (θ − sen θ) por arco.
