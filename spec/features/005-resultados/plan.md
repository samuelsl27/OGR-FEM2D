# Plan de implementación — Spec 005, resultados (`.h5`) y su interpretación sin interfaz

> **Propuesto (2026-11-24), para aprobar** con D1–D16 de `spec.md`. Ninguna fórmula se programa
> antes de estar en la tabla «Formulación» como leída **sobre la página** (no sobre el texto
> extraído).

## Enfoque

0. **T0, antes de programar.** El OK de D1–D16. Con él, ADR-0003 y `plan_de_desarrollo.md`
   corregidos donde dicen que se parte de `results_io.py` y citan el §14.2, y `h5py` declarado en
   `pyproject.toml` (D8). Va en su propio commit.
1. **v0.0.11: las magnitudes** (D1, D2, D3, D16): el catálogo, sus definiciones con fuente y la
   conversión de salida en `model/conventions.py`. Probadas con tensores sueltos, antes que nada
   más.
2. **Las deformaciones y el motor fase a fase** (D6, D7): B u con la B del motor, y un generador
   de fases en `analysis.py` que deja `run` igual, bit a bit.
3. **El `.h5`** (D6, D7, D13): el formato documentado, la escritura a un temporal, la lectura
   perezosa, los estados y `calculate`.
4. **Los nudos y las consultas** (D5, D9, D11, D12, D14, D15): situar puntos, la recuperación por
   material, las consultas, el resumen y la tabla.
5. **Los tres casos por la consulta** (D10), con las tolerancias escritas antes de medir en su
   propio commit.

Sin Qt, en un paquete nuevo `ogr_fem2d/results/`, fuera del motor (regla 11). El motor cambia en un
solo punto, en Python (el generador de D7), con los casos 001 a 007 bit a bit como prueba. `rust/` y
la CI no se tocan, así que no hace falta rama corta. Del núcleo no se pide nada.

## Lo que se reutiliza

| De dónde | Qué | Para qué |
|---|---|---|
| `ogr_fem2d/engine/analysis.py` | `StageOutcome`, `axis_nodes` | Lo que se guarda por fase |
| `ogr_fem2d/engine/reference/solver.py` | `integration_points`, `IntegrationPoint.strain`, `SHAPES` | La B del motor para las deformaciones (D6); las funciones de forma para interpolar |
| `ogr_fem2d/engine/reference/loads.py` | `local_coordinates` | Situar un punto en un T6 curvo (D11) |
| `ogr_fem2d/engine/reference/quadrature.py` | `rule_for` | Los puntos de cada elemento, en coordenadas de área, para la recuperación |
| `ogr_fem2d/engine/initial_stress.py` | `integration_point_coordinates` | Las coordenadas de los puntos (D6) |
| `ogr_fem2d/model/translate.py` | `to_engine`, `context`, `deciding_values` | La entrada del motor; el mapa segmento → contorno de la malla (D14); lo que decide el resultado (regla 12) |
| `ogr_fem2d/model/fingerprint.py` | `model_fingerprint` | La huella del `.h5` (RF-1, RF-3) |
| `ogr_fem2d/model/conventions.py` | el único cambio de signo | Se le añade la salida (D1) |
| `ogr_fem2d/mesh/mesher.py` | `Mesh.boundaries` | Las reacciones por contorno (D14) |
| `ogr_core.units` | `get_system`, `UnitSystem.to_user`, `label_for` | La tabla en las unidades que se muestran (D15) |
| `h5py` (lo trae el núcleo; se declara, D8) | HDF5 con gzip | El `.h5` |

## Archivos que se tocan

