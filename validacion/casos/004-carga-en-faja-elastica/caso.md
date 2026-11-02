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

**El dominio de la ficha no basta.** Con el medio modelo de 25 × 25 m y el contorno apoyado, σ3 se
queda a **0.035 q** de Michell con cualquier malla: más de tres veces la tolerancia. Es el efecto del
contorno, y baja despacio, como 1/L, porque las tensiones de un semiespacio cargado decaen como 1/r
(Flamant, T&G §33) y lo que el apoyo corta a la distancia L perturba el eje en proporción a q b / L.

Para separar los dos errores se usa también un **contorno exacto**: en x = W y en y = −D se
aplican las tracciones de la propia solución de Michell (σ·n, integradas con Gauss-Legendre de 10
puntos), con u = 0 en el eje y un solo v sujeto. Ese modelo tiene la solución del semiespacio
infinito y su error es solo de discretización.

**Convergencia** (contorno exacto, 25 × 25 m, h0 = tamaño en la faja, g = 1.5^(1/2^k)):

| h0 | T6: σ1 | T6: σ3 | T3: σ1 | T3: σ3 |
|---|---|---|---|---|
| 0.5 | 0.0215 q | 0.0189 q | 0.134 q | 0.159 q |
| 0.25 | 0.0051 q | 0.0040 q | 0.051 q | 0.097 q |
| 0.125 | **0.0012 q** | **0.0009 q** | 0.020 q | 0.052 q |
| 0.0625 | 0.0003 q | 0.0002 q | 0.0085 q | 0.026 q |
| 0.03125 | — | — | 0.0040 q | 0.013 q |

El T6 baja ×4 por refinamiento; el T3, ×2, y no cumple en σ3 ni con 37 088 elementos.

**Dominio** (contorno apoyado, T6, h0 = 0.125):

| W = D | σ1 | σ3 | efecto del dominio en σ3 |
|---|---|---|---|
| 100 m | 0.0011 q | 0.0097 q | 0.0088 q |
| 200 m | **0.0012 q** | **0.0054 q** | 0.0045 q |
| 400 m | 0.0011 q | 0.0031 q | 0.0022 q |

**Se fija W = D = 200 m** (el rectángulo completo, 400 × 200 m) **con T6, h0 = 0.125 m y g = 1.5^¼**:
σ1 0.0012 q y σ3 0.0054 q, con la tolerancia de 0.01 q. Con 100 m también cumpliría, pero con un 3 %
de margen y el efecto del dominio ocupando él solo casi toda la tolerancia; con 200 m es la mitad.
