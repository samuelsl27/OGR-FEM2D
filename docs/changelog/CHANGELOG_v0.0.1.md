# OGR FEM2D v0.0.1 (en curso)

**Fase 0: la prueba de concepto del motor** (spec 001). Esta entrada se completa al cerrar la
versión, registrando **qué se encontró**.

## 0. Lo que se encontró (hasta ahora)

- **Tarea T1, las fuentes** (`spec/features/001-prueba-de-concepto/plan.md`, «Formulación»):
  - el desplazamiento del hueco en Mohr-Coulomb con dilatancia no nula no está impreso en Salençon
    (1969); la fórmula de la ficha coincide a 1e-12 con la integración de su modelo en pequeñas
    deformaciones, y ese es su respaldo;
  - con el contorno a 21 m (la geometría de las fichas), la solución exacta del modelo ya se aparta
    de las fórmulas de medio infinito en ur(a) un 0.60 % (Kirsch) y hasta un 1.83 % (Salençon); la
    spec decía «en torno a un 0.2 %» sin haberlo calculado. De ahí D3 bis: casos a 100 m y la
    identidad del anillo de 21 m.
- **Tarea T3, el entorno**: el núcleo se fija a `ogr-core` v0.1.0 y el runner se niega a medir
  contra cualquier otra versión, en particular contra el `ogr_core` de OGR Slip2D, que tiene el
  mismo nombre de paquete. La primera versión del envoltorio fallaba con un `ModuleNotFoundError`
  confuso en ese caso; ahora lo explica y sale con 2.
- **Tarea T4, el T6**: la cuadratura cuadrática de la tabla 9.2 de Zienkiewicz y Taylor (2000)
  pone los puntos en el centro de los lados; con los nudos intermedios del hueco sobre el círculo,
  hay puntos de integración exactamente en r = a.
- **Tarea T5, el Mohr-Coulomb**: el Box 8.6 de de Souza Neto et al. (2008) tiene una errata en σ1
  de la arista izquierda (Δγb por Δγa; la ec. 8.78 y su propia subrutina SUMC están bien), y el
  criterio de elección de arista solo se pudo fijar con la subrutina. Por eso cada retorno se
  construye desde la ec. (8.68) y los vectores de flujo, y los tests comprueban las ecuaciones de
  los planos: una comprobación con errores introducidos a propósito confirma que los cazan.
- **Tarea T6, la malla radial**: el área de la malla no es la de la corona (los arcos son parábolas)
  pero se conoce exacta, por la cuadratura de la parábola de Arquímedes, y la cuadratura del T6 la
  da a 1e-16; la diferencia con π(b² − a²)/4 baja como Δθ⁴. Una mutación sobrevivió a los primeros
  tests (el nudo intermedio de un lado radial fuera de su centro: no cambia el área ni invierte
  nada), y se añadió el invariante que define la construcción: en polares, cada nudo intermedio es
  la media de sus esquinas. Con la diagonal recta, la malla de una sola división angular sale con
  un elemento degenerado; la construcción polar lo evita.
- **Tarea T7, los escalones y las iteraciones**:
  - la (4.77) de de Souza Neto et al. (2008) divide el residuo por ‖f_ext‖, que al final de una
    excavación es cero (el hueco queda libre): se divide por la norma de la carga de la fase, el
    término de tensión inicial de la (2.13b) de Zienkiewicz y Taylor (2000);
  - la identidad de la carga de la excavación (resultante P0·a sobre el arco del hueco) falló la
    primera vez por una cuenta incompleta del test, no del código: los nudos extremos del hueco
    reciben además la parte del lado radial del eje en el que están, P0·(r1 − a)/6;
  - **la rigidez inicial converge muy despacio en Mohr-Coulomb, y empeora al refinar la malla**
    (anillo de 21 m, cinco escalones, tolerancia 1e-8; factor de reducción del residuo por
    iteración en el último escalón): con ψ = 0°, 0.965 en la malla de 4 × 12 divisiones (521
    iteraciones) y 0.9966 en la de 8 × 24 (4873 iteraciones, 141 s en Python); con ψ = 30°, 0.996
    ya en la de 4 × 12 (4170 iteraciones). Con un factor tan cerca de 1, además, un residuo pequeño
    no asegura un desplazamiento preciso (el error en u va como r/(1 − ρ)). Con mallas de la
    finura que piden las tolerancias de D3, el oráculo en Python tardaría decenas de minutos por
    caso. **Pendiente de decisión del propietario** (cambia el plan, «Iteraciones»);
  - con mallas gruesas el Mohr-Coulomb da mucha dispersión en ur(a) entre nudos vecinos del hueco
    (±10 % con ψ = 0° y −35/+56 % con ψ = 30° en la de 4 × 12, donde la zona plástica ocupa uno o
    dos elementos); con la de 8 × 24 y ψ = 0° baja a +0.4/+2.2 %. Es error de discretización que
    baja con la malla, no un defecto visto hasta ahora, pero obliga a mallas finas cerca del hueco.

