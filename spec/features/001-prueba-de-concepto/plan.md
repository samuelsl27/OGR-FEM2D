# Plan de implementación — Spec 001, prueba de concepto

> Borrador (2026-10-27), con las decisiones D1–D4 y D6 de `spec.md` tomadas. **Ninguna fórmula se
> programa antes de comprobarla contra su fuente original (tarea T1).** Donde abajo no se da
> ecuación ni página, es porque todavía no se ha leído la fuente.

## Enfoque

1. **Primero la referencia en Python** (RF-1, RF-2, RF-5, RF-7): el elemento T6, la ley elástica,
   el Mohr-Coulomb, la malla radial y el bucle de escalones e iteraciones, escritos para leerse. Se
   validan contra Kirsch, Lamé y Salençon, con el estudio de convergencia. Hasta que esto no pasa,
   no se escribe ni NumPy ni Rust: el oráculo tiene que estar validado contra algo externo antes de
   servir de oráculo.
2. **Después las otras dos variantes** (RF-3), con la misma interfaz, y la identidad con la
   referencia: punto material primero, malla después.
3. **Después las medidas** (RF-8) y la **distribución** (RF-9, RF-10).
4. **Al final, el informe** con los cinco criterios y la decisión del propietario.

La frontera Python ↔ Rust es la del ADR-0001: **una llamada por iteración global**. Python monta el
problema, ensambla la rigidez elástica una vez, resuelve con SuperLU y controla escalones e
iteraciones; en cada iteración llama una vez a la variante para «dado el incremento de
desplazamiento, actualiza las tensiones de todos los puntos de integración y devuelve el vector de
fuerzas internas».

## Archivos que se tocan

| Archivo | Qué es | RF |
|---|---|---|
| `pyproject.toml` | paquete `ogr-fem2d` con *backend* `maturin` (proyecto mixto Python + Rust), dependencia `ogr-core @ git+…@v0.1.0`, Python ≥ 3.11 | RF-9 |
| `ogr_fem2d/__init__.py` | paquete, versión | — |
| `ogr_fem2d/engine/reference/element_t6.py` | funciones de forma, matriz B, puntos de Gauss, rigidez, fuerzas internas | RF-1 |
| `ogr_fem2d/engine/reference/elastic.py` | matriz elástica de deformación plana | RF-2 |
| `ogr_fem2d/engine/reference/mohr_coulomb.py` | retorno en tensiones principales: plano, arista, vértice | RF-2, RF-4 |
| `ogr_fem2d/engine/reference/solver.py` | escalones de carga, iteraciones, criterio de convergencia, historia | RF-5, RF-6 |
| `ogr_fem2d/engine/mesh_radial.py` | malla radial estructurada de T6 de un cuarto de corona | RF-7 |
| `ogr_fem2d/engine/interface.py` | la interfaz común de las tres variantes | RF-3 |
| `poc/vectorized.py` | variante NumPy (solo para medir; D4) | RF-3 |
| `rust/` (`Cargo.toml`, `src/lib.rs`, `src/t6.rs`, `src/mohr_coulomb.rs`) | variante Rust con PyO3, módulo `ogr_fem2d._engine` | RF-3 |
| `poc/benchmark.py` | medida A/B en el mismo proceso | RF-8 |
| `poc/freeze/` | guion de PyInstaller y comprobación del ejecutable | RF-10 |
| `.github/workflows/wheels.yml` | ruedas con `maturin-action` en Windows, macOS ARM y Linux; tests en cada una | RF-9 |
| `tests/_runner.py` | envoltorio del runner de la suite (`ogr_core.testing.runner`): propio `ogr_fem2d`, compartido `ogr_core` fijado a 0.1.0 | — |
| `tests/test_*_v001.py` | tests (ver «Estrategia de pruebas») | todos |
| `validacion/casos/001-kirsch-hueco-elastico/`, `002-salencon-hueco-mohr-coulomb/` | `caso.md`, `esperado.json` (y modelo cuando exista el formato) | — |
| `docs/changelog/CHANGELOG_v0.0.1.md` | qué se encontró | — |

## Formulación

**Fuentes comprobadas (tarea T1, 2026-10-27).** Están en `../Referencias/Bibliografia/` (fuera del
repositorio). Las soluciones cerradas, con cada ecuación citada, están escritas y comprobadas en
`comprobaciones/soluciones_cerradas.py`.

