# 003 — Cavidad esférica en medio elástico con tensión inicial hidrostática (Lamé)

| Campo | Valor |
|---|---|
| Ficha de trabajo | `VER-STR-09` (en `../Referencias/Ejemplos/Casos_por_problema/`) |
| Fuente científica | Lamé (1852), en Timoshenko y Goodier (1951), *Theory of Elasticity*, 2.ª ed., §121, ecs. (197)–(198), págs. 358–359; el desplazamiento por la ley de Hooke (§6) |
| Tipo de referencia | analítica |
| Tipo de análisis | axisimetría; elástico lineal; una fase de excavación |

## Geometría

Cavidad de radio a = 1 m. Por la simetría respecto al plano z = 0, se modela un cuarto de corona
del plano meridiano, a ≤ R ≤ b, con x = r ≥ 0 y y = z ≥ 0, y el eje de revolución en x = 0. El
contorno exterior es esférico y fijo, a **b = 21 m**: la solución exacta del modelo se aparta de
la de medio infinito un **0.022 %** en u_R(a) y un **0.011 %** en σt(a) (`sphere_fixed_outer` en
`spec/features/002-motor-elastico/comprobaciones/`). El efecto va con 1/b³, no con 1/b² como en el
hueco cilíndrico, y una sola geometría basta (spec 002, D4).

La ficha usa un contorno exterior rectangular y triángulos de 3 nudos; aquí el contorno es esférico
porque la malla general llega con la spec 003 (D5), y el elemento lo fija el estudio de abajo.

## Materiales y parámetros

E = 20 000 MPa, ν = 0.2 (G = 8 333.3 MPa).

## Condiciones de contorno, tensión inicial y fases

- Eje (x = 0): u_r = 0, que el motor impone siempre (spec 002, D1 bis).
- Plano de simetría (y = 0): v = 0.
- Contorno exterior fijo en las dos direcciones.
- Tensión inicial hidrostática de 10 MPa de compresión, σr = σz = σθ (la enmienda de D3 lo exige
  en axisimetría y aquí se cumple).
- Una fase: excavación de la cavidad, sin presión. La carga es el término de tensión inicial de la
  ec. (2.13b) de Zienkiewicz y Taylor (2000).

## Valor esperado y de dónde sale

En medio infinito, con compresión positiva y u_R positivo hacia el centro:

- σR = p0 (1 − a³/R³), σt = p0 (1 + a³/(2R³)): **σt(a) = 15 MPa**, σR(a) = 0;
- u_R = p0 a³ / (4 G R²): **u_R(a) = 3.0·10⁻⁴ m**.

Se compara el **peor** punto. σt, en todos los puntos de integración del primer anillo de elementos,
cada uno contra la solución en su propio radio: la regla de 7 puntos del T6 en axisimetría (D1) no
pone ninguno sobre el hueco. Por la simetría esférica las dos tensiones tangenciales, la meridiana
y la circunferencial, son σt, y se comparan las dos. u_R, en todos los nudos sobre R = a.
Tolerancia de D4: **0.5 %** en los dos.

## Malla y elemento con que se fija la tolerancia

T6 con la regla de 7 puntos (D1) (`ogr_fem2d.engine.mesh_radial.quarter_annulus`): **16 divisiones
radiales, 4 angulares, crecimiento 1.69^½ = 1.3** (primer elemento de 0.092 m). Estudio de
convergencia con la familia anidada 2 × 8, 4 × 16, 8 × 32 (n_θ × n_R; crecimiento 1.69^(1/2^k),
cada refinamiento parte cada elemento en cuatro):

| Malla | T6: σt (primer anillo) | T6: u_R(a) | T3: σt | T3: u_R(a) |
|---|---|---|---|---|
| 2 × 8 | 1.416 % | 0.936 % | 7.35 % | 8.98 % |
| 4 × 16 | **0.341 %** | **0.130 %** | 3.71 % | 3.16 % |
| 8 × 32 | 0.089 % | 0.037 % | 1.66 % | 1.10 % |
| 16 × 64 | — | — | 0.73 % | 0.34 % |
| 32 × 128 | — | — | 0.36 % | 0.10 % |

La de 4 × 16 es la primera con T6 que cumple las dos tolerancias. Frente a la solución exacta del
modelo con el exterior fijo (identidad: solo discretización), el error del T6 baja ×4 en σt y ×6–8
en u_R con cada refinamiento, y la distancia entre las dos referencias es la del contorno, 0.01–0.02 %.

El T3, que es lo que usa la ficha, converge con orden 1 en las tensiones (el error se reduce a la
mitad en cada refinamiento) y solo cumple la tolerancia en 32 × 128 (16 384 elementos, 39 s con la
referencia en Python). Por la regla 9 el caso queda fijado con T6; un caso con T3 sería otro caso.
