# El modelo y su archivo `.ogrfem2d`

> Spec 004 (RF-1 a RF-16) y ADR-0004. Código: `ogr_fem2d/model/`. Es lo que el ingeniero define, lo
> que se guarda y cómo se traduce a la entrada del mallador (`docs/malla/entrada.md`) y a la del motor
> (`docs/motor/entrada.md`).

El modelo es un **valor**: dataclasses congeladas (`model.Model`). Cada edición da un modelo nuevo, y
deshacer es volver al anterior (`history`). No hay Qt: se usa desde scripts, tests, la línea de
órdenes y el servidor MCP.

## Convenios

| Qué | Convenio | De dónde |
|---|---|---|
| Unidades | se guarda siempre en **m, kN, kPa y kN/m³**; `units` es solo el sistema que se muestra, de la lista del núcleo (`ogr_core.units`), y uno desconocido es un error. El motor recibe kPa | D5 |
| Tensión de campo | **compresión positiva**, como la escribe el usuario | D6 |
| Carga normal | **positiva cuando empuja hacia el terreno**, es decir, hacia el elemento activo del lado cargado | D6; D08 del análisis de interfaz |
| Otras orientaciones de carga | las del núcleo (`LoadOrientation`), positivas según su dirección: vertical (0, −1), horizontal (1, 0), ángulo desde la horizontal (cos a, sen a), ángulo al contorno (la tangente del tramo, en su sentido, girada a en sentido antihorario) | D6 |
| Desplazamientos | según +x y +y, como el motor | D6 |
| Cambio de signo | en un único sitio, `model/conventions.py`: la tensión de campo (por `engine/initial_stress.py`, que recibe compresión positiva) y la carga normal (el motor la quiere positiva hacia fuera del elemento) | RF-8, regla 10 |
| Fases | lista ordenada; cada una con **id estable** y nombre. Lo que depende de la fase se guarda una vez por fase, en el orden de las fases, y en el archivo como objeto con clave el id de la fase | D10 |
| Totales | carga y desplazamiento impuesto de cada fase = factor × valor; un factor 0 anula una carga; un factor `null` hace que un desplazamiento impuesto no actúe en esa fase | D10; spec 001, D2 |
| Axisimetría | x es el radio; el modelo está en x ≥ 0; una carga puntual es la del **anillo entero** | spec 002, D1 y D2 |
| Vértices | se nombran por sus coordenadas, que son exactas: una carga o una condición no dependen del orden de los vértices | — |

## Las piezas del modelo

### Contornos (`Boundary`)

| Campo | Qué es |
|---|---|
| `id`, `name` | identificador único y nombre |
| `kind` | `external` (uno, cerrado), `material` (abierto o cerrado), `excavation` (cerrado) o `stage` (abierto o cerrado: el que parte una región para excavarla por partes) |
| `vertices`, `closed` | los vértices en orden y si se cierra (sin repetir el primero) |
| `segments` | `SegmentAttr(index, arc, divisions)`, solo para los segmentos con algún atributo: el segmento `index` va del vértice `index` al siguiente; `arc` es el centro del arco menor (spec 003, D3 y D4); `divisions`, las divisiones forzadas (spec 003, D10) |

Los contornos **solo se tocan en vértices que comparten** (D15). Un tramo (`Span(boundary, start,
end)`) va del vértice `start` al `end` hacia delante en el orden de los vértices del contorno (dando
la vuelta en uno cerrado); con los dos a `None` es el contorno entero.

### Materiales, asignaciones y fases

| Pieza | Campos |
|---|---|
| `Material` | `id`, `name`, `color`; `E` y `nu` (elástico isótropo, D9; `None` hasta que se den, D16); `unit_weight`; `initial_loading` (D11, abajo) |
| `Stage` | `id`, `name` |
| `Assignment` | `point` (dentro de la región), `material` (el de la región en todo el cálculo, el estado inicial incluido) y `excavated`, una bandera por fase |

**Carga inicial** (`initial_loading`, D11):

| Modo | Tensión inicial | Peso propio | Por defecto |
|---|---|---|---|
| `field_stress` | el campo | no | con campo constante |
| `field_stress_and_body_force` | el campo | γ del material | con campo gravitatorio |
| `body_force` | ninguna | γ del material | — |
| `none` | ninguna | no | — |