| Archivo | Qué es | RF |
|---|---|---|
| `docs/decisiones/ADR-0003-…`, `spec/constitution/plan_de_desarrollo.md` | ya no se parte de `results_io.py`; §14.3–14.4; el factor de resistencia, a la 008 | D4, D8 |
| `pyproject.toml`, `ogr_fem2d/__init__.py` | `h5py>=3.10` en las dependencias (T0); versión 0.0.11 (T1) | D8 |
| `ogr_fem2d/model/conventions.py` | la conversión de salida: tensión ×(−1), deformación ×(−1), desplazamiento igual | RF-7, D1 |
| `ogr_fem2d/results/__init__.py` (nuevo) | el paquete | — |
| `ogr_fem2d/results/quantities.py` (nuevo) | el catálogo (D16) y el cálculo de cada magnitud desde el tensor del motor, vectorizado con NumPy | RF-5, 6, 7 |
| `ogr_fem2d/results/strains.py` (nuevo) | B u en cada punto, con la B del motor | RF-5, D6 |
| `ogr_fem2d/engine/analysis.py` | `stages(m, variant)`, un generador que entrega cada `StageOutcome` al resolverlo, y el error de la fase que falla; `run` = `list(stages(...))` | RF-2, D7 |
| `ogr_fem2d/results/store.py` (nuevo) | el `.h5`: escritura a un temporal y `os.replace`, lectura perezosa por fase y por campo, comprobación de la forma y de la versión | RF-1, 2, 4, D6, D13 |
| `ogr_fem2d/results/calculate.py` (nuevo) | `calculate(modelo, ruta, variant, should_stop)`, `open_results(ruta_modelo)` con su estado | RF-1, 2, 3, D7, D13 |
| `ogr_fem2d/results/locate.py` (nuevo) | la rejilla de elementos activos y el punto en su elemento | RF-10, D11 |
| `ogr_fem2d/results/recovery.py` (nuevo) | SPR material a material, con los bordes por los parches interiores y la salida sin parche | RF-8, 9, D5 |
| `ogr_fem2d/results/queries.py` (nuevo) | línea y polilínea, contorno con distancia, todos los nudos, todos los puntos, punto frente a fase, resumen por fase | RF-11–13, 15, D9, D12, D14 |
| `ogr_fem2d/results/table.py` (nuevo) | la tabla CSV | RF-14, D15 |
| `docs/resultados/formato.md` (nuevo) | el `.h5` campo a campo, el catálogo y los convenios | RF-1, D6 |
| `validacion/casos/005-…`, `006-…`, `007-…/esperado.json` | `comparaciones_consulta`, con su tolerancia antes de medir | D10 |
| `tests/test_results_*_v0011.py` (nuevos) | ver «Estrategia de pruebas» | todos |
| `docs/changelog/CHANGELOG_v0.0.11.md` (nuevo) | qué se encontró | — |

## El `.h5`

HDF5 leído y escrito con `h5py`. Los nombres son fijos y en inglés, como los del `.ogrfem2d`. El
detalle, en `docs/resultados/formato.md` (T4).

| Dónde | Qué lleva |
|---|---|
| `/` (atributos) | `format` = `"ogr-fem2d-results"`, `format_version` = 1, `written_by` (programa y versión), `core` (versión de `ogr-core`), `engine_variant`, `model_fingerprint`, `analysis`, `units_stored` = `"m, kN, kPa"`, `sign_convention` = `"tension positive (engine)"`, `status` (`complete`, `incomplete`, `cancelled`), y con un estado que no es `complete`, `stopped_at` (la fase) y `reason` |
| `/deciding` | `deciding_values` del modelo, como tabla de texto (qué, valor, por qué) |
| `/mesh` | `nodes` (N × 2), `elements` (E × 3 o 6), `element_region` y `element_material` (E), `points` (P × 2, las coordenadas de los puntos de integración, en el orden del motor), `point_element` (P) |
| `/stages/NNNN` (atributos) | `id`, `name`, `solved`, `steps`, `tolerance`, `cuts` |
| `/stages/NNNN` (datos) | `displacement` (N × 2); `stress` (P × 4: σxx, σyy, σzz, τxy, con NaN en los puntos de los elementos inactivos); `strain` (P × 3 en deformación plana, εxx, εyy, γxy; P × 4 en axisimetría, εr, εz, εθ, γrz; NaN igual); `plastic` (P); `active` (E); `removed_nodes`; `axis_held`; `reactions` (nudo, Rx, Ry); `history` (escalón, iteración, residuo) |

