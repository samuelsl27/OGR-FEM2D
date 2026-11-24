# Editar un modelo

> Spec 006, parte A (RF-1 a RF-3). Código: `ogr_fem2d/model/edit.py`, `cuts.py`, `shapes.py`,
> `stages.py` y `regions.region_of`. Lo que se edita es el modelo de `docs/modelo/formato.md`.

Cada edición es una **función pura**: recibe un modelo y devuelve otro, sin tocar el que recibe. La
interfaz, la línea de órdenes y el servidor MCP las aplican con `history.Document.edit`, que hace de
cada una un paso de deshacer. Un script puede usarlas tal cual:

```python
from ogr_fem2d.model import cuts, edit, shapes, stages, translate
from ogr_fem2d.model import model as md

m = md.Model()
m = edit.add_boundary(m, md.EXTERNAL, ((-20, -20), (20, -20), (20, 20), (-20, 20)))
vertices, segments = shapes.circle((0.0, 0.0), 2.5)
m = edit.add_boundary(m, md.EXCAVATION, vertices, segments=segments)
m = edit.add_material(m, name="Roca", E=2.0e6, nu=0.25)
m = stages.assign_material(m, (10.0, 0.0), "m1")
m = stages.assign_material(m, (0.0, 0.0), "m1")
m = stages.set_excavated(m, (0.0, 0.0), "1", True)
m = edit.set_field(m, md.ConstantField(10000.0, 10000.0, 10000.0, 0.0))
m = edit.set_mesh_settings(m, boundary_nodes=60)   # the graded mesh has no default (spec 003)
m = translate.mesh(m)
```

## Qué se rechaza y por qué

Un modelo a medio dibujar no es un modelo válido (sin externo, una región sin material), y las
ediciones no lo exigen:

- **las de la geometría** (contornos, vértices, segmentos) comprueban el contorno que tocan con las
  reglas del propio modelo (`model._boundary_problems`): su tipo, sus vértices, el cierre, los
  atributos de sus segmentos y el eje en axisimetría;
- **las demás** (materiales, asignaciones, fases, campo, condiciones, cargas, unidades, análisis) se
  rechazan **cuando añaden un problema** al modelo (`model.refuse_new_problems`), no porque el modelo
  ya tuviera alguno.

Lo que se rechaza sale como `ModelError`, con un problema por cosa: la regla, dónde y por qué. Un
argumento que no existe (un campo de un material, de una carga, de los ajustes de la malla) o un
índice o un identificador que no existe se rechaza por su nombre.

## La geometría

| Función | Qué hace |
|---|---|
| `add_boundary(m, tipo, vértices, closed=None, segments=(), boundary_id=None, name="")` | Un contorno nuevo; cerrado por defecto si es externo o de excavación; el id, `next_id` (`ext1`, `mat1`, `exc1`, `stg1`…) |
| `delete_boundary(m, id, with_dependents=False)` | Lo borra; si tiene condiciones o cargas, se rechaza, salvo con `with_dependents`, que las borra con él |
| `rename_boundary`, `set_boundary_kind`, `set_closed` | El nombre, el tipo (uno abierto no puede ser externo ni de excavación), cerrar o abrir (el lado que se va se lleva sus atributos) |
| `translate_boundary(m, id, dx, dy)` | Lo traslada con sus centros de arco y lo que nombra sus vértices; se rechaza si comparte un vértice con otro |
| `move_vertex(m, punto, a)` | Mueve el vértice **en todos los contornos que lo tienen**, y con él los extremos de tramos, condiciones en vértice y cargas puntuales; se rechaza si ya hay un vértice allí o si es el extremo de un arco |
| `insert_vertex(m, id, segmento, punto)` | Un vértice sobre el segmento (o su arco), **en todos los contornos que tienen ese lado**; un arco queda en dos con el mismo centro; se rechaza en un lado con divisiones forzadas |
| `delete_vertex(m, id, índice)` | Los dos segmentos pasan a uno; se rechaza junto a un arco, un lado con divisiones o un lado compartido, y si un tramo, una condición o una carga lo nombran |
| `set_arc(m, id, segmento, centro)`, `set_divisions(…)` | El arco menor de un segmento (con sus dos extremos en la circunferencia y el centro fuera de la cuerda) y sus divisiones forzadas; `None` los quita |

Los contornos solo se tocan en vértices que comparten (spec 004, D15), y un vértice se comparte por
tener las mismas coordenadas. Por eso ninguna edición separa en silencio lo que está unido: o lo mueve
todo junto, o se niega y nombra el otro contorno.

**La malla se queda.** Una edición de la geometría o de los ajustes la deja como malla de otra
geometría, y calcular lo rechaza diciéndolo; se vuelve a mallar con `translate.mesh`.

