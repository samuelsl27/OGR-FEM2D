# 001 — Hueco circular en medio elástico con tensión inicial hidrostática (Kirsch)

| Campo | Valor |
|---|---|
| Ficha de trabajo | `VER-STR-01` (en `../Referencias/Ejemplos/Casos_por_problema/`) |
| Fuente científica | Kirsch (1898), en Jaeger, Cook y Zimmerman (2007), *Fundamentals of Rock Mechanics*, 4.ª ed., §8.4, ecs. (8.90)–(8.92), págs. 216–218 |
| Tipo de referencia | analítica |
| Tipo de análisis | deformación plana; elástico lineal; una fase de excavación |

## Geometría

Hueco de radio a = 1 m. Se modela un cuarto de corona, a ≤ r ≤ b, 0 ≤ θ ≤ 90°, con
**b = 100 m** (spec 001, D3 bis): a esa distancia el contorno fijo aparta la solución exacta del
modelo de la de medio infinito un 0.027 % en ur(a) y un 0.017 % en σθ(a)
(`comprobaciones/soluciones_cerradas.py`, `lame_fixed_outer`).

## Materiales y parámetros

E = 10 000 MPa, ν = 0.2.

## Condiciones de contorno, tensión inicial y fases

- Rodillos en los dos ejes (v = 0 en el eje x, u = 0 en el eje y), por la doble simetría.
- Contorno exterior fijo en las dos direcciones.
- Tensión inicial hidrostática de 30 MPa de compresión en las tres direcciones (σzz incluida).
- Una fase: excavación del hueco, que queda sin presión. La carga es el término de tensión inicial
  de la ec. (2.13b) de Zienkiewicz y Taylor (2000); la carga total de la fase es cero (D2).

## Valor esperado y de dónde sale

En medio infinito, con compresión positiva y ur positivo hacia el centro:

- σθ(a) = 2 p0 = **60 MPa** (8.92, con el signo que dan el límite b → ∞ de la (8.86) y la (8.104);
  plan, «Formulación»);
- ur(a) = p0 a / (2G) = **0.0036 m**, solo el término a²/r de la (8.90): el (1 − 2ν) p0 r es el
  desplazamiento del estado inicial, que la excavación no causa.

Se compara el **peor** punto: σθ en todos los puntos de integración sobre r = a (la regla
cuadrática pone uno en el centro de cada lado del hueco, sobre el círculo) y ur en todos los nudos
sobre r = a. Tolerancia de D3: **0.5 %** en los dos.

## Malla y elemento con que se fija la tolerancia

T6 isoparamétrico (`ogr_fem2d.engine.mesh_radial.quarter_annulus`): **32 divisiones radiales, 8
angulares, crecimiento 1.69^¼ = 1.1402** (primer elemento de 0.21 m). Estudio de convergencia con
la familia anidada 2 × 8, 4 × 16, 8 × 32 y 16 × 64 (crecimiento 1.69^(1/2^k)):

| Malla | error máx. en ur(a) | error máx. en σθ(a) |
|---|---|---|
| 2 × 8 | 10.3 % | 2.71 % |
| 4 × 16 | 1.34 % | 0.587 % |
| **8 × 32** | **0.189 %** | **0.194 %** |
| 16 × 64 | 0.047 % | 0.048 % |

La de 8 × 32 es la primera que cumple las dos tolerancias. Las tolerancias se escribieron en
`esperado.json` antes del estudio (commit 962f504, con la malla a `null`).