Los datos grandes van con gzip y el nivel que dé la medida del caso 005 (T5). Las fases se escriben
según salen del generador, en el temporal; al final, el estado y `os.replace`.

## Las magnitudes (D2, D3, D16)

En el convenio del usuario (D1). Con t el tensor del motor (tracción positiva), s = −t.

| id | Qué | Definición | Fuente |
|---|---|---|---|
| `sigma_xx`, `sigma_yy`, `tau_xy`, `sigma_z` | cartesianas y la de fuera del plano (en axisimetría: radial, axial, rz, circunferencial) | s | — |
| `sigma_1`, `sigma_3` | principales en el plano, σ1 ≥ σ3 | ½(sxx + syy) ± [τxy² + ¼(sxx − syy)²]^½ | JCZ ecs. (2.37)–(2.38) |
| `theta_1` | ángulo de σ1 desde +x, antihorario, en (−90°, 90°] | tan 2θ = 2τxy / (sxx − syy), con la rama de las ecs. (2.41)–(2.44) | JCZ ecs. (2.33), (2.41)–(2.44) |
| `sigma_I`, `sigma_II`, `sigma_III` | las tres principales ordenadas | {σ1, σ3, σz} ordenadas: z es principal porque τxz = τyz = 0 | JCZ §2.5 |
| `p` | tensión media | (sxx + syy + sz) / 3 | JCZ ec. (2.153) |
| `q` | tensión de von Mises | √(3 J2), J2 = ⅙[(sxx − syy)² + (syy − sz)² + (sz − sxx)²] + τxy² | dSN ec. (6.111); JCZ ec. (2.163) |
| `sigma_diff` | diferencial | σI − σIII | JCZ cap. 6, pág. 151 |
| `u_x`, `u_y`, `u` | desplazamientos y su módulo | u, v; √(u² + v²) | — |
| `eps_xx`, `eps_yy`, `gamma_xy`, `eps_z` | deformaciones (acortamiento positivo; γ ingenieril) | e = −(B u); en deformación plana, εz = 0 | JCZ ecs. (2.181)–(2.186), pág. 46; Z&T cap. 2 |
| `eps_v` | volumétrica | εxx + εyy + εz | JCZ ec. (2.231) |
| `gamma_max` | corte máxima ingenieril en el plano | ε1 − ε3 = 2[εxy² + ¼(εxx − εyy)²]^½, con εxy = γxy/2 | JCZ ec. (2.195), pág. 46 |

## Decisiones de diseño

- **El `.h5` es el número del motor; la interpretación se calcula al leer (D1, D6).** Lo que
  depende de un método (los nudos recuperados) o de un convenio (el signo) no se guarda. Así la ida
  y vuelta es bit a bit, y cambiar el método no deja viejos los archivos.
- **La recuperación (D5).**
  - Los parches se forman, fase a fase, con los elementos activos de un mismo material. El parche
    de un nudo de esquina reúne los elementos de ese material que lo tienen.
  - Ajuste por mínimos cuadrados (Z&T ecs. 14.28–14.31): polinomio de grado p en coordenadas locales
    del parche (centradas en el nudo y escaladas por su tamaño, para que A esté bien condicionada),
    con P = [1, x, y] en T3 y [1, x, y, x², xy, y²] en T6.
  - Un nudo «interior del material» es el que no está en un lado con un solo elemento del material
    activo. Sus parches son los que se ajustan.
  - Un nudo del borde del material toma la media de los polinomios de los parches interiores cuyos
    elementos lo contienen (fig. 14.9). Si no hay ninguno, el campo extrapolado de cada elemento suyo
    del material, y la procedencia lo dice.
  - Un parche con menos puntos que coeficientes, o con A mal condicionada (número de condición por
    encima de 10¹⁰), no cuenta.
  - El resultado se guarda por (elemento, nudo local): continuo dentro de un material, con un valor
    por material en los nudos de contacto. Así lo dibuja la 006 elemento a elemento, sin mezclar.