| Qué | Fuente | Dónde | Lo que se encontró |
|---|---|---|---|
| Hueco elástico en medio infinito (STR-01) | Jaeger, Cook y Zimmerman (2007), *Fundamentals of Rock Mechanics*, **4.ª ed.** (la ficha cita la 3.ª, de 1976) | §8.4, ecs. (8.90)–(8.92), y §8.5, ecs. (8.104)–(8.106) (Kirsch, 1898); págs. 216–218 | Coinciden con la ficha. En el texto extraído, la (8.92) sale con «−» en σθ; el límite b → ∞ de la (8.86) y la (8.104) con σ1 = σ2 dan **+**, que es lo que exige la física (σθ(a) = 2P0). Se usan esas. El ur de la excavación es solo el término a²/r de la (8.90): el (1 − 2ν)P0 r es el desplazamiento del estado inicial |
| Anillo finito con el exterior fijo (identidad del modelo de 21 m) | Jaeger, Cook y Zimmerman (2007) | Solución general §8.4, ecs. (8.78)–(8.81), con u(b) = 0 en vez de la presión de la (8.73) | Derivación nuestra, en `lame_fixed_outer`. **Con b = 21 m, ur(a) queda un 0.60 % por debajo de Kirsch y σθ un 0.38 %** (no «un 0.2 %», como decía la spec antes de calcularlo). No hace falta Timoshenko y Goodier |
| Hueco en Mohr-Coulomb (STR-02): tensiones y radio plástico | Salençon (1969), *Annales des Ponts et Chaussées*, IV, págs. 231–236 | §3 (criterio y flujo); §5, ecs. (2″), (3″) y (9″), pág. 235 | Coinciden con la ficha pasando de tracción positiva (Salençon) a compresión positiva. H = C cotg φ = q/(Kp − 1). Salençon supone que σz es la tensión principal intermedia: el test lo comprueba en el modelo |
| STR-02: desplazamiento | Salençon (1969) | Pág. 236: r(r0, c) **solo para k = 1 (ψ = 0°) y en grandes deformaciones**; para otro k remite a su artículo de 1966 | La ficha da ur en pequeñas deformaciones para cualquier ψ. Comprobado: (a) con ψ = 0°, la fórmula publicada linealizada da lo mismo que la ficha (0.008236257 m); (b) con ψ = 0° y 30°, la solución exacta en pequeñas deformaciones del modelo de Salençon (su flujo εpθ = −k εpr, con k = 1/Kps, integrado; es la forma de pequeñas deformaciones de su (6″)) coincide con la ficha hasta 1e-12. Para ψ = 30°, el respaldo es esa derivación, no una fórmula impresa |
| STR-02 en el anillo finito (identidad del modelo de 21 m) | Salençon (1969) y Jaeger, Cook y Zimmerman (2007) | Las dos anteriores, con u(b) = 0 | Derivación nuestra, en `salencon_finite`; con b → ∞ reproduce Salençon. **Con b = 21 m, ur(a) queda un 1.42 % (ψ = 0°) y un 1.83 % (ψ = 30°) por debajo**; R0 un 0.28 % |
| Mohr-Coulomb: superficie, potencial y retorno (plano, aristas, vértice) | de Souza Neto, Perić y Owen (2008), *Computational Methods for Plasticity*, Wiley | §8.2, págs. 295–324: flujo (8.55)–(8.60); algoritmo en los Box 8.4 (predictor-corrector, pág. 305), 8.5 (plano), 8.6 (aristas) y 8.7 (vértice) | Mismo convenio que el motor: tracción positiva, σ1 ≥ σ2 ≥ σ3. Flujo no asociado con ψ. Incluye endurecimiento de la cohesión, c(ε̄p): el caso perfectamente plástico es c constante. Contraste disponible: tesis de Clausen (2007, Aalborg) |
| T6: coordenadas de área, funciones de forma, cuadratura; tensión inicial en el equilibrio | Zienkiewicz y Taylor (2000), *The Finite Element Method*, 5.ª ed., vol. 1 | Ec. (2.13b) y su comentario (pág. 25): la tensión inicial y la **excavación** en roca con tensiones previas; §8.8.1, ecs. (8.30)–(8.33), y el triángulo cuadrático (págs. 180–183); §9.10, tabla 9.2 (págs. 221–222) | El término de tensión inicial de la (2.13b) es exactamente el vector de carga de la excavación que propone este plan |

**Convenio de signos (D1, decidido):** tracción positiva. Vector de tensiones de deformación plana
(σxx, σyy, σzz, τxy), con σzz guardada en cada punto porque el Mohr-Coulomb de deformación plana la
necesita para ordenar las tensiones principales. La compresión geotécnica positiva solo aparece en la
entrada y la salida, convertida en un único sitio.

**Excavación:** la malla no tiene el hueco. Todos los elementos parten de la tensión inicial σ0
(−30 MPa hidrostática, con tracción positiva), y la excavación es el desequilibrio que esa tensión
deja en el borde libre del hueco: el vector de carga de la fase es el término de tensión inicial de
la ecuación de equilibrio (Zienkiewicz y Taylor 2000, ec. 2.13b, que pone precisamente este
ejemplo), con el contorno exterior fijo. Se aplica en escalones.

**Iteraciones:** Newton-Raphson modificado con la **rigidez elástica** (rigidez inicial), que
evita la matriz tangente no simétrica del flujo no asociado y permite factorizar una sola vez.
Tolerancia de la prueba: estricta (norma del desequilibrio frente a la norma de la carga de la
fase, del orden de 1e-8; se fija en T5). **No es la tolerancia por defecto del programa**: esa se
decide en la fase 2 con STR-05 (enmienda 3).

