# 006 — Carga en faja sobre un semiespacio, con malla general y por el modelo (Michell)

| Campo | Valor |
|---|---|
| Ficha de trabajo | `VER-STR-04` (en `../Referencias/Ejemplos/Casos_por_problema/`) |
| Fuente científica | J. H. Michell (1902), en Timoshenko y Goodier (1951), *Theory of Elasticity*, 2.ª ed., §34, ec. (f), págs. 92–95 (la del caso 004) |
| Tipo de referencia | analítica |
| Tipo de análisis | deformación plana; elástico lineal; una fase de carga |
| Modelo | `modelo.ogrfem2d` (spec 004) |

El caso 004 con la **malla general** de la spec 003 y **por el modelo** de la spec 004 (D4): la carga
y las condiciones se dan sobre la geometría, no sobre nudos. El caso 004 no cambia (regla 9).

> **Estado (2026-11-23): la malla, fijada por su estudio; el caso, dentro de su tolerancia.** La
> tolerancia se escribió antes de medir (commit 397305c) y no ha cambiado.

## Geometría, material, condiciones y carga

Las del caso 004: el medio modelo 0 ≤ x ≤ W, −D ≤ y ≤ 0, con **W = D = 200 m** (el dominio que fijó el
estudio del caso 004), y el contorno externo con un vértice en (b, 0), b = 1 m, el borde de la faja.
E = 20 000 MPa, ν = 0.2, sin peso ni tensión inicial.

- Tramo x = 0 (de (0, 0) a (0, −D)): restricción en x (simetría).
- Tramo x = W: restricción en x.
- Superficie (de (W, 0) a (0, 0)): libre.
- Fondo: el defecto del contorno externo, fijo en x e y (D16; los nudos de las esquinas toman la
  unión de sus tramos).
- Carga repartida **normal**, q = 1 MPa (1000 kPa: el modelo guarda en kPa, D5), sobre el tramo
  (b, 0) → (0, 0), positiva hacia el terreno (D6).

## Valor esperado y de dónde sale

El del caso 004: σ1 = q/π (α + sen α) y σ3 = q/π (α − sen α), compresión positiva. Se compara el
**peor** punto de todos los puntos de integración con **x ≤ 0.25 m** y 0.25 ≤ z ≤ 5 m, cada uno
contra Michell en su (x, z). **Tolerancia absoluta: 0.01 q**, la del caso 004 (spec 002, D4). La
primera columna de elementos del caso 004 no existe en una malla general; la banda de 0.25 m es dos
veces el tamaño de los elementos junto al eje del caso 004.

El efecto del dominio de 200 m lo midió el caso 004: 0.0045 q en σ3, la mitad de la tolerancia.

## Malla y elemento con que se fija la tolerancia

T6, malla graduada de la spec 003, B = √2, con una **ventana** 0 ≤ x ≤ 6, −6 ≤ y ≤ 0 m de tamaño
**h = 0.125 m**, el tramo de la faja en 8 divisiones (piezas de h), una **cota máxima de 6.25 m**
(50 h) y 4 nudos repartidos en los demás tramos del contorno (el mínimo: entran con sus extremos y el
refinado gradúa). 17 532 elementos. `tests/_cases_model.py` construye el modelo;
`spec/features/004-modelo-y-proyecto/comprobaciones/estudio_006_007.py` rehace el estudio.

| h (m) | Elementos | σ1 | σ3 |
|---|---|---|---|
| 0.25 | 4 541 | 0.00160 q | 0.00855 q |
| **0.125** | **17 532** | **0.00062 q** | **0.00533 q** |
| 0.0625 | 68 945 | 0.00016 q | 0.00466 q |

σ1 baja cuatro veces por paso. σ3 tiende al efecto del dominio de 200 m que midió el caso 004
(0.0045 q): lo que queda de discretización con h = 0.125 es unas 0.0008 q. La malla de h = 0.25 ya
cumple, con un margen del 15 %; la de 0.125 es la primera con margen, como en el caso 004.