- **Situar puntos (D11).** Rejilla uniforme de lado del orden del elemento medio, con la caja de cada
  elemento activo ampliada un 1 % de su diagonal, para los lados curvos. En cada candidato,
  `local_coordinates`, que admite el punto si sus coordenadas de área son ≥ −10⁻⁹. Los candidatos
  van en orden de índice, y así un empate es determinista.
- **La línea (RF-11).** N puntos a la misma distancia a lo largo de toda la polilínea, o los
  vértices; la distancia, la acumulada desde el primero. Un punto sobre un contacto entre materiales
  da una fila por material (D9). Un punto fuera da su fila sin valor y con la razón (`excavated`,
  `outside`).
- **El contorno (D12).** Se toman los vértices, o N puntos por segmento (sobre el arco si lo es). La
  normal de un segmento recto es la de su dirección girada; la de un arco, la radial. Hacia dentro o
  fuera según el sentido del anillo de su región (`regions`, orden canónico de la 004). En un vértice,
  la bisectriz de las normales de los dos segmentos. Un punto movido fuera del modelo queda sin valor,
  como en la línea.
- **El motor fase a fase (D7).** `stages()` es el cuerpo actual de `run` con `yield` en lugar de
  `append`. Si una fase lanza, la excepción sale del generador después de haber entregado las
  anteriores. `calculate` las escribe según llegan y, al cortarse, pone el estado y la razón.
  `should_stop()`, consultado entre fases, da `cancelled`.
- **Estados al abrir (RF-3).** `open_results(ruta_modelo)` lee el modelo y el `.h5` hermano y da uno
  de estos estados: `valid`, `stale` (otra huella), `incomplete`, `cancelled`, `missing` (no hay
  `.h5`) o `damaged` (con el error). Con un estado distinto de `valid`, los datos solo se leen
  pidiéndolo explícitamente, y cada valor que se lea así lleva el estado. Un `.h5` sin modelo se lee
  con `store.read`, que lo dice.

## Formulación