### Tensión de campo

- `ConstantField(sigma_1, sigma_3, sigma_z, angle)`: σ1 ≥ σ3 en el plano, σz fuera, ángulo de σ1
  desde x en sentido antihorario, en grados (JCZ 2007, ecs. 2.28–2.30).
- `GravityField(surface, strata)`: superficie horizontal y estratos horizontales, cada uno con su cota
  inferior, γ, K y Kz (JCZ 2007, ecs. 13.1 y 13.5; spec 002, D3). La superficie real del terreno es de
  la spec 009 (D14).

En axisimetría el campo tiene que estar en equilibrio radial: K = Kz, y en el constante σr = σθ y
τrz = 0 (spec 002, enmienda de D3).

### Condiciones (`Condition`)

| Campo | Qué es |
|---|---|
| `kind` | `x`, `y`, `xy` (restringido), `free` (liberado) o `displacement` (impuesto) |
| `span` o `vertex` | dónde, uno de los dos |
| `active` | restricciones: si actúa en cada fase |
| `ux`, `uy`, `factors` | desplazamiento impuesto: los valores (`None`, la componente no se impone) y el factor de cada fase |

`Model.default_restraint` (por defecto `xy`, escrito siempre) es la condición del contorno externo
donde no se dice otra cosa. Cómo se llevan a los nudos, en «La traducción».

### Cargas

| Pieza | Campos |
|---|---|
| `DistributedLoad` | `span`; `start_value`, `end_value` (kN/m, lineal en la longitud del tramo); `orientation`, `angle`; `factors`; `name` |
| `PointLoad` | `vertex`; `magnitude` (kN, o kN/m en deformación plana); `orientation` (vertical, horizontal o ángulo desde la horizontal), `angle`; `factors`; `name` |

### Malla

`mesh_settings` son los `MeshSettings` del mallador (spec 003). `mesh` es la malla guardada (D3):
`nodes`, `elements`, `element_region` (la **región** de cada elemento, no el material), `boundaries`
(el mapa segmento → nudos y lados del mallador), `notes`, `warnings` y `source`, la huella de la
entrada del mallador de la que salió.

## El archivo `.ogrfem2d`

JSON en UTF-8, con estas secciones en este orden (`ogr_file.to_dict`). Todas las claves se escriben
siempre (`null` cuando no hay nada).

| Sección | Qué lleva |
|---|---|
| `format`, `format_version`, `written_by` | `"ogr-fem2d"`, `1`, el programa y su versión |
| `summary` | `title`, `author`, `date`, `notes` |
| `units` | el id del sistema que se muestra |
| `analysis` | `plane_strain` o `axisymmetric` |
| `boundaries` | `id`, `kind`, `name`, `closed`, `vertices` (`[x, y]`), `segments` (`index`, `arc`, `divisions`) |
| `materials` | `id`, `name`, `color`, `E`, `nu`, `unit_weight`, `initial_loading` |
| `stages` | `id`, `name` |
| `assignments` | `point`, `material`, `excavated` (`{id de fase: true/false}`) |
| `field_stress` | `{"kind": "constant", sigma_1, sigma_3, sigma_z, angle}` o `{"kind": "gravitational", surface, strata: [{bottom, unit_weight, k, kz}]}` |
| `default_restraint` | `x`, `y`, `xy` o `free` |
| `conditions` | `kind`, `name`, `span` (`{boundary, start, end}` o `null`), `vertex`, `active` (`{id: bool}`, o `null` en un impuesto), `ux`, `uy`, `factors` (`{id: número o null}`, o `null` en una restricción) |
| `loads` | `{"type": "distributed", name, span, start_value, end_value, orientation, angle, factors}` o `{"type": "point", name, vertex, magnitude, orientation, angle, factors}` |
| `mesh_settings` | `kind`, `nodes_per_element`, `quality_bound`, `boundary_nodes`, `max_size`, `size`, `elements`, `windows` (`[{polygon, size}]`) |
| `mesh` | `null`, o `source`, `nodes`, `elements`, `element_region`, `boundaries` (`[{name, nodes, sides, mids}]`), `warnings`, `notes` |

