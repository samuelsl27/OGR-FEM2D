# Plan de implementación — Spec 003, malla

> **Aprobado (2026-11-22)**, con D1–D13 de `spec.md` y la enmienda de RF-5 (abajo, «Anomalías»;
> las dos ya anotadas en la spec). Ninguna fórmula se programa antes de estar en la tabla
> «Formulación» como leída.

## Enfoque

0. **v0.0.7, antes de la spec (D1)**: la fijación sube a `ogr-core` v0.2.3, como pide
   `Promts_desarrollo/2026_11_20_subir_a_ogr_core_0.2.3.md` (con las reglas de hoy, no las de ese
   escrito). Versión propia, con su changelog. Tras el commit, avisar de la fila de
   `docs/consumidores.md` en OGR-Core.
1. **La petición a OGR-Core (D2a)**: un escrito para su sesión (abajo, «Lo que se pide a
   OGR-Core»), en `Promts_desarrollo/`. Lo lleva la propietaria. El núcleo lo hace en una rama corta
   con su PR, y aquí se prueba con `--dev-core` mientras no esté etiquetado.
2. **Lo de FEM2D que no espera al núcleo**, en `ogr_fem2d/mesh/` (fuera del motor, regla 11):
   la discretización de contornos con arcos (paso 1), el paso de T3 a T6 con los nudos sobre los
   arcos, las comprobaciones (jacobiano, conformidad, conexión, Euler), la malla radial y la
   conversión a `EngineModel`. Se prueban sobre mallas T3 que ya existen (las estructuradas de la
   spec 002 y `generate_mesh` del núcleo), que no dependen de la petición.
3. **Lo que usa el generador nuevo**: las cotas de tamaño (uniforme, graduada, ventanas), el
   mallador completo de dos pasos y el resumen de calidad, primero contra el núcleo en desarrollo y
   al final contra la versión etiquetada, que se fija en un commit propio.
4. **El caso 005** con su estudio de convergencia y la identidad de Kirsch, y la malla radial contra
   el anillo exacto.

## Lo que se pide a OGR-Core (D2a)

Una función **nueva** en `ogr_core.fem`; `generate_mesh` no se toca y Slip2D sigue bit a bit.

- **Entrada**: un PSLG (vértices y segmentos, cada segmento con la etiqueta del segmento de origen),
  puntos semilla de cada región para el material, puntos en los huecos que no se mallan, la cota B
  del cociente circunradio / lado más corto (por defecto √2) y una cota de tamaño opcional como
  función de la posición (longitud máxima de lado o área máxima de un triángulo).
- **Algoritmo**: refinamiento de Delaunay de Ruppert en la versión de Shewchuk (2002a): §3.1
  (invasión de subsegmentos con prioridad, circuncentros de los triángulos flacos, rechazo del
  circuncentro que invade), con la división en capas concéntricas de §6.2 y el «Terminator» de §6.3
  para los ángulos de entrada de 60° o menos, y las indicaciones del apéndice A. Parte de un Delaunay
  sin restricciones y recupera los segmentos partiéndolos (§3.1, pág. 7): sin dependencias nuevas.
- **Salida**: la malla T3 (`Mesh`, nudos en sentido antihorario), y para cada segmento de entrada la
  lista ordenada de sus vértices; las notas: cota B, cota de tamaño, vértices añadidos en cada
  segmento, triángulos que quedan flacos por un ángulo de entrada pequeño y dónde.
- **Medidas de calidad** por triángulo, en `ogr_core.fem.mesh`: ángulos mínimo y máximo y las dos de
  la tabla 4 de Shewchuk (2002b) que fije D7, normalizadas a 1 en el equilátero.
- **Determinista**: la misma entrada da la misma malla, bit a bit (D11).
- **Tests que lo demostrarían**, todos contra la fuente: la cota B en PSLG con ángulos ≥ 60°
  (teorema 4); la cota del teorema 12 con un ángulo de entrada de 5°, y que termina (teorema 11; el
  PSLG de la fig. 20, con el que Ruppert sin más no termina); la distancia al vecino más próximo
  ≥ lfs/(D_S + 1) con B > √2 (teorema 8); círculos circunscritos vacíos en la malla final (pág. 9);
  cada segmento es unión de lados; área exacta; la cota de tamaño cumplida; las medidas valen 1 en
  el equilátero, 0 en el degenerado, son negativas en el invertido e invariantes con la escala y el
  giro (§6.3, propiedades 1–4); la suite de Slip2D, sin cambios.