| Qué | Fuente | Dónde | Estado |
|---|---|---|---|
| Tensiones en un plano y principales en 2-D | Jaeger, Cook y Zimmerman (2007), 4.ª ed. | §2.3, ecs. (2.31)–(2.44), págs. 20–21 (PDF 33–34) | **Leído** en el texto; se comprueba sobre la página en la T1 |
| Invariantes, media, desviador, J2 | JCZ (2007) | §2.8, ecs. (2.137)–(2.167), págs. 38–41 (PDF 51–54) | **Leído**; **(2.149)** sale con «(σ3 − σ3)» y **(2.162)** con τ²xx donde se espera s²xx: errata de la extracción o del libro, se mira la página en la T1 |
| Deformaciones en 2-D, γ = 2ε | JCZ (2007) | §2.10, ecs. (2.181)–(2.186), págs. 44–46 (PDF 57–59) | **Leído** |
| Principales de deformación | JCZ (2007) | ec. (2.195), pág. 47 (PDF 60) | **Leído**; la raíz del corchete no sale en la extracción: se mira la página en la T1 |
| Deformación volumétrica | JCZ (2007) | §2.13, ec. (2.231), pág. 53 (PDF 66) | **Leído** |
| Convenio de signos de JCZ (compresión y acortamiento positivos; su x* = x − u, que aquí **no** se sigue) | JCZ (2007) | §2.2; ecs. (2.168)–(2.170), págs. 42–43 | **Leído** |
| Tensión diferencial | JCZ (2007) | cap. 6, pág. 151 (PDF 164): «σ1 − σ3 is referred to as the differential stress» | **Leído** |
| Tensión de von Mises | de Souza Neto, Perić y Owen (2008) | ec. (6.111), pág. 163 (PDF 188) | **Leído** |
| Mohr-Coulomb en invariantes (para la 008, D4) | dSN (2008), según Owen y Hinton (1980) | ec. (6.119), pág. 166 (PDF 191); ángulo de Lode, ec. (6.97) | **Leído**; no se programa aquí |
| Deformación B u, la B del motor | Zienkiewicz y Taylor (2000), 5.ª ed., vol. 1 | ecs. (2.2)–(2.4); en axisimetría, (5.5)–(5.6) | **Leído** (spec 002) |
| Recuperación: el promedio, inadecuado | Z&T (2000) | §14.3, págs. 375–377 (PDF 391–393) | **Leído** |
| SPR: el polinomio, el ajuste, la media de parches, los bordes y contactos | Z&T (2000) | §14.4.1, ecs. (14.28)–(14.31), figs. 14.8–14.9, págs. 377–379 (PDF 393–395) | **Leído**; las figs. 14.8 y 14.9 se miran sobre la página en la T8 |
| Puntos de muestreo óptimos de los triángulos | Z&T (2000), según Moan (1974) | §14.2, fig. 14.6, pág. 375 (PDF 391) | **Por mirar sobre la página** (T8): qué puntos da para T6, y si son los tres medios de los lados de la spec 002 |
| Interpolación de los valores recuperados | Z&T (2000) | ec. (14.27), pág. 376 (PDF 392) | **Leído** |
| Kirsch, para la línea del 005 | JCZ (2007) | §8.4, ecs. (8.90)–(8.92), págs. 216–218 | **Leído** (spec 001; errata de signo de la (8.92) en la extracción, en la memoria) |
| Michell, para la línea del 006 | Timoshenko y Goodier (1951) | §34, ec. (f), págs. 92–95 | **Leído** (caso 004) |
| Lamé con u(b) = 0, para la línea del 007 | Timoshenko y Goodier (1951) | §121, ecs. (197)–(198), págs. 358–359 | **Leído** (spec 002, `comprobaciones/soluciones_cerradas.py`, `sphere_fixed_outer`) |

**Convenio:** el `.h5`, en el del motor (tracción positiva); lo que entrega esta capa, en el del
usuario (D1). La conversión va en `model/conventions.py` y en ningún otro sitio.

## Anomalías que se vigilan (regla 6)

- Que los puntos óptimos del T6 en la fig. 14.6 no sean los tres medios de los lados. La
  recuperación funciona igual como ajuste, pero cambia lo que se espera de ella. Se reporta, sin
  tocar la regla de integración.
- Que la regla de 7 puntos de la axisimetría, que no es de puntos óptimos, recupere peor. Se ve en la
  línea del 007; si no cumple, es un hallazgo.
- Que el generador de fases cambie un número de los casos 001 a 007. No debería: es el mismo código
  con `yield`.
- Que una de las erratas de JCZ sea del libro, no de la extracción. Se anota y se programa la
  correcta, comprobada con la identidad.

## Estrategia de pruebas

