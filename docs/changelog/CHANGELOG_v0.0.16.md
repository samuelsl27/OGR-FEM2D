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

## T3 — El bucle de la fase: progreso, parada, incrementos, colapso y tangente singular (2026-11-28)

`engine/reference/solver.py`, `engine/analysis.py`, `results/calculate.py`; `tests/test_stage_loop_v0016.py`
(RF-3, RF-4, RF-7, RF-10; D2, D10, D12). Ningún número cambia: el caso 002 (ψ = 0° con 8 × 32 y
ψ = 30° con 16 × 64), el anillo grueso con particiones (referencia y Rust) y el de 16 × 48 dan lo
mismo, bit a bit, con el `solver.py` de `bee6617` y con el nuevo (comprobado con una copia temporal
del anterior, ya borrada).

- **El progreso por iteración** (D10): `solve_stage(…, progress=, should_stop=)`. `progress` oye
  cada iteración (`Iteration`: el incremento con sus factores, la iteración, el residuo relativo y las
  particiones hechas), en el orden de la historia. `should_stop` se pregunta antes de cada
  corrección y para la fase con `Cancelled`. `analysis.stages` y `analysis.run` los pasan, con el
  índice de la fase.
- **Los incrementos** (D2): cada uno probado es un `Increment` (factores, estado `converged`,
  `floor` o `cut`, motivo de la partición, correcciones hechas). Hasta ahora eran (inicio, fin,
  texto). `StageOutcome.increments` los lleva, **fuera de la comparación** de `StageOutcome` hasta
  que el `.h5` los guarde (T13): siete tests comparan una fase leída del archivo con la del motor, y
  fallaron en la primera vuelta de la suite por eso. `test_solver_v001` se adaptó al formato nuevo, con
  las mismas comprobaciones.
- **El factor alcanzado** (D2, de Souza Neto et al. 2008, §7.5.3): agotadas las particiones, el error
  que sale de la fase lleva `reached` (el factor convergido hasta entonces) y `smallest` (el
  incremento más pequeño probado). En el anillo de 16 × 48 con ψ = 0°, 5 escalones y 4 particiones:
  0.95 y 0.2/2⁴, lo que dio el diagnóstico de la T2.
- **El suelo de redondeo, marcado** (D12): el incremento que converge por `NO_LOAD` y no por la
  tolerancia queda `floor`. Con la carga de 1e-9 de las fuerzas en juego de la v0.0.2 es `floor`, y
  con una carga normal, `converged`.
- **La tangente singular** (la anomalía de la T2, corregida con el OK de la propietaria): un `splu`
  singular en una corrección es ahora `SingularTangentError`. Se parte el incremento como los demás
  fallos (`INCREMENT_FAILURES`; de Souza Neto et al., fig. 5.2) y `calculate` lo escribe como una
  fase que falla (`incomplete`), no como un error del programa. El caso 002 con 16 × 64 y ψ = 1°:
  sin particiones falla en 0.8 con su motivo; con 4, llega a 0.9 y vuelve a dar con una tangente
  singular. La factorización elástica del principio no cambia: una matriz elástica singular es un
  mecanismo del modelo, que `analysis` busca antes de resolver.

Mutaciones (`tests/test_stage_loop_v0016.py`), 13 de 13 cazadas:

| Etiqueta | Cambio |
|---|---|
| `progress_skipped` | sin avisar la iteración 0 |
| `progress_cuts` | las particiones siempre 0 en el aviso |
| `stop_late` | no preguntar antes de la primera corrección |
| `stop_ignored_stage` | `analysis` no pasa `should_stop` |
| `reached_wrong` | `reached` es el factor buscado, no el alcanzado |
| `smallest_wrong` | `smallest` es el mayor |
| `floor_never`, `floor_always` | la marca del suelo, nunca o siempre |
| `singular_not_caught` | cualquier `RuntimeError` del factorizador es una tangente singular |
| `singular_not_cut` | la tangente singular no parte el incremento |
| `calculate_not_stage` | `calculate` no la trata como fase que falla |
| `iterations_count` | una corrección de más en el incremento |
| `increments_lost` | `StageOutcome` sin los incrementos |

## T4 — Los tres modos de los escalones (2026-11-28)

`engine/reference/solver.py`, `engine/model.py`, `engine/analysis.py`; `tests/test_steps_v0016.py`
(RF-5, RF-6; D3 modificada). Además de `steps` escalones iguales, una fase admite:

- **`factors`**, la lista de factores de carga del final de cada incremento: creciente, en (0, 1] y
  terminada en 1 (de Souza Neto et al. 2008, §5.4.1: los factores son un dato);