**Escritura** determinista: un objeto con una clave por línea, una lista de números en una línea y
una lista de esas listas una por línea (vértices, nudos y elementos: el archivo se puede comparar con
git). Los números como los escribe Python (el texto más corto que se lee como el mismo número), así
que escribir lo leído da los mismos bytes.

**Lectura** estricta (`ogr_file.read`): una clave que falta, una que sobra (de una versión posterior
o un error), un valor de otro tipo o un `format_version` posterior son un `FileFormatError` que los
nombra, todos a la vez. Nada se pierde en silencio. Después, el modelo pasa sus propias reglas.

## La traducción

### Al mallador (`translate.to_mesh_input`)

`regions.build` resuelve la geometría:

1. **puntos**: cada vértice una vez, en el orden de los contornos y de sus vértices;
2. **segmentos**: cada lado una vez; el mismo lado en dos contornos es uno (con arcos o divisiones
   distintos, error). Los de un contorno de excavación se marcan para la malla graduada;
3. **cruces**: con los predicados del mallador (exactos en los rectos, analíticos en los arcos);
4. **caras** del grafo plano, recorriendo cada medio lado con la cara a su izquierda y tomando en cada
   vértice el siguiente lado en sentido horario (en un arco cuenta su tangente; dos tangentes iguales,
   por la curvatura). Un recorrido que pasa dos veces por un vértice se parte en anillos simples;
5. **regiones**: los anillos antihorarios son contornos de región; los horarios, huecos (de su propia
   cara, o el anillo exterior de otro grupo de contornos, hueco de la menor región que lo contiene). El
   grupo que nada contiene es el del externo, y su anillo exterior tiene que ser exactamente él;
6. **asignaciones**: una por región, ni más ni menos (D15).

El orden es canónico: los anillos empiezan en su menor índice y las regiones se ordenan por su
contorno. En el `MeshInput`, la «material» de cada región es **el índice de la región**: la malla no
depende de los materiales (D3).

### Al motor (`translate.to_engine`)

- La malla guardada, que tiene que ser de este modelo: su `source` es la huella del `MeshInput` de
  ahora. Cambiar la geometría o los ajustes de malla la deja como de otro modelo (RF-11); cambiar un
  material, una fase, una condición o una carga, no.
- Un material del motor por cada material del modelo, en su orden; el de cada elemento, el de la
  asignación de su región. La tensión inicial y el peso propio, según el modo de carga inicial (D11);
  si ningún punto empieza con tensión, el motor recibe `None`.
- Por fase: los elementos activos (los de las regiones no excavadas), las condiciones y las cargas.
  Los ajustes del solver son los del motor (D9).

**Condiciones a nudos** (`conditions.py`, D16):

1. cada segmento toma la unión de las restricciones de los tramos que actúan sobre él en la fase; un
   `free` no aporta nada pero dice que el segmento tiene condición; un segmento del externo sin ninguna
   toma `default_restraint`;
2. cada nudo (esquinas e intermedios de los segmentos en la malla) toma la unión de sus segmentos:
   liberar un segmento no suelta la esquina del vecino (P14:82);
3. una condición de vértice sustituye, en su nudo, lo que dieron los segmentos;
4. desplazamientos impuestos: primero los de tramos, después los de vértices, que los sustituyen; dos
   valores distintos del mismo grado de libertad en el mismo nivel, error; una componente impuesta
   sustituye a la restricción de esa componente.

**Cargas a lados y nudos** (`loads.py`): una carga repartida, lineal en la longitud a lo largo del
tramo, da un `EdgeLoad` por lado de la malla, sobre el **único** elemento activo de ese lado en la
fase (ninguno o dos, error). La normal va con `normal=True` y el signo cambiado; las demás, en
componentes globales en cada esquina. Una carga puntual da un `NodalLoad` en el nudo del vértice.

## Lo que decide el resultado (`translate.deciding_values`)

La lista de cada valor que decide el resultado y no se dibujó (regla 12): las unidades (y que el
sistema mostrado no cambia los valores), el tipo de análisis, la condición por defecto del externo, la
carga inicial de cada material, cada ajuste de la malla, los ajustes del solver que la traducción toma
del motor (D9) y, en axisimetría con cargas puntuales, que son las del anillo entero. Los resultados
(spec 005) la llevarán con ellos.