- **Por qué en el núcleo**: es mallado genérico, y la filtración de Slip2D lo necesita igual (el
  ángulo de 4.9° del sondeo es su malla). Hecho aquí sería una segunda copia que diverge (ADR-0002).
- El escrito incluye el hallazgo de `generate_mesh` (cae muy por debajo de su propio suelo de 25°),
  como nota para su sesión, sin pedir que lo cambie.

## Archivos que se tocan (FEM2D)

| Archivo | Qué es | RF |
|---|---|---|
| `ogr_fem2d/mesh/__init__.py` (nuevo) | el paquete de mallado, fuera de `engine/` | — |
| `ogr_fem2d/mesh/geometry.py` (nuevo) | la entrada: regiones, segmentos con arco opcional, parámetros; su validación con errores que dicen dónde | RF-1 |
| `ogr_fem2d/mesh/discretize.py` (nuevo) | paso 1: nudos de cada segmento; los arcos, con sus nudos sobre la circunferencia; número de divisiones forzado | RF-2, D10 |
| `ogr_fem2d/mesh/sizing.py` (nuevo) | las cotas de tamaño: uniforme, graduada (cota máxima opcional), ventanas y polígonos | RF-5 a RF-7, D5, D9 |
| `ogr_fem2d/mesh/quadratic.py` (nuevo) | T3 → T6: un nudo intermedio por lado, sobre el arco en los lados de un arco (D4) | RF-10 |
| `ogr_fem2d/mesh/checks.py` (nuevo) | jacobiano del T6, conformidad, Euler, conexión, regiones unidas por un nudo | RF-13, RF-14 |
| `ogr_fem2d/mesh/radial.py` (nuevo) | malla radial del anillo completo (no es `engine/mesh_radial.py`, que se queda para los casos 001 y 002) | RF-8, D8 |
| `ogr_fem2d/mesh/mesher.py` (nuevo) | los dos pasos de principio a fin y la salida: nudos, elementos, material, mapa segmento → nudos y lados, notas | RF-3, RF-11, RF-15 |
| `docs/malla/entrada.md` (nuevo) | la entrada y la salida documentadas, como `docs/motor/entrada.md` | RF-1, RF-15 |
| `spec/features/003-malla/comprobaciones/soluciones_cerradas.py` (nuevo) | Kirsch con campo no hidrostático: el desplazamiento que causa la excavación | caso 005 |
| `validacion/casos/005-kirsch-malla-general/` (nuevo) | `caso.md`, `esperado.json` | D12 |
| `tests/test_mesh_*_v008.py` (nuevos) | ver «Estrategia de pruebas» | todos |
| `pyproject.toml` | la fijación del núcleo, dos veces: v0.2.3 (v0.0.7) y la versión que traiga la petición | D1, D2 |
| `docs/changelog/CHANGELOG_v0.0.7.md`, `CHANGELOG_v0.0.8.md` | qué se encontró | — |

`rust/` y la CI no se tocan: no hace falta rama corta. El motor (`ogr_fem2d/engine/`), tampoco.

## Formulación

Fuentes en `../Referencias/Bibliografia/` (índice en su `00_LEEME.md`). Las de Shewchuk, con la
página del preprint; las fórmulas, leídas sobre la página renderizada.

