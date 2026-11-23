# 007 — Cavidad esférica en un medio elástico, con malla general y por el modelo (Lamé)

| Campo | Valor |
|---|---|
| Ficha de trabajo | `VER-STR-09` (en `../Referencias/Ejemplos/Casos_por_problema/`) |
| Fuente científica | Lamé (1852), en Timoshenko y Goodier (1951), *Theory of Elasticity*, 2.ª ed., §121, ecs. (197)–(198), págs. 358–359; u_R por la ley de Hooke (§6) (la del caso 003) |
| Tipo de referencia | analítica |
| Tipo de análisis | axisimetría; elástico lineal; una fase de excavación |
| Modelo | `modelo.ogrfem2d` (spec 004) |

El caso 003 con la **malla general** de la spec 003 y **por el modelo** de la spec 004 (D4): los arcos
de la cavidad y de la esfera exterior, la axisimetría, las condiciones por tramo y la excavación como
región que la fase desactiva. El caso 003 no cambia (regla 9).

> **Estado (2026-11-23): tolerancia escrita antes de medir, malla a `null`.** La fija su estudio.

## Geometría, material, tensión inicial y condiciones

Las del caso 003, en el plano meridiano (x = r ≥ 0, y = z ≥ 0): la cavidad de radio a = 1 m y la esfera
exterior de radio b = 21 m, cada una un arco de 90° de centro el origen. La cavidad es una región, el
cuarto de disco, **excavada en la única fase**. E = 20 000 MPa, ν = 0.2. Tensión inicial hidrostática
de 10 MPa de compresión en las tres direcciones (10 000 kPa).

- Tramo y = 0 (de (0, 0) a (b, 0)): restricción en y (simetría).
- Eje x = 0 (de (0, b) a (0, 0)): libre; el motor sujeta u_r = 0 en el eje (spec 002, D1 bis).
- Esfera exterior: el defecto del contorno externo, fija en x e y.

## Valor esperado y de dónde sale

El del caso 003, con compresión positiva y u_R positivo hacia el centro: σt = P0 (1 + a³/(2R³)), 15
MPa en R = a, y u_R(a) = 0.0003 m (`sphere_infinite` de la spec 002). Se compara el **peor** punto:
σt, la meridiana y la circunferencial, en todos los puntos de integración de los **elementos activos
con un lado sobre la cavidad**, cada uno contra la solución en su radio (la regla de 7 puntos del T6 en
axisimetría no pone ninguno sobre la cavidad), y u_R en todos los nudos sobre R = a, esquinas e
intermedios. **Tolerancia: 0.5 %**, la del caso 003 (spec 002, D4).

Con el exterior fijo a 21 m la solución exacta del modelo se aparta de la de medio infinito un 0.022 %
en u_R(a) y un 0.011 % en σt(a) (caso 003).

## Malla y elemento con que se fija la tolerancia

Por fijar en su estudio (spec 004, T17).