## Huellas (`fingerprint.py`)

SHA-256 de un JSON canónico (claves ordenadas, separadores fijos, ASCII, sin NaN ni infinitos).

- **Del modelo**: el contenido del archivo sin `format`, `format_version`, `written_by`, `summary`,
  `units`, los nombres, los colores, ni las notas y avisos de la malla, y con los ids de contornos,
  materiales y fases cambiados por su lugar (su orden es parte del modelo): renombrar un id en todas
  partes no la mueve. Cambia con todo lo que cambia el resultado, malla incluida, y con nada más
  (RF-16, ADR-0003).
- **Del documento**: todo menos `written_by`.

## Abrir otros formatos

- **`.ogr` de OGR Slip2D** (`import_slip2d.open_slip2d`, D16): las regiones que resuelve el núcleo
  convertidas en contornos que se tocan en vértices compartidos. Se traen los materiales (sin E ni ν),
  las asignaciones y las cargas (con vértices insertados). Las restricciones son las de la
  referencia: laterales y fondo fijos, superficie libre. El informe (`Report`) dice qué se trajo, qué
  no, qué se puso por defecto y qué se cambió.
- **DXF** (`import_dxf.boundaries_from_dxf`, D13): las polilíneas del lector del núcleo, por capa, en
  los cuatro tipos de contorno. El lector aplana los arcos, y el informe lo dice.

## Reglas

| Regla | Qué rechaza | Dónde |
|---|---|---|
| `analysis`, `units` | un tipo de análisis o un sistema de unidades que no existe | `model` |
| `boundary`, `boundary_id`, `segment_attr` | contorno de tipo desconocido, sin cerrar cuando debe, con pocos vértices o repetidos; id vacío o repetido; atributo de un segmento que no existe, dado dos veces o vacío (regla 7) | `model` |
| `external` | ningún contorno externo, o más de uno | `model` |
| `left_of_axis` | en axisimetría, un vértice con x < 0 | `model` |
| `material`, `material_id` | E ≤ 0, ν fuera de (−1, 0.5), γ < 0, modo de carga inicial desconocido; id vacío o repetido | `model` |
| `stage` | ninguna fase; id vacío o repetido | `model` |
| `assignment`, `reactivated` | material que no existe, banderas que no son una por fase; una región excavada que vuelve (RF-4) | `model` |
| `field` | σ1 < σ3, estratos que no bajan, valores negativos; un campo que el preproceso rechaza | `model`, `field` |
| `default_restraint`, `condition` | condición por defecto desconocida; condición sin sitio o con dos, en un tramo o vértice que no existe, con banderas o factores que no le corresponden (regla 7) | `model` |
| `load` | tramo o vértice que no existe, orientación desconocida (o normal en una puntual), ángulo que no hace nada (regla 7), factores que no son uno por fase | `model` |
| `mesh` | una malla guardada mal formada | `model` |
| `arc`, `segment_conflict`, `crossing`, `dangling`, `outside_external`, `region_unassigned`, `region_twice`, `assignment_outside` | arco que no es arco; el mismo lado con atributos distintos; contornos que se cortan fuera de un vértice compartido; extremo suelto; contornos fuera del externo; región sin asignación o con dos; asignación fuera de toda región | `regions` |
| `material_change` | cambiar el material de una región entre fases (RF-4) | `stages` |
| `mesh`, `mesh_stale`, `material_incomplete`, `condition_conflict`, `condition_inactive`, `load_not_on_boundary` | sin malla; malla de otro modelo (RF-11); material sin E o ν (D16); dos impuestos distintos en un grado de libertad; impuesto en un nudo sin elementos activos; carga sobre un lado sin un único elemento activo (RF-10) | `translate`, `conditions`, `loads` |
| `format`, `format_version`, `key`, `type` | no es un `.ogrfem2d`; versión posterior; clave que falta o sobra; valor de otro tipo | `ogr_file` |

Los errores del mallador y del motor se reescriben con los nombres del modelo: el contorno y el
segmento, el vértice, la región por su asignación, el material y la fase (RF-12). El original va
detrás, entre corchetes.
