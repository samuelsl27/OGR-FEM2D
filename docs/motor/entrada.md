# Entrada del motor

> Spec 002, RF-1 y RF-2. Código: `ogr_fem2d/engine/model.py`; tests:
> `tests/test_engine_input_v002.py`. Es lo que el modelo (spec 004) tiene que entregar al motor.

El motor recibe **datos discretos** (regla 11 de `AGENTS.md`): nudos, elementos, materiales,
tensiones iniciales y fases. No sabe de contornos, menús ni unidades de usuario: todos los números
llegan en **un único sistema coherente de unidades** que elige quien llama (por ejemplo m, kN, kPa y
kN/m³), y la conversión desde las unidades del usuario se hace en un solo sitio, fuera del motor.

## Convenios

| Qué | Convenio | De dónde |
|---|---|---|
| Signo de las tensiones | **tracción positiva** | spec 001, D1 |
| Vector de tensiones | (σxx, σyy, σzz, τxy) | spec 001 |
| Axisimetría | x es el radio r, y es el eje z; σzz es la circunferencial σθθ; el eje es x = 0 y el modelo está en x ≥ 0 | spec 002, plan, «Convenio» |
| Gravedad | según −y, con el peso específico de cada material | — |
| Cargas y desplazamientos impuestos | **en totales**: el estado al final de la fase, no lo que añade | spec 001, D2 |
| Fuerzas en axisimetría | las del **anillo entero** (2π r por la fuerza por unidad de longitud de circunferencia) | spec 002, D2; Zienkiewicz y Taylor (2000), §5.2.6 |
| Orden de los nudos de un elemento | esquinas en sentido **antihorario**; en el T6, después los nudos de los lados: el lado k va de la esquina k a la k + 1 (módulo 3) y su nudo intermedio es el k + 3 | Zienkiewicz y Taylor (2000), §4.2.1 |

## El modelo: `EngineModel`

| Campo | Qué es |
|---|---|
| `analysis` | `"plane_strain"` (deformación plana) o `"axisymmetric"` |
| `nodes` | coordenadas (x, y) de cada nudo; el índice de la lista es el número del nudo |
| `elements` | nudos de cada elemento: **todos** de 3 nudos o **todos** de 6 (un tipo por modelo) |
| `materials` | `Material(law, unit_weight)`: la ley (`Elastic` o `MohrCoulomb`) y el peso específico (0 = sin peso propio) |
| `element_material` | índice del material de cada elemento |
| `stages` | la secuencia de fases (al menos una) |
| `initial_stresses` | un tensor por punto de integración, elemento a elemento y en el orden de la regla del elemento; `None` es cero. Los campos constante y gravitatorio se calculan fuera del motor, con `initial_stress.constant_field` y `initial_stress.gravitational_field`, que reciben compresión positiva (spec 002, D3 y su enmienda) |

**Puntos de integración por elemento** (spec 002, D1; Zienkiewicz y Taylor 2000, tabla 9.2):

| Elemento | Deformación plana | Axisimetría |
|---|---|---|
| T3 | 1 (centroide) | 1 (centroide) |
| T6 | 3 (centro de los lados) | 7 (interiores, ninguno sobre el eje) |

## Cada fase: `Stage`

| Campo | Qué es |
|---|---|
| `active` | si cada elemento existe en la fase; quitar un elemento es excavarlo (RF-8) |
| `restraints` | `Restraint(node, x, y)`: desplazamiento nulo en x, en y o en los dos |
| `imposed` | `ImposedDisplacement(node, component, value)`: desplazamiento **total** de un grado de libertad (0 = x, 1 = y) |
| `nodal_loads` | `NodalLoad(node, fx, fy)`: fuerza **total** en un nudo |
| `point_loads` | `PointLoad(element, x, y, fx, fy)`: fuerza **total** en un punto de un elemento; el motor la reparte con las funciones de forma, fᵢ = Nᵢ(x, y)·(fx, fy) |
| `edge_loads` | `EdgeLoad(element, side, start, end, normal)`: tracción **total** por unidad de longitud a lo largo del lado `side`, lineal de su primera esquina a la segunda (uniforme: `start == end`; triangular: una de las dos nula). En ejes globales (x, y) o, con `normal=True`, como (normal, tangencial): normal positiva hacia fuera del elemento, que es tirar (tracción positiva); tangencial positiva de la primera esquina a la segunda. En axisimetría, por unidad de longitud del meridiano; el anillo lo pone el motor |
| `steps`, `tolerance`, `max_iterations`, `max_cuts` | escalones, tolerancia del residuo relativo, iteraciones por escalón y particiones permitidas en la fase. **Cambian el resultado** y van con él (regla 12) |

## Reglas de validación

`validate()` comprueba todo lo que se puede comprobar antes de calcular y lanza `InputError` con
**todos** los problemas a la vez. Cada problema (`Problem`) dice la regla que incumple, el sitio
(fase, elemento, nudo o material) y por qué.

