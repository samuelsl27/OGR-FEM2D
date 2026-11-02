# 004 — Carga uniforme en faja sobre un semiespacio elástico (Michell)

| Campo | Valor |
|---|---|
| Ficha de trabajo | `VER-STR-04` (en `../Referencias/Ejemplos/Casos_por_problema/`) |
| Fuente científica | J. H. Michell (1902), en Timoshenko y Goodier (1951), *Theory of Elasticity*, 2.ª ed., §34, ec. (f), págs. 92–95; comprobada por superposición numérica de la fuerza puntual de Flamant (1892), §33, ec. (66), pág. 85 |
| Tipo de referencia | analítica |
| Tipo de análisis | deformación plana; elástico lineal; una fase de carga |

La ficha cita Poulos y Davis (1974), que no está en la bibliografía; da la misma solución.

## Geometría

Semiespacio cargado en una faja de semianchura b = 1 m. Por la simetría respecto a x = 0 se modela
la mitad, 0 ≤ x ≤ W y −D ≤ y ≤ 0, con y hacia arriba, la superficie en y = 0 y la profundidad z = −y.
La ficha usa un rectángulo de 50 × 25 m (W = 25, D = 25 en el medio modelo). **El dominio lo fija
un estudio** (spec 002, D4): el semiespacio es infinito y el modelo no.

## Materiales y parámetros

E = 20 000 MPa, ν = 0.2. Sin peso propio ni tensión inicial: la solución de Michell es la de la
carga sola.

## Condiciones de contorno y carga

- x = 0: u = 0 (simetría).
- x = W: u = 0 (rodillos).
- y = −D: u = v = 0.
- Presión q = 1 MPa sobre 0 ≤ x ≤ b de la superficie, como carga repartida normal sobre los lados
  de los elementos (tracción normal −q).

La ficha no documenta el tipo de apoyo de cada lado; estos son los elegidos, y su efecto entra en
el estudio de dominio.

## Valor esperado y de dónde sale

En cualquier punto, con α el ángulo entre los radios a los dos bordes de la faja y compresión
positiva: **σ1 = q/π (α + sen α)**, **σ3 = q/π (α − sen α)**, con σ1 en la bisectriz de ese ángulo
(T&G §34, ec. f, con 2πA = q). En el eje, a 1 m de profundidad, σ1 = 0.818310 y σ3 = 0.181690 MPa; a
5 m, 0.248093 y 0.003239 MPa (`spec/features/002-motor-elastico/comprobaciones/`).

Se compara el **peor** punto: σ1 y σ3 en todos los puntos de integración de la primera columna de
elementos, junto al eje, con 0.25 ≤ z ≤ 5 m, cada uno contra Michell en su (x, z). Tolerancia de D4,
**absoluta: 0.01 q** en los dos (σ3 baja a 0.003 q a 5 m: un error relativo no significaría nada).
Desde z = 0.25 m porque en la superficie la tracción salta en el borde de la faja.

Solo tensiones, como la ficha: en deformación plana el desplazamiento bajo una carga en un
semiespacio no está acotado; lleva log r y una constante que depende del punto que se toma como
fijo (T&G §33, ecs. g–72).

**Lo que la ficha da como error (0.6 % en σ1) es el resultado de otro programa: no es valor
esperado.**

## Dominio, malla y elemento con que se fija la tolerancia

Pendientes de los estudios de dominio y de convergencia (tarea T12).