| Qué | Fuente | Dónde | Estado |
|---|---|---|---|
| Cota de calidad y ángulo mínimo | Shewchuk (2002a) | §2, pág. 5: un triángulo con circunradio / lado más corto ≤ B no tiene ángulos menores que arcsin(1/2B); Ruppert usa B = √2 → ángulos entre 20.7° y 138.6° | **Leído** |
| Refinado de Ruppert | Shewchuk (2002a); Ruppert (1995) | §3.1, págs. 7–11: subsegmento invadido si un vértice cae en su círculo diametral y es visible; se parte por el punto medio, con prioridad; el triángulo flaco se parte por su circuncentro salvo que invada, y entonces se parten los subsegmentos invadidos; lema 1 (pág. 9): sin subsegmentos invadidos, el circuncentro está dentro; la malla final es de Delaunay (pág. 9) | **Leído.** Ruppert (1995), en preprint, solo hojeado |
| Terminación | Shewchuk (2002a) | Teorema 4, pág. 16: termina con B ≥ √2 y ángulos de entrada ≥ 60° | **Leído** el enunciado y el diagrama de la fig. 13; la prueba, no |
| Cota de tamaño según la posición | Shewchuk (2002a) | §3.1, pág. 11: el usuario puede dar una cota de área o de lado que dependa de la posición; si está acotada por debajo por una constante positiva, la terminación no se pierde | **Leído** |
| Graduación | Shewchuk (2002a) | §3.2, pág. 11 (tamaño local de rasgo, lfs); teorema 8 (Ruppert), pág. 23: distancia de cada vértice a su vecino más próximo ≥ lfs(v)/(D_S + 1), con D_T = (B+1)/(B−√2), D_S = (1+√2)B/(B−√2), o D_S = 1/(1 − 2 cos α_min), D_T = 1 + D_S/B; exige **B > √2 estrictamente** y α_min > 60° | **Leído.** Anomalía en RF-4/RF-5 (abajo) |
| Ángulos de entrada pequeños | Shewchuk (2002a) | §5, pág. 27 (no siempre hay malla sin ángulos nuevos pequeños); §6.2, págs. 29–31 (capas concéntricas de radio potencia de dos); §6.3, págs. 33–35: el Terminator, condiciones A–F; teorema 11 (siempre termina) y teorema 12: con φ ≤ 60° el menor ángulo de entrada, circunradio / lado más corto ≤ 1/(√2 sin(φ/2)), luego ningún ángulo menor que arcsin(sin(φ/2)/√2) | **Leído** el algoritmo y los enunciados; la prueba del teorema 12 y el apéndice A, no (son de la sesión de OGR-Core) |
| Medidas de calidad del triángulo | Shewchuk (2002b) | Tabla 1, pág. 3 (notación: A con signo, ℓrms = √(Σℓᵢ²/3), r_in = 2A/(ℓ1+ℓ2+ℓ3)); tabla 4, pág. 44. Gradiente: A/(ℓmáx ℓmed (ℓmín + 4\|r_in\|))^(2/3), suave A/(ℓ1ℓ2ℓ3)^(2/3). Condicionamiento: A/(3ℓ²rms + √((3ℓ²rms)² − 48A²)), suave A/ℓ²rms. §6.3, pág. 51: propiedades de una medida «justa» (Field) | **Leído.** Propuesta para D7: las **exactas**, no las suaves (pág. 46: las suaves son «menos precisas» y están pensadas para optimizar, que aquí no se hace). Normalización (propia, aritmética): en el equilátero de lado 1, la de gradiente vale (√3/4)/(1 + 2√3/3)^(2/3) y la de condicionamiento √3/12 (el radicando se anula) |
| Ángulos del triángulo | — | Ley del coseno (geometría elemental) | — |
| Malla uniforme por número de elementos | — | h² = 4A/(√3 N), el área del triángulo equilátero (la misma cuenta que `generate_mesh`) | — |
| Elemento curvo válido | Zienkiewicz y Taylor (2000) | §9.2, págs. 205–206: la transformación es biunívoca si el determinante del jacobiano conserva el signo en todo el elemento; en los parabólicos, nudo intermedio en la mitad central del lado, más seguro el tercio central (fig. 9.6). §9.5, ecs. (9.10)–(9.11), págs. 208–209: la matriz jacobiana | **Leído.** El det J del T6 es un polinomio de grado 2, que la interpolación cuadrática por los seis nudos reproduce exacto; su **mínimo sobre todo el elemento** se halla exacto (vértices, extremo de la parábola de cada lado, punto estacionario interior: cálculo elemental), y además se mira en los nudos y en los puntos de integración del motor. *Enmendado en la T6 (2026-11-22): decía solo «nudos y puntos de integración» y que una garantía en todo el elemento no se afirmaba; un T6 con det J > 0 en sus seis nudos puede plegarse por dentro, y en deformación plana sus puntos de integración son los nudos intermedios, así que el motor lo calcularía sin verlo (changelog v0.0.8, T6)* |
| Nudo intermedio sobre el arco | — | Punto medio del arco entre los dos nudos de esquina: c + R·(m − c)/\|m − c\|, con m el punto medio de la cuerda (arco menor de 180°) | Geometría elemental; es la construcción de `mesh_radial.py`, validada en la spec 001 |
| Área de un T6 con un lado parabólico | — | Área del triángulo rectilíneo ± 2/3·cuerda·flecha (cuadratura de la parábola, Arquímedes) | Usada en la spec 001 (T6, changelog v0.0.1) |
| Parcela con elementos curvos | Zienkiewicz y Taylor (2000) | §9.7, teorema 3, págs. 213–214, ecs. (9.23)–(9.25): todo elemento isoparamétrico reproduce exacto un campo lineal, porque Σ Nᵢ = 1 | **Leído** |
| Kirsch, campo hidrostático | Jaeger, Cook y Zimmerman (2007) | §8.4, ecs. (8.90)–(8.92), pág. 216, con la corrección de signo de la spec 001 | **Leído** (spec 001) |
| Kirsch, campo no hidrostático | Jaeger, Cook y Zimmerman (2007) | §8.5, tensiones (8.113)–(8.116), pág. 219; desplazamientos (8.121)–(8.125), págs. 220–221: 8G u_r/(aσ₁) = [(κ−1)(r/a) + 2(a/r)] + 2[(r/a) + (κ+1)(a/r) − (a/r)³] cos 2θ, 8G u_θ/(aσ₁) = −2[(r/a) + (κ−1)(a/r) + (a/r)³] sin 2θ, κ = 3 − 4ν; σ₂ girando 90° | **Leído.** El desplazamiento **que causa la excavación** es el de (8.122) menos el del medio sin hueco (A = B = C = 0): 8G u_r/(aσ₁) = 2(a/r) + 2[(κ+1)(a/r) − (a/r)³] cos 2θ, 8G u_θ/(aσ₁) = −2[(κ−1)(a/r) + (a/r)³] sin 2θ. Derivación propia; con σ₁ = σ₂ = p da p a²/(2G r), la (8.90). Se comprueba en `comprobaciones/` |
| Característica de Euler | — | En una malla plana conexa con H huecos sin mallar, V − E + T = 1 − H | Teorema clásico (Euler); no está en la bibliografía |

