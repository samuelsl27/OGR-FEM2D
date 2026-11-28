# OGR FEM2D v0.0.16

**Fase 2, primera parte: el motor y STR-05** (spec 007, parte A). La tolerancia, el criterio de
colapso y los escalones del cálculo elastoplástico, fijados con la zapata de Prandtl (caso 008) y el
caso 002. Este archivo cuenta lo que fue entrando, tarea a tarea.

## La spec, el plan y las tareas (2026-11-28)

Revisados contra el código, el núcleo `v0.2.13`, las fuentes y la ficha STR-05, y aprobados con
D1–D14 (`spec/features/007-convergencia-y-colapso/`, commit `ee437eb`). Lo que se encontró al
revisarla:

- **No hay regla con fuente para el número ni el reparto de los escalones** con carga impuesta: de
  Souza Neto et al. (2008), §5.4.1, dan los factores de carga como dato, y su regla de tamaño
  automático (ec. 5.3) es de la longitud de arco. La regla del programa de referencia (T05) y su
  reparto geométrico de razón 0.7 (P13) no tienen fuente. El número por defecto sale de un estudio
  (D3).
- **Ninguna fuente da una tolerancia por defecto** (de Souza Neto, Zienkiewicz y Taylor; Clausen
  2007, «usually around 1e-3»). Sale de un estudio escrito antes de medir (D1).
- **La carga de colapso con carga impuesta sí tiene definición con fuente** (de Souza Neto, §7.5.3):
  aquella por encima de la cual las iteraciones no convergen con un incremento suficientemente
  pequeño. Es el criterio de D2.
- **La búsqueda lineal global no está en las fuentes disponibles**: de Souza Neto remite a Crisfield
  (1991), que no está. Pedido a la propietaria, con Hill (1950) o Prandtl (1921) y Sloan y Randolph
  (1982).
- El Mohr-Coulomb del modelo sigue en la 008 (004, D9): STR-05 es un caso del motor, el 008.

## T1 — Tresca en un punto de Gauss (2026-11-28)

`tests/test_tresca_point_v0016.py` (RF-12, D14; regla 8). El Mohr-Coulomb del motor con φ = ψ = 0,
con el material del caso 008 (E = 250 MPa, ν = 0.2, c = 0.1 MPa), frente al retorno de Tresca de
de Souza Neto et al. (2008), §8.1.1, boxes 8.1–8.3 (págs. 275–278), escrito aparte en el test con
σ_y = 2c y sin endurecimiento (los Newton de las boxes 8.2 y 8.3 terminan en un paso: forma cerrada).
Sus tensiones principales salen de `numpy.linalg.eigh` del tensor 3 × 3, no del código probado.

- **Coinciden** en una nube de 4000 estados que cubre las cuatro regiones: la tensión a 1e-12 MPa,
  la región y los dos multiplicadores. Lo que dice la Remark 8.2 (pág. 300) se cumple.
- **Con φ = 0 el vértice no se pide nunca**, en 40 000 estados con incrementos diez veces mayores. El
  código rechaza el vértice con φ = 0 (lo que hace SUMC, pág. 313); Tresca no lo tiene, así que el
  Mohr-Coulomb de ahora sirve para el caso 008 sin cambios.
- **Corte simple en deformación plana** desde tensión nula: τxy = Gγ hasta τxy = c y después c, a
  1e-12, con σxx = σyy = σzz = 0.
- **La tangente consistente** es la derivada de la actualización en el plano y en las dos aristas
  (diferencias centrales, 1e-5 E).
- **Rust** da lo mismo que la referencia en la misma nube: 1e-10 en tensiones y tangentes.

Mutaciones (`{etiqueta: (archivo, texto, sustituto)}`, todas en
`ogr_fem2d/engine/reference/mohr_coulomb.py`), 9 cazadas y 1 equivalente:

| Etiqueta | Cambio | Resultado |
|---|---|---|
| `edge_choice` | la arista derecha con `< 0.0` | cazada |
| `plane_multiplier` | `dg = 0.5 * phi_trial / a` | cazada |
| `elastic_tolerance` | elástico hasta `1e-3 * scale` | cazada |
| `principal_angle` | `atan2(t_xy, …)` sin el 2 | cazada |
| `assembly_shear` | `(hi - lo) * s * s` | cazada |
| `edge_order_check` | el retorno al plano siempre válido | cazada |
| `tangent_plane` | `0.9 * d1[i] * ga[j] / a` | cazada |
| `tangent_left_edge` | el gradiente de la arista izquierda sin su tercera componente | cazada |
| `tangent_right_edge` | el de la derecha sin la segunda | cazada |
| `tangent_edge` | `-(1.0 + sf)` por `-(1.0 - sf)` | **equivalente** con φ = 0 (sen φ = 0); por eso las dos anteriores |

Las mutaciones de `rust/` no se hacen: piden recompilar, y la identidad con la referencia ya las
cubre (spec 001, T12).

**Hallazgo, sin tocar** (regla 6): en la primera vuelta de la suite con esta tarea fallaron dos tests
de Cancelar de la ventana de cálculo (`test_gui_compute_v0015.py`, `TestCancel` y
`TestCancelAnsweredLate`): esperan la parada entre fases, y la ventana dijo «parado durante una
fase», es decir, el proceso hijo no llegó al final de la primera fase dentro del plazo de 5 s de
D9 (spec 006) y se mató. Solos, y en la vuelta siguiente de la suite entera (862 de 862), pasan. Es
un test que depende del tiempo con el equipo cargado; nada de esta tarea toca ese camino. Queda
anotado por si vuelve; la cancelación entre iteraciones de la T3 (D10) le quita la dependencia del
plazo.