## Los cortes

`cuts.cut(m, id)` pone un vértice donde el contorno `id` se encuentra con otro lejos de un vértice que
compartan, en los dos, y devuelve el modelo y la lista de lo que ha puesto (`Cut.added`: contorno y
punto). Recto con recto, con arco, arco con arco.

- En una T, el extremo entra exacto en el otro contorno; un cruce por un vértice que los dos tienen no
  pone nada. Un punto de encuentro a menos de la tolerancia del mallador de un vértice es ese vértice.
- **Un tramo en común se rechaza** nombrando los dos segmentos: no es un corte. El mismo lado en dos
  contornos sí está permitido.
- Un lado con divisiones forzadas no se corta.

Se llama después de añadir o mover un contorno: `cuts.cut(edit.add_boundary(m, …), id).model`.

## Arcos y círculos

Un segmento guarda el **arco menor** sobre su centro (spec 003, D3 y D4). `shapes` lo construye:

| Función | Qué da |
|---|---|
| `arc_three_points(inicio, por, fin)` | El arco del inicio al fin pasando por el punto del medio |
| `arc_by_centre(inicio, centro, fin, anticlockwise=True)` | Del inicio al fin sobre el centro, en el sentido pedido; el fin tiene que estar en la circunferencia |
| `arc_by_angle(inicio, centro, ángulo)` | Del inicio, girando el ángulo en grados (positivo, antihorario) |
| `circle(centro, radio, start_angle=0)`, `circle_through(centro, punto)` | Cuatro arcos de 90°; con el inicio por defecto, vértices exactos en centro + (r, 0), (0, r), (−r, 0), (0, −r) |
| `Drawn.start(p).line_to(q).arc_to(pieza)` | Rectas y arcos juntos; un arco que acaba en el primer vértice cierra el contorno. Sus `vertices`, `segments` y `closed` van a `add_boundary` |

Medio círculo o más sale en **dos segmentos**, partidos por su punto medio. Un cuarto o media vuelta
pone su vértice donde se dibuja (sin el 6·10⁻¹⁷ de cos π/2).

## Materiales, asignaciones y fases

| Función | Qué hace |
|---|---|
| `add_material(m, id=None, name=…, E=…, nu=…, unit_weight=…, initial_loading=…, color=…)` | Un material nuevo; **E y ν quedan sin valor hasta que se dan** (spec 004, D16), y la traducción al motor dice cuál falta |
| `set_material`, `delete_material` | Cambiarlo; borrarlo, solo si ninguna región lo tiene |
| `stages.assign_material(m, punto, material, stage_id=None, this_stage_only=False)` | La región del punto toma el material. Se busca con la geometría sola (`regions.region_of`): una región se asigna aunque otra siga sin material. Se rechaza en un punto sobre un contorno o fuera del modelo, si la geometría no deja encontrar las regiones (un cruce, sin externo) y en una región que ya tiene dos asignaciones |
| `stages.set_excavated`, `insert_stage`, `delete_stage`, `rename_stage`, `set_condition_active`, `set_condition_factor`, `set_load_factor` | Las de la spec 004: excavar, las fases y el estado de condiciones y cargas fase a fase; `next_stage_id` da un id libre |

Una región tiene una asignación y ninguna por defecto (spec 004, D15). OGR Slip2D lo hace de otro
modo: allí cada clic se añade a una historia, gana el último y una región sin asignar toma el primer
material.

## Campo, condiciones, cargas y ajustes

| Función | Qué hace |
|---|---|
| `set_field(m, campo)` | `ConstantField` o `GravityField` con sus estratos; compresión positiva |
| `add_condition(m, tipo, span=None, vertex=None, ux=None, uy=None, name="")` | Una restricción (`x`, `y`, `xy`) o una liberación (`free`) activa en todas las fases, o un desplazamiento impuesto con factor 1 en todas |
| `set_condition`, `delete_condition`, `set_default_restraint` | Cambiarla, borrarla; la condición del externo donde no se dice otra cosa |
| `add_distributed_load(m, span, inicio, fin=None, orientation=NORMAL, angle=0, name="")`, `add_point_load(…)` | Una carga con factor 1 en todas las fases; la repartida es uniforme si no se da el fin |
| `set_load`, `delete_load` | Cambiarla, borrarla |
| `set_mesh_settings(m, **cambios)` | Los ajustes del mallador, comprobados con sus reglas |
| `set_analysis`, `set_units`, `set_summary` | El tipo de análisis (rechazado si la geometría no lo admite), el sistema de unidades que se muestra (los valores no cambian) y el resumen |