| Nivel | Test | Invariante |
|---|---|---|
| Magnitudes | Tensores al azar girados por ángulos al azar: principales, p, J2, q y diferencial iguales; θ1 gira con los ejes; hidrostático: q = diferencial = 0; σ1 + σ3 = sxx + syy; JCZ ec. (2.146); orden σI ≥ σII ≥ σIII también con σz intermedia, mayor o menor | D2 |
| Convenio | Compresión uniaxial del motor (tracción negativa) → σ1 > 0; acortamiento → ε > 0; desplazamiento sin cambio; el `.h5` con el signo del motor; un solo sitio (búsqueda de otro ×(−1) en `results/`) | D1, RF-7 |
| Axisimetría | Las mismas ids con su nombre radial, axial y circunferencial; σz = σθ | RF-6 |
| Deformaciones | Prueba de la parcela: desplazamiento lineal impuesto → deformación exacta en todos los puntos, T3 y T6, plana y axisimétrica; γmax con el factor 2 | D3, D6 |
| Motor | `run` y `list(stages())`, iguales bit a bit en los casos 001 a 007; una fase que falla entrega antes las anteriores | D7 |
| `.h5` | Ida y vuelta bit a bit (NaN en su sitio); una fase sola sin leer el resto; dañado, sin un campo, formato posterior: error que lo nombra; un fallo a mitad de la escritura deja el `.h5` anterior | RF-1, 2, 4 |
| Estados | Válido; mutar el modelo → `stale`; sin `.h5` → `missing`; fase que falla → `incomplete` con las anteriores; `should_stop` → `cancelled`; `.h5` de otra versión del programa → válido, dicho | RF-3, D7 |
| Situar | Punto en el interior, sobre un lado común, sobre un contacto, entre la cuerda y el arco de un T6 curvo, en una excavación, fuera | D11 |
| Recuperación | Campo gravitatorio (lineal) con T6, sin excavar: exacto en todos los nudos, bordes incluidos; constante con T3; dos materiales de distinto peso: exacto a cada lado; con los materiales mezclados (mutación), no; un material de un elemento de espesor: salida extrapolada, dicha; un elemento inactivo no entra | D5, RF-8, 9 |
| Consultas | N puntos y vértices; distancia acumulada; un contacto da dos filas; fuera y excavado sin valor; desplazamiento interpolado igual al nodal en los nudos; contorno con arcos sobre el arco; distancia dentro y fuera de un círculo = círculo concéntrico; distancia 0 por defecto | D9, D12 |
| Resumen | Extremos con dónde y de qué tipo; reacciones por contorno que suman la total, y la total equilibra cargas y peso | D14 |
| Tabla | Cabecera completa; MPa = kPa / 1000; columnas fijas; ida y vuelta de los números (repr) | D15 |
| Casos | 005, 006 y 007 por la consulta, con la tolerancia de D10 escrita antes de medir | D10 |
| Regla 7 | N, modo (vértices o repartidos), lado y distancia, fase, magnitud, sistema de unidades: cada uno mueve el número | regla 7 |

Cada test lleva su cabecera (qué invariante protege) y tiene dientes: una mutación sistemática por
invariante (`{etiqueta: (archivo, texto, sustituto)}`), anotada en `tasks.md`.

## Riesgos

| Riesgo | Cómo se detecta o se acota |
|---|---|
| El tiempo de la recuperación y de B u en el caso 005 (84 198 puntos, unos 56 000 nudos) en Python puro | Se mide en la T5 y la T8; las magnitudes, B u y el ajuste van vectorizados con NumPy (es posproceso, no un elemento ni una ley: no necesita oráculo aparte). La meta se anota antes de medir: menos de 30 s por fase |
| El margen del caso 006 en la línea: 0.0047 q sobre el efecto del dominio | El test lo dice; si no cumple, hallazgo (regla 6). No se afloja la tolerancia ni se cambia la malla |
| Parches mal condicionados junto a arcos y en la ventana graduada | El número de condición de cada parche se mira; los que no cuentan, se cuentan y se dicen en las notas de la recuperación |
| `os.replace` sobre un `.h5` abierto por otro programa en Windows | Error que lo dice, y el temporal se borra; el test cierra siempre |
| `h5py` en la CI (Python 3.11, Linux, macOS) y en el congelado de PyInstaller | Llega con el núcleo, así que ya está en la CI. El congelado no lo usa hasta que un caso lo pida; si lo pide, se mira allí |
| Que la copia de la malla en el `.h5` pese más de lo que vale | Se mide en el 005 (T5) y se anota; si pesa, es propuesta para la propietaria, no decisión sola |