## T2 — El diagnóstico de la robustez (2026-11-28)

`spec/features/007-convergencia-y-colapso/comprobaciones/diagnostico_robustez.py` (D5, 1; regla 6).
Mira el motor desde fuera, sin cambiar código: una variante que envuelve la de Rust y anota cada
actualización (las regiones de los puntos, el tamaño de la corrección, el punto que se rechaza y
su tensión de prueba). Los incrementos y la historia de una fase que falla se leen de las variables
de `solve_stage` en la traza. Los dos problemas que la spec 001 dejó sin converger, con ψ = 0°,
tolerancia 1e-10 y 25 iteraciones: el caso 002 con 16 × 64 (b = 100 m) y el anillo de 21 m con
16 × 48.

**Factor de carga alcanzado** (la excavación va de 0 a 1), con 5, 10, 20 y 40 escalones y 0, 4, 8 y
16 particiones. **Ninguna de las 32 combinaciones converge**:

| | 0 part. | 4 | 8 | 16 |
|---|---|---|---|---|
| 002, 5 escalones | 0.800 | 0.850 | 0.860 | 0.894 |
| 002, 10 | 0.800 | 0.856 | 0.860 | 0.895 |
| 002, 20 | 0.850 | 0.859 | 0.875 | 0.895 |
| 002, 40 | 0.850 | 0.859 | 0.860 | 0.891 |
| anillo, 5 | 0.800 | 0.950 | 0.959 | 0.961 |
| anillo, 10 | 0.900 | 0.956 | 0.960 | 0.961 |
| anillo, 20 | 0.950 | 0.959 | 0.960 | 0.960 |
| anillo, 40 | 0.950 | 0.959 | 0.961 | 0.961 |

Lo encontrado:

- **Es una barrera de nivel de carga, no de tamaño de incremento.** El 002 se para hacia 0.86–0.90 y
  el anillo hacia 0.96, sea cual sea el reparto. Con 40 escalones y 16 particiones, el último
  incremento del anillo que falla va de 0.961249 a 0.961255: 6e-6 de la fase. **La partición (D5, 2)
  no basta**, y tampoco más escalones (lo que dice Clausen 2007, apéndice B).
- **El mecanismo**: Newton no reduce el residuo, lo hace oscilar. En cada iteración, entre 30 y 170
  puntos cambian de región (plano, arista, elástico). Con una corrección a veces enorme: el residuo
  baja a 1e-3 o 1e-5 y en la iteración siguiente la corrección de desplazamiento llega a 0.02–0.65 m,
  frente a los 8 mm de la pared en la solución. Es la firma de una tangente casi singular. Un punto
  de la pared del hueco, siempre en los primeros elementos junto al eje x (a 0°–14°), recibe entonces
  una tensión de prueba de 10³ a 10⁴ MPa y pide el vértice, que con ψ = 0 no existe. Así terminan la
  mayoría de los incrementos que fallan. Los demás agotan las 25 iteraciones oscilando.
- **Es de ψ = 0.** Con ψ = 5° los dos convergen con 5 escalones y sin ninguna partición. Con ψ = 1° el
  anillo converge y el 002 da con una **tangente exactamente singular**: los puntos que llegan al
  vértice tienen D^ep = 0 (de Souza Neto et al., Remark 8.3; Clausen 2007, cap. 8, págs. 94–96: «a
  breakdown due to a singular global stiffness matrix»).
- **Anomalía del motor, sin corregir** (regla 6): esa factorización singular **se escapa** de
  `solve_stage` como el `RuntimeError` de SuperLU («Factor is exactly singular»). No se parte el
  incremento, y `calculate` no lo trata como una fase que falla sino como un error del programa (no
  está en `STAGE_FAILURES`). De Souza Neto et al. (2008), fig. 5.2, cuentan el pivote nulo entre los
  fallos que llevan a partir el incremento. Se propone tratarlo así en la T3: partir el incremento y,
  agotadas las particiones, una no convergencia con su motivo. Pendiente del OK de la propietaria.

**Consecuencia para la T9 (RF-8)**: con la estrategia de D5 (2), los dos casos no van a converger. Lo
que corrige una corrección desmesurada es acotarla, que es lo que hace una búsqueda lineal, y su
fuente (Crisfield 1991) no está. Se propone a la propietaria dejar RF-8 como hallazgo con este
diagnóstico, y la búsqueda lineal para cuando esté la fuente (D5, 3). No afecta a STR-05: con φ = 0
no hay vértice (T1).

**Decisiones de la propietaria al cerrar la T2** (2026-11-28):

- La anomalía de la tangente singular se corrige en la T3: cuenta como incremento que falla.
- **Crisfield (1991) conseguido**. Con él, la búsqueda lineal de su §9.2 entra en la T9, medida A/B.
- **D3 modificada**: Crisfield, ec. (9.40), da una regla con fuente para el tamaño automático del
  incremento con carga impuesta, Δλ_n = Δλ_o (I_d / I_o)^(1/2). La premisa de D3 («no hay regla con
  fuente») era falsa. Se programan los dos modos, iguales y automáticos (T4), y el estudio de la T7
  elige cuál va por defecto.
- Crisfield, §9.5.4, respalda D1: el criterio de desplazamiento no basta solo, y los de energía
  «should be used with great caution». Su §2.4 da β típica entre 0.001 y 0.01 para estructuras; aquí
  el valor sigue saliendo del estudio.