| Regla | Qué rechaza | Por qué |
|---|---|---|
| `analysis` | un tipo de análisis que no es ninguno de los dos | — |
| `nodes` | menos de tres nudos, o coordenadas que no son dos números finitos | — |
| `node_left_of_axis` | en axisimetría, un nudo con x < 0 | el eje es x = 0; a la izquierda, el radio sería negativo |
| `unused_node` | un nudo que no está en ningún elemento | no tendría rigidez: la matriz sería singular |
| `element_kind` | elementos que no son todos de 3 o todos de 6 nudos | un tipo por modelo (spec 002, plan) |
| `element_node` | un elemento con un nudo que no existe | — |
| `repeated_node` | un elemento que repite un nudo | — |
| `degenerate_element` | esquinas con área nula o en sentido horario (área por debajo de 10⁻¹⁰ veces el cuadrado del lado mayor) | el jacobiano sería nulo o negativo. La posición de los nudos intermedios del T6 la comprueba el elemento (det J > 0 en cada punto) |
| `element_material` | un índice de material que no existe, o un número de índices distinto del de elementos | — |
| `material` | E ≤ 0, ν fuera de (−1, 0.5), peso negativo; en Mohr-Coulomb, c < 0 o fuera de 0 ≤ ψ ≤ φ < 90° | los límites de la ley (de Souza Neto et al. 2008, §8.2) |
| `plasticity_not_validated` | Mohr-Coulomb con T3 o en axisimetría | no está validado (spec 002, D6) |
| `initial_stresses` | un número de tensiones distinto del de puntos de integración, o una que no son cuatro números finitos | — |
| `no_stage` | ninguna fase | — |
| `active` | un número de indicadores distinto del de elementos | — |
| `no_active_element` | una fase sin ningún elemento activo | — |
| `node` | una restricción, desplazamiento o carga en un nudo que no existe | — |
| `inactive_node` | un desplazamiento impuesto o una carga en un nudo sin elementos activos en la fase | se perderían: el nudo sale del sistema. Una **restricción** en ese nudo se acepta: no sujeta nada, y el contorno de una zona excavada después conserva sus restricciones |
| `restrained_and_imposed` | un grado de libertad restringido e impuesto a la vez | dos condiciones para el mismo valor |
| `imposed_twice` | un grado de libertad impuesto dos veces | — |
| `component` | una componente que no es 0 (x) ni 1 (y) | — |
| `load_on_axis` | en axisimetría, una fuerza radial en un nudo del eje (x = 0 exacto) | allí u_r = 0 por simetría y el motor lo impone siempre (spec 002, D1 bis): la fuerza iría a la reacción |
| `imposed_on_axis` | en axisimetría, un desplazamiento radial no nulo en un nudo del eje | lo mismo |
| `element` | una carga en un elemento que no existe | — |
| `inactive_element` | una carga en un elemento no activo en la fase | — |
| `side` | un lado que no es 0, 1 ni 2 | — |
| `finite` | un valor de carga o de desplazamiento que no es finito | — |
| `stage_settings` | escalones < 1, iteraciones < 1, particiones < 0 o tolerancia ≤ 0 | — |

## Lo que hace el motor con ella

`analysis.run` (`ogr_fem2d/engine/analysis.py`) valida la entrada y resuelve las fases en orden.
Por fase devuelve los desplazamientos y las tensiones **totales**, las **reacciones** por nudo
(R = f_int − f_ext en cada componente restringida o impuesta), la historia de convergencia y los
ajustes que cambian el resultado. Además:

- en axisimetría sujeta u_r = 0 en todos los nudos con x = 0 aunque no se pida, y devuelve la
  lista (`axis_held`; spec 002, D1 bis);
- antes de resolver comprueba que las restricciones paran los movimientos de sólido rígido (en
  deformación plana, las dos traslaciones y el giro; en axisimetría, la traslación axial) y, si
  no, dice cuál queda libre (`InsufficientRestraintError`);
- una fase cuyo desequilibrio es redondeo (menos de 1e-12 de la mayor fuerza en juego) no se
  resuelve: su estado es el de la anterior, y el resultado lo dice (`solved = False`);
- cada fase se resuelve sobre sus elementos **activos**: quitar elementos es excavar, y la carga
  es el desequilibrio que dejan las tensiones de los que quedan (Z&T ec. 2.13b). Los nudos que se
  quedan sin elementos salen del sistema, conservan su desplazamiento y se listan
  (`removed_nodes`); las tensiones de los elementos inactivos son `None`. Un elemento que vuelve
  a activarse se rechaza (spec 002, T9).

**Lo que solo se ve al calcular** lo informa el solver, no `validate()`: una matriz de rigidez
singular (restricciones insuficientes), un punto de integración con det J ≤ 0 en un T6 de nudos
intermedios mal colocados, y una carga puntual fuera de su elemento o, en axisimetría, una fuerza
puntual radial sobre el eje (`LoadError`, con la fase y el elemento).

## Cómo se convierten las cargas

Todas pasan a **fuerzas nodales consistentes** (`ogr_fem2d/engine/reference/loads.py`):

| Carga | Fuerzas nodales | Fuente |
|---|---|---|
| Nodal | tal cual | Zienkiewicz y Taylor (2000), ec. (2.14) |
| Peso propio | ∫Nᵀb dV con b = (0, −γ), por la regla del elemento; en axisimetría, sobre el anillo | ecs. (2.13b) y (5.19) |
| Repartida sobre un lado | ∫Nᵀt ds, con t lineal de la primera esquina a la segunda, por Gauss-Legendre de 10 puntos; en axisimetría, con 2π r | ec. (2.15) y tabla 9.1 |
| Puntual | Nₐ(x, y)·P, con (x, y) llevado a coordenadas de área invirtiendo la transformación del elemento | trabajo virtual de la ec. (2.10) (derivación propia) |

En un lado recto, o con carga normal en un lado curvo, la integral es exacta. Con la carga en
componentes globales sobre un lado curvo del T6 es una aproximación: 2·10⁻¹¹ en un lado que abarca
90° de circunferencia, redondeo a partir de 22.5°.