**Convenio:** Jaeger et al. trabajan con compresión positiva; el motor, con tracción positiva
(regla 10). La conversión va en un solo sitio, en `comprobaciones/`, como en la spec 001.

## Anomalías (regla 6: se reportan antes de corregirlas)

- **Error propio en RF-4 y RF-5 de la spec.** RF-5 dice que la graduación de la malla graduada tiene
  fuente con la cota por defecto, B = √2. El teorema 8 (pág. 23) exige **B > √2 estrictamente**: en
  √2 las constantes D_T y D_S son infinitas y la garantía de graduación desaparece (la de terminación
  y la del ángulo, teorema 4, se mantienen). La fuente añade que en la práctica gradúa mucho mejor
  que la cota. Enmienda (decidida por la propietaria el 2026-11-22, ya en la spec):
  - **por defecto B = √2**: el ángulo mínimo garantizado (20.7°) y la terminación, que es lo que
    más importa;
  - RF-5 dice que la graduación se **mide** (el test del teorema 8 se hace con B > √2, por ejemplo
    B = 1.93, ángulo de 15°, que da D_S ≈ 9.01 en la fuente) y que con B = √2 no está garantizada.
- **D13 (nueva): vértices añadidos sobre las cuerdas de un arco.** Un arco entra al refinado como
  una cadena de cuerdas. Si el refinado parte una cuerda (D10 lo permite), el vértice nuevo cae
  sobre la cuerda y no sobre el arco, y el nudo intermedio del T6, que sí va sobre el arco, deja el
  lado mal representado. Decidido (2026-11-22, como se propuso): después de mallar, **llevar al arco** (radialmente desde el
  centro) cada vértice añadido sobre una cuerda, comprobar después el jacobiano de los elementos
  afectados (RF-13) y decir cuántos se movieron (regla 12). La alternativa, prohibir partir las
  cuerdas, deja sin garantía de calidad los elementos junto al arco (D10).

## Decisiones de diseño

- **Lo que hace cada lado.** El núcleo malla un PSLG en T3 con calidad garantizada; FEM2D decide qué
  PSLG (contornos, arcos, discretización) y qué cotas (tipo de malla, ventanas), y convierte el
  resultado en T6 y en la entrada del motor. El motor no cambia.
- **La graduada, sin factor de graduación (D5)**: los nudos de las excavaciones se reparten entre sus
  segmentos en proporción a su longitud (al menos una división por segmento); los demás segmentos
  entran solo con sus extremos, y el refinado gradúa. Sin excavaciones, lo mismo con el contorno
  exterior.
