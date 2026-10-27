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
  - con diagonales alternas (prueba aparte, no en el código) la dispersión del Mohr-Coulomb se
    ordena: los nudos intermedios del hueco salen bien (−1.9 % y +0.3 % en la malla de 4 × 12) y
    son las esquinas las que oscilan (hasta −22/+30 % con ψ = 30°). En todos los puntos plásticos
    σz es la intermedia y f = 0 a 1e-12: el material hace lo que debe. La firma es la de un
    bloqueo del T6 por la restricción del flujo plástico; está por respaldar con una fuente.
- **Tarea T8, parte elástica**: el anillo de 21 m contra `lame_fixed_outer` converge limpio, con
  orden ≈ 2.9 en ur y 1.5–1.9 en σθ en los puntos de integración del hueco (Zienkiewicz y Taylor
  2000, §14.1, dan O(h²) para las tensiones del elemento cuadrático). Con gradación √g y el doble
  de divisiones, las mallas quedan anidadas.
- **Tarea T9, caso 001 (Kirsch, 100 m)**: tolerancias escritas antes del estudio (commit
  962f504); la malla de 8 × 32 divisiones es la primera que cumple el 0.5 % de D3 en el peor
  punto (0.19 % en ur(a) y en σθ(a)); la de 4 × 16 se queda en 1.34 % y 0.59 %.
- **D7, Newton completo con la tangente consistente** (decidido tras la T7): la tangente del
  Mohr-Coulomb se construye desde las mismas ecuaciones lineales del retorno (con plasticidad
  perfecta cada retorno es afín en las tensiones de prueba) y coincide a 1e-15 con las expresiones
  de la subrutina CTMC de de Souza Neto et al. (2008) en el plano y en las dos aristas, y a 1e-10
  con la derivada numérica de la actualización en las cinco regiones, también con valores
  principales repetidos (ec. A.30). Newton da la misma solución discreta que la rigidez inicial
  en 6–8 iteraciones por escalón, con convergencia cuadrática.
- **La hipótesis de Salençon no se cumple en el caso STR-02** (pendiente de decisión del
  propietario). Con los datos de la ficha, si no hubiera deformación plástica en z, σz =
  p0 − ν(Δσr + Δσθ) llegaría a 20.39 MPa en la pared, por encima de σθ = 11.95 MPa: para
  r < 1.281 m, σz sería la principal mayor (en compresión), no la intermedia. El modelo lo resuelve
  como debe, con retorno a la arista (σz = σθ) en los puntos con r de 1.000 a 1.241 m y al plano
  de 1.306 a 1.721 m. Las tensiones σr y σθ y el radio plástico no cambian (el equilibrio no ve
  σz), pero el desplazamiento sí: la solución cerrada extendida con esa zona (el flujo de la
  arista, ecs. 8.58–8.59 de de Souza Neto et al., con εz = 0, da k εp_r + εp_θ = e_z) da ur(a)
  un **+0.99 % (ψ = 0°) y un +1.90 % (ψ = 30°)** por encima de Salençon en medio infinito, y en el
  anillo de 21 m un +1.93 % con ψ = 30°, que es lo que da el modelo con la malla de 32 × 96 (media
  +1.90 %). Con la tolerancia del 2 % de D3 frente a Salençon, ψ = 30° habría pasado por 0.1 %:
  una coincidencia sin razón. La primera comprobación de «σz intermedia» de esta sesión estaba
  mal planteada (contaba como intermedia una σz igual a otra principal, que es lo que pasa en la
  arista); se rehízo por regiones de retorno.
- **Newton sin control diverge con ψ = 0° y mallas finas**: en el anillo de 21 m con 16 × 48
  divisiones, en el último escalón (cuando la zona plástica crece de 272 a 555 puntos) el residuo
  sube a 2.6 y un iterado intermedio lleva un punto al vértice, que con ψ = 0° no tiene solución.
  Se añadió la partición automática del incremento de de Souza Neto et al. (2008), §5.4.3: el
  incremento que falla se parte en dos y se reintenta desde el último estado convergido, hasta
  `max_cuts` particiones sucesivas; el resultado dice cuántas hubo.
- **El resultado del Mohr-Coulomb depende del número de escalones**: en la malla gruesa del anillo
  con ψ = 0°, 1, 2 y 4 escalones dan lo mismo a 1e-15, pero 8 y 32 se apartan un 0.31 % y un
  0.17 % en ur(a). Un punto que ya está en el plano y acaba el incremento en la arista recibe una
  proyección de Euler implícito que solo es exacta dentro de una región. El número de escalones
  se fija, como la malla, con un estudio. Lo descubrió un test que comparaba la partición con 16
  escalones iguales y pasaba por coincidencia (los dos terminan con el mismo incremento); se
  rehízo para comprobar lo que es de principio.