**Simetría:** cuarto de corona (0 a 90°) con rodillos en los dos ejes. La geometría y la carga
hidrostática son simétricas respecto a los dos ejes, así que el cuarto da la misma solución que el
círculo con un cuarto de los grados de libertad. El contorno exterior, fijo en las dos direcciones
(con carga hidrostática el desplazamiento es radial, así que fijar las dos o solo la radial da lo
mismo), a **dos distancias** (D3 bis): a **100 m** para los casos de validación contra Kirsch y
Salençon, donde su efecto es de 0.03–0.08 %, y a **21 m**, la geometría de las fichas, como
identidad contra la solución exacta del anillo finito.

## Decisiones de diseño

- **La referencia primero y validada contra algo externo.** Si la referencia tuviera un error,
  Rust lo copiaría y los tests de identidad lo darían por bueno; el oráculo solo vale si antes
  coincide con Kirsch, Lamé y Salençon.
- **Comparar en los puntos de integración y en los nudos**, no en valores suavizados: la tensión se
  compara donde se calcula, con la solución cerrada evaluada en el radio del punto. Así el error
  medido es del elemento y no de una extrapolación.
- **Dos geometrías (D3 bis).** Kirsch y Salençon son para un medio infinito; con el contorno a
  21 m, la solución exacta del propio modelo ya se aparta de ellos un 0.60 % (STR-01) y hasta un
  1.83 % (STR-02) en ur(a), así que ninguna malla cumpliría las tolerancias. Los casos de
  validación van a 100 m (efecto del 0.03–0.08 %), y el modelo de 21 m se compara con la solución
  exacta del anillo finito, que mide solo la discretización y comprueba además el contorno fijo.
- **Rigidez inicial y no tangente.** Más iteraciones, pero las mismas en las tres variantes y sin
  matriz no simétrica: la prueba mide la integración constitutiva, no la convergencia de Newton.
- **Medir como manda el `AGENTS.md` de la suite**: A/B en el mismo proceso, espalda con espalda, con
  un control repetido; si los controles difieren tanto como el efecto, la medida no decide.
- **Mismos puntos e incrementos para las tres variantes en la medida**: un conjunto fijado con
  semilla que recorre la región elástica, el plano, las aristas y el vértice, con la proporción
  documentada.

## Estrategia de pruebas

| Nivel | Test | Invariante |
|---|---|---|
| Punto material | Elástico: tensión = D·ε para incrementos aleatorios | la ley elástica es la de la fuente |
| Punto material | Mohr-Coulomb: tras el retorno, f(σ) = 0 dentro de tolerancia y la dirección del retorno es la del potencial | el retorno cae en la superficie por el camino correcto |
| Punto material | Trayectorias con solución conocida: compresión triaxial con retorno al plano, a la arista y al vértice | cada región de retorno da lo que dice la fuente |
| Elemento | Parche: un campo de desplazamiento lineal se reproduce exactamente; movimiento de sólido rígido sin tensión | el elemento pasa la prueba de la parcela |
| Elemento | Tensión inicial uniforme en un elemento libre da fuerzas internas en equilibrio | el término de tensión inicial está bien |
| Malla | Anillo de 21 m, elástico y Mohr-Coulomb, contra su solución exacta (`lame_fixed_outer`, `salencon_finite`): error que baja con el refinamiento | la discretización converge y el contorno fijo está bien |
| Caso | STR-01 y STR-02 (ψ = 0° y 30°), contorno a 100 m, contra Kirsch y Salençon dentro de tolerancia, con la malla fijada | los casos de validación |
| Caso | En STR-02, σz es la tensión principal intermedia en todos los puntos plastificados | la hipótesis de Salençon se cumple en el modelo |
| Identidad | Python de referencia = Rust (~1e-10) en punto material y en malla; NumPy igual | las variantes calculan lo mismo |
| Plataformas | Las ruedas pasan los casos en Windows, macOS ARM y Linux; el ejecutable congelado también | se puede distribuir |

## Riesgos

| Riesgo | Cómo se detecta |
|---|---|
| Una fórmula de la ficha mal transcrita (la de bulones de STR-21 ya da desplazamientos discontinuos en r = rb, duda 1 de S06) | T1 compara cada fórmula con la fuente original antes de usarla |
| El retorno al vértice o a la arista, raro en estos casos, sin probar | tests de punto material que fuerzan cada región |
| El hueco en Mohr-Coulomb converge a otra solución con malla gruesa (P02: −11 % con lineales) | estudio de convergencia antes de fijar la tolerancia |
| La ganancia de Rust depende de cómo se escribe NumPy | la variante NumPy se escribe vectorizada de verdad (sin bucles por punto en Python) y se revisa antes de medir |
| La rueda de macOS ARM no se puede probar en local | la CI la construye y la prueba; sin CI verde, el criterio 3 no se da por cumplido |
| El propietario no lee Rust con soltura (criterio 4) | se le presentan el Mohr-Coulomb en Rust y en Python lado a lado, con los mismos nombres y la misma estructura |
