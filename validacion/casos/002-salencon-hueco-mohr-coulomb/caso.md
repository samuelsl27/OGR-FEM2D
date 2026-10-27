# 002 — Hueco circular en Mohr-Coulomb perfectamente plástico (Salençon)

| Campo | Valor |
|---|---|
| Ficha de trabajo | `VER-STR-02` (en `../Referencias/Ejemplos/Casos_por_problema/`) |
| Fuente científica | Salençon (1969), «Contraction quasi-statique d'une cavité à symétrie sphérique ou cylindrique dans un milieu élasto-plastique», *Annales des Ponts et Chaussées*, IV, págs. 231–236: §3 y §5, ecs. (2″), (3″) y (9″), pág. 235 |
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
- ur(a), positivo hacia el centro: **0.008236 m** (ψ = 0°) y **0.019086 m** (ψ = 30°). Salençon
  (1969) solo imprime el desplazamiento para k = 1 (ψ = 0°) y en grandes deformaciones; el valor es
  la integración de su modelo en pequeñas deformaciones (su flujo εpθ = −k εpr), que con ψ = 0°
  coincide con la fórmula publicada linealizada (plan, «Formulación», y
  `comprobaciones/soluciones_cerradas.py`).
- Salençon supone que σz es la tensión principal intermedia (§5, ec. 4″): se comprueba en todos
  los puntos plastificados del modelo.

Tolerancias de D3: **2 %** en ur(a), en el peor nudo del hueco, y **R0 dentro de un tamaño de
elemento** (el radio del punto de integración plástico más alejado frente a R0, con la longitud
radial del elemento que contiene R0).

## Malla y elemento con que se fija la tolerancia

**Pendiente.** Las tolerancias están escritas antes del estudio (commit 962f504). La iteración ya
no es obstáculo (D7), pero el estudio destapó que **la hipótesis de Salençon no se cumple** con
estos datos: cerca de la pared (r < 1.281 m) σz sería la principal mayor, y el material está en la
arista σz = σθ. Las tensiones σr, σθ y R0 de Salençon siguen siendo las del modelo, pero ur(a) del
modelo es un 0.99 % (ψ = 0°) y un 1.90 % (ψ = 30°) mayor (changelog v0.0.1). El valor de
referencia de ur(a) espera la decisión del propietario.