- **`automatic`**, el tamaño automático de **Crisfield (1991), §9.5, ec. (9.40)**, leída sobre la
  página (pág. 287): Δλ_n = Δλ_o (I_d / I_o)^n, con Δλ_o el incremento anterior, I_o sus
  iteraciones, I_d las deseadas («I_d ≃ 3», no «≥ 3», como se había escrito en la spec y se corrigió)
  y n = 1/2 (Ramm, adoptado por el autor). El usuario da el primer incremento, un máximo y, si
  quiere, un mínimo. El mínimo acota lo que propone la regla, nunca una partición («too high a
  minimum increment size can interfere with the increment-cutting procedure»). El último incremento
  acaba en 1.

En los tres, un incremento que falla se parte como antes, y la fase sigue hasta el objetivo que
tenía. Solo cuando no queda objetivo propone el tamaño automático el siguiente. Con `factors` o
`automatic`, el `steps` del resultado es el número de incrementos que convergieron (regla 12). El
modelo del motor valida los dos y dice por qué rechaza uno.

En la excavación del anillo con Mohr-Coulomb (12 × 4), cada ajuste mueve el desplazamiento entre
1e-5 y 4e-4 m (u_r(a) ≈ 8 mm). La lista de factores y el automático por defecto de los tests dan lo
mismo a 1e-15 en ese caso, porque los dos acaban con un solo incremento plástico desde un estado
elástico: por eso la lista se compara con cuatro escalones iguales.

Mutaciones (`tests/test_steps_v0016.py`), 15. En la primera pasada sobrevivieron 3 y los tests se
reforzaron: los escalones contados sin las particiones (hacía falta un caso con particiones), una
lista con dos factores iguales y que `analysis` pase la lista (se miran los incrementos). Ahora las
15, cazadas:

| Etiqueta | Cambio |
|---|---|
| `exponent_one` | n = 1 en lugar de 1/2 |
| `no_largest`, `no_smallest` | sin el máximo o sin el mínimo |
| `auto_size_from_cut` | el tamaño anterior mal tomado tras el primero |
| `auto_not_to_one` | el último incremento puede pasar de 1 |
| `first_ignored` | el primero es el máximo |
| `factors_ignored` | la lista se convierte en escalones iguales |
| `steps_reported` | los escalones cuentan también las particiones |
| `check_increasing`, `check_last` | factores iguales admitidos; el último puede no ser 1 |
| `analysis_drops_factors` | `analysis` no pasa la lista |
| `validate_skips` | el modelo no valida la lista |

## T5 — El caso 008 escrito antes de medir, y dos hallazgos al resolverlo (2026-11-28)

El caso (`caso.md`, `esperado.json`) va en su commit, `c35a218`, antes de ninguna medida, con el
dominio y la malla a `null` y los protocolos de los estudios. `tests/_footing.py` construye las dos
variantes. En la primera resolución (el test de identidad referencia–Rust, con la malla más gruesa
del estudio: W = D = 30 m, h0 = 0.5 m) salieron dos cosas, que se reportan antes de tocar nada
(regla 6):

- **Anomalía del Mohr-Coulomb, en Python y en Rust: un retorno a la arista válido se rechaza por
  redondeo.** Una iteración lejos del equilibrio da en un punto una tensión de prueba de 1.9e4 MPa
  (σ₁ = 19 491, σ₃ = −19 486). El retorno a la arista derecha es válido: σ = (2.159, 1.959, 1.959).
  Pero sale con σ₂ − σ₃ = −3.3e-12 por la cancelación, y `_in_order` mide la tolerancia
  (`TOLERANCE` = 1e-12) contra las tensiones **devueltas**, del orden de 2 MPa, no contra las de
  prueba. Lo rechaza, pasa al vértice, y con φ = 0 (o ψ = 0) el vértice se rechaza. Con 1e-10 el
  mismo retorno se acepta. **Esto corrige lo que dijo la T1** («con φ = 0 el vértice no se pide
  nunca»): no se pide en estados razonables, pero sí en estados de prueba diez mil veces mayores que
  c, que la nube de la T1 no tenía. **Puede explicar parte del diagnóstico de la T2**: allí los puntos
  rechazados tenían tensiones de prueba de 10³ a 10⁴ MPa. La comprobación de fluencia del mismo
  retorno sí escala con la tensión de prueba (`scale` en `return_principal`).
