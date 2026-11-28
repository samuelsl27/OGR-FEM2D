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