- **Uniforme**: cota de longitud de lado h en todo el dominio, y los segmentos discretizados a h.
- **Ventanas y polígonos (D9)**: la cota en un punto es la menor de las que lo cubren.
- **T6 después del T3**: el refinado trabaja con triángulos rectos (la fuente no trata las curvas,
  Shewchuk 2002a, pág. 1). El nudo intermedio se añade después: en el punto medio del lado, o sobre
  el arco (D4). La numeración: primero los nudos de esquina, en el orden del núcleo; después los
  intermedios, en el orden en que aparece cada lado recorriendo los elementos.
- **La malla radial** no pasa por el refinado: es estructurada, con progresión geométrica en el radio
  como `engine/mesh_radial.py`, pero del anillo completo y con la salida común del mallador.
- **Determinismo (D11)**: ningún paso usa azar ni el orden de un `set`.
- **Las mallas de prueba de la spec 002 no se tocan**: los casos 001 a 004 siguen con ellas.

## Estrategia de pruebas

| Nivel | Test | Invariante |
|---|---|---|
| Entrada | Cada regla de validación de la geometría con una entrada que la incumple | el error dice el sitio y la regla |
| Discretización | Número de nudos por segmento (forzado y repartido), extremos compartidos, nudos de un arco sobre la circunferencia | el paso 1 hace lo que dice |
| T6 | Un nudo intermedio por lado, compartido; en el punto medio o sobre el arco (\|x − c\| = R a redondeo); área: rectilíneo ± 2/3·c·s | RF-10 |
| Jacobiano | Un T6 con el nudo intermedio desplazado fuera de la mitad central se rechaza con su motivo; uno dentro del tercio central pasa | RF-13 |
| Topología | Conformidad, Euler (V − E + T = 1 − H), lados de contorno = subsegmentos; dos regiones unidas por un nudo, avisadas | RF-14 |
| Parcela | Campo lineal exacto en mallas generadas, T3 y T6 con lados curvos, deformación plana y axisimetría (Z&T §9.7, teorema 3) | la malla es válida para el motor |
| Cotas | Cota B (teorema 4), cota de tamaño, Delaunay final; con B = 1.93, el teorema 8; con un ángulo de entrada de 5°, el teorema 12 y que termina | las garantías de la fuente, vistas desde FEM2D (los tests del núcleo son de su sesión) |
| Calidad | Medidas en el equilátero (1), degenerado (0) e invertido (< 0); invariantes con la escala | RF-12 |
| Radial | Nudos en r_k de la progresión; caso de la malla radial contra `lame_fixed_outer`, 0.5 % | RF-8 |
| Determinismo | Dos mallados de la misma entrada, iguales bit a bit | RF-11 |
| Caso | 005 con su tolerancia (D12) y el estudio con 16, 32, 64 y 128 divisiones del hueco | STR-01 con malla general |
| Identidad | Kirsch con el desplazamiento de la excavación impuesto en el contorno, hidrostático y con p2 = p1/2, misma malla del 005 | discretización sola; la diferencia con el 005 es el efecto del contorno |
| Regresión | Casos 001 a 004, bit a bit | no se toca lo validado |

Cada test con su cabecera (qué invariante protege) y con dientes: una mutación sistemática por
invariante (`{etiqueta: (archivo, texto, sustituto)}`), anotada en `tasks.md`.

## Riesgos

| Riesgo | Cómo se detecta o se acota |
|---|---|
| La spec espera a una versión del núcleo (D2a) | Lo de FEM2D que no depende del generador va primero (paso 2 del enfoque); el resto, con `--dev-core` contra la rama del núcleo |
| El refinado en Python puro es lento con decenas de miles de elementos | Se mide en el caso 005 y en el mayor de los casos de la fase 1; el plan de desarrollo ya prevé Rust (`spade`) solo si se mide que hace falta |
| El Delaunay de SciPy (Qhull) no es incremental ni da adyacencias para el refinado | Lo decide la sesión del núcleo (el apéndice A de Shewchuk 2002a trata la estructura de datos); aquí solo se pide que no añada dependencias |
| Las mallas de Delaunay no están anidadas y el error puede no bajar en cada refinamiento | Se reporta como hallazgo; la malla del caso no se elige a dedo (spec, «Validación») |
| Mover al arco los vértices añadidos en una cuerda (D13) invierte un elemento | Se comprueba el jacobiano de los afectados; si pasa, es un hallazgo y se para |
| El determinismo depende de Qhull | Test de dos mallados bit a bit, y en las tres plataformas por la CI |
| El teorema 12 da ángulos muy pequeños con ángulos de entrada pequeños (φ = 5° → 1.8°) | Es lo que dice la fuente; el resumen de calidad lo muestra y dice por qué |