- **Newton se rompe en la primera fase de la zapata rígida**, con los ajustes de los estudios (5
  escalones, tolerancia 1e-10, 8 particiones): no pasa del 9.4 % del asiento elástico δ_e, y la
  corrección de desplazamiento llega a 43 m. Es la misma firma que en la T2: una tangente casi
  singular que produce correcciones desmesuradas. Hipótesis, sin comprobar: en Tresca perfecto, un
  punto que retorna a una arista no tiene rigidez desviadora en el plano, y los elementos con todos
  sus puntos así dejan modos sin rigidez.

**Decisiones de la propietaria** (2026-11-28): corregir la anomalía en Python y en Rust, en una rama
corta (`dev/mc-tolerancia-orden`, porque toca `rust/`); después, extender el diagnóstico a STR-05 y
adelantar la búsqueda lineal (T9) antes de los estudios T6–T8.

### La corrección de la tolerancia del orden (rama `dev/mc-tolerancia-orden`)

`_in_order` (`mohr_coulomb.py`), `in_order` (`rust/src/mohr_coulomb.rs`) y el de la variante NumPy
(`poc/vectorized.py`) miden ahora la tolerancia contra la escala de la tensión de prueba (la misma
`scale` de la comprobación de fluencia), o contra la devuelta si es mayor. Lo que se comprobó:

- el estado de 1.9e4 MPa del caso 008 va a la arista derecha, con σ₂ = σ₃, σ₁ − σ₃ = 2c y la presión
  media de la prueba; una nube de 20 000 estados con incrementos de deformación de hasta 100
  (desviadores de hasta 1e4 MPa frente a c = 0.1 MPa) no pide nunca el vértice, y Rust da lo mismo
  que la referencia. Con el `mohr_coulomb.py` anterior, los dos tests fallan;
- **ningún número de los casos cambia**: el 002 con ψ = 0° y 8 × 32 y los anillos de 12 × 4 (ψ = 30°)
  y de 24 × 8 (ψ = 0°), bit a bit con la comprobación anterior puesta en su sitio por un momento;
- **el diagnóstico de la T2 no cambia**: en el 002 y en el anillo con ψ = 0 el vértice se pide de
  verdad (con φ = 30° existe y está en tracción). La corrección no los arregla;
- **en STR-05 el fallo cambia de forma**: el punto ya no se rechaza. Newton sigue hasta la iteración
  13 del mismo incremento (factor 0.094 del asiento elástico) y allí encuentra una **tangente
  singular**, que se parte como cualquier fallo (T3). Apoya la hipótesis de arriba: puntos en arista
  sin rigidez desviadora.

Las mutaciones de `rust/` no se hacen (piden recompilar); la identidad con la referencia en la nube
de estados enormes las cubre.

### La CI de la rama (run 46155954731): dos fallos de la T3, corregidos

Lanzada a mano sobre `dev/mc-tolerancia-orden` (`workflow_dispatch`). Los trabajos de construcción y
de congelado, en verde. Fallaron 5 de 9 de test, todos en `test_stage_loop_v0016` (T3), el caso 002
con 16 × 64 y ψ = 1°:

- **Linux 3.13 y Windows 3.11**: SuperLU no dijo «Factor is exactly singular» (lo de este equipo),
  sino «failed to factorize matrix at line 406/413 in dpanel_bmod.c». `factorise_tangent` solo
  reconocía el primer texto. Con la misma matriz, la referencia y Rust (que difieren en 1e-14) dan
  aquí un texto o el otro.
- **macOS, las tres versiones: segfault** dentro de `splu` (lo dijo `PYTHONFAULTHANDLER`; lo de la
  posición 677 era la salida retenida en el buffer). La matriz no tiene NaN ni infinitos, pero sí
  **819 filas exactamente nulas**: nudos cuyos puntos están todos en el vértice, con D^ep = 0
  (Remark 8.3). Con ellas SuperLU entra en su «abort» interno de `dpanel_bmod`, que en macOS revienta
  el proceso.

**Corrección** (`solver.factorise_tangent`): los grados de libertad sin ninguna rigidez se buscan
antes de factorizar, y la tangente no llega a SuperLU (`SingularTangentError`, «N degrees of freedom
with no stiffness»). Cualquier otro fallo de la factorización es un pivote nulo, con el texto de la
plataforma. La otra singularidad, la de la zapata (un mecanismo, sin filas nulas), la devuelve
SuperLU por su retorno normal. Un test nuevo la provoca, para que la CI diga si en macOS también es
segura. La mutación `singular_not_caught` de la T3 ya no aplica (no se mira el texto). Dos nuevas,
cazadas: `empty_rows_not_checked` (sobrevivía en este equipo, donde SuperLU también lanza; el test
exige ahora que el corte venga de la comprobación) y `superlu_error_escapes`.
