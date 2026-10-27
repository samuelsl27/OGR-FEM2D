# 002 — Hueco circular en Mohr-Coulomb perfectamente plástico (Salençon)

| Campo | Valor |
|---|---|
| Ficha de trabajo | `VER-STR-02` (en `../Referencias/Ejemplos/Casos_por_problema/`) |
| Fuente científica | Salençon (1969), «Contraction quasi-statique d'une cavité à symétrie sphérique ou cylindrique dans un milieu élasto-plastique», *Annales des Ponts et Chaussées*, IV, págs. 231–236: §3 y §5, ecs. (2″), (3″) y (9″), pág. 235; para la zona de arista, de Souza Neto, Perić y Owen (2008), ecs. (8.58)–(8.59) (spec 001, D8) |
| Tipo de referencia | analítica |
| Tipo de análisis | deformación plana; Mohr-Coulomb perfectamente plástico, ψ = 0° y ψ = 30°; una fase de excavación |

## Geometría, contorno, tensión inicial y fase

Las del caso 001: a = 1 m, cuarto de corona hasta **b = 100 m**, rodillos en los ejes, contorno
exterior fijo, 30 MPa hidrostáticos de compresión, excavación sin presión interior. A 100 m el
contorno aparta la solución exacta del modelo de la de medio infinito un 0.063 % (ψ = 0°) y un
0.082 % (ψ = 30°) en ur(a) (`salencon_finite`).

## Materiales y parámetros

E = 10 000 MPa, ν = 0.2, c = 3.45 MPa, φ = 30°; dos variantes: ψ = 0° (no asociado) y ψ = 30°
(asociado).

## Valor esperado y de dónde sale

- R0 = **1.734998 m**, de la (3″) despejada para el radio plástico; no depende de ψ.
- **La hipótesis de Salençon no se cumple cerca de la pared.** Supone que σz es la tensión
  principal intermedia (§5, ec. 4″). Con estos datos, sin deformación plástica en z, σz llegaría
  a 20.39 MPa en la pared, por encima de σθ = 11.95 MPa: para r < r_e = **1.2814 m** el material
  está en la arista σz = σθ y la deformación plástica tiene componente z. Las tensiones σr, σθ y
  R0 no cambian (el equilibrio no ve σz); el desplazamiento sí.
- ur(a), positivo hacia el centro, de la solución exacta del modelo (D8,
  `salencon_edge_infinite`): **0.0083175 m** (ψ = 0°) y **0.0194475 m** (ψ = 30°). Con εz = 0, el
  flujo de la arista da k εp_r + εp_θ = e_z, que sin arista es la ecuación de Salençon; los
  multiplicadores salen ≥ 0 en toda la zona plástica.
- Dato informativo, Salençon (1969) con su hipótesis: 0.008236 m (ψ = 0°; con k = 1 coincide con
  su fórmula publicada linealizada) y 0.019086 m (ψ = 30°), un 0.99 % y un 1.90 % menos.
- Se comprueba en el modelo que los puntos plastificados con r < r_e están en la arista y los demás
  en el plano principal.

Tolerancias de D3: **2 %** en ur(a), en el peor nudo del hueco, y **R0 dentro de un tamaño de
elemento** (el radio del punto de integración plástico más alejado frente a R0, con la longitud
radial del elemento que contiene R0).

## Malla y elemento con que se fija la tolerancia

**Pendiente del estudio de convergencia** (malla y escalones). Las tolerancias están escritas antes
del estudio (commit 962f504) y no cambian; los valores de ur(a) se cambiaron por D8, también
antes del estudio.
