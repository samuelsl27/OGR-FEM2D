# Plan de implementación — Spec 002, motor elástico general

> Aprobado (2026-10-27), con D1–D7 de `spec.md`. **Ninguna fórmula se programa antes de
> comprobarla contra su fuente (tarea T1, hecha).**

## Enfoque

1. **Entrada y validación** (RF-1, RF-2): un esquema discreto con sus reglas, y los errores que dicen
   dónde está el fallo. Es lo que leerá la spec 004.
2. **Elementos** (RF-3, RF-4): el T6 de la spec 001 se generaliza sin cambiar su resultado; se
   añaden el T3 y la axisimetría en la referencia, cada uno con su parcela y su sólido rígido.
3. **Contorno, cargas, tensión inicial y fases** (RF-5 a RF-9), con las identidades exactas
   (equilibrio de reacciones, campo gravitatorio en equilibrio, excavación por desactivación).
4. **Casos** STR-09 y STR-04 con sus estudios, y los casos 001 y 002 por el motor general.
5. **Rust** (RF-10, RF-11) y su identidad; después CI y congelado.

La frontera Python ↔ Rust no cambia: **una llamada por iteración global**. En elástico hay una sola
iteración por escalón; el bucle es el mismo que con Mohr-Coulomb.

## Archivos que se tocan

| Archivo | Qué es | RF |
|---|---|---|
| `ogr_fem2d/engine/model.py` (nuevo) | la entrada discreta: `EngineModel`, `Stage`, `Load`…, y `validate()` con sus errores | RF-1, RF-2 |
| `docs/motor/entrada.md` (nuevo) | el esquema documentado: cada campo, unidades coherentes, convenio de signos, reglas de validación | RF-1 |
| `ogr_fem2d/engine/reference/element_t3.py` (nuevo) | triángulo de 3 nudos | RF-3 |
| `ogr_fem2d/engine/reference/element_t6.py` | gana la axisimetría y la regla de 7 puntos; en deformación plana, idéntico | RF-3, RF-4 |
| `ogr_fem2d/engine/reference/quadrature.py` (nuevo) | las reglas de la tabla 9.2 que se usan (lineal, cuadrática, quíntica), en un solo sitio | RF-3 |
| `ogr_fem2d/engine/reference/elastic.py` | matriz D de axisimetría (Z&T ec. 5.12) | RF-3 |
| `ogr_fem2d/engine/reference/loads.py` (nuevo) | fuerzas nodales consistentes: nodales, puntuales, repartidas, peso propio | RF-6 |
| `ogr_fem2d/engine/initial_stress.py` (nuevo) | preproceso: campo constante y gravitatorio (fuera del motor, D3) | RF-7 |
| `ogr_fem2d/engine/reference/solver.py` | fases, elementos activos, restricciones y desplazamientos impuestos, reacciones | RF-5, RF-8, RF-9 |
| `ogr_fem2d/engine/analysis.py` (nuevo, T6) | resuelve un `EngineModel` fase a fase: totales a incrementos, eje (D1 bis), restricciones insuficientes, reacciones por nudo | RF-5, RF-9 |
| `ogr_fem2d/engine/interface.py`, `compiled.py` | la interfaz admite T3/T6 y los dos tipos de análisis | RF-10 |
| `ogr_fem2d/engine/mesh_structured.py` (nuevo) | rectángulo graduado de T3 o T6 para los tests y STR-04 (no es el generador de la spec 003) | — |
| `ogr_fem2d/engine/mesh_radial.py` | opción T3 (cada T6 partido en cuatro T3 sobre los mismos nudos) | — |
| `rust/src/{t3.rs, t6.rs, elastic.rs, lib.rs}` | gemelos de la referencia | RF-10 |
| `validacion/casos/003-cavidad-esferica-elastica/`, `004-carga-en-faja-elastica/` | `caso.md`, `esperado.json` | — |
| `tests/test_*_v002.py` | ver «Estrategia de pruebas» | todos |
| `docs/changelog/CHANGELOG_v0.0.2.md` | qué se encontró | — |

## Formulación

Fuentes en `../Referencias/Bibliografia/`. Las soluciones cerradas, en
`comprobaciones/soluciones_cerradas.py` (comprobado: Michell = Flamant superpuesto a 2·10⁻¹⁶ MPa;
la esfera finita tiende a la infinita como 1/b³).

| Qué | Fuente | Dónde | Estado |
|---|---|---|---|
| Carga en faja (STR-04) | Timoshenko y Goodier (1951), 2.ª ed. | §34, ecs. (c)–(f), págs. 92–95 (J. H. Michell 1902): principales −2A(α ± sen α), 2Aπ = q, dirección bisectriz | **Leído y comprobado.** La ficha cita Poulos y Davis (1974), que no está en la bibliografía; da la misma solución |
| Fuerza puntual en el semiespacio | Timoshenko y Goodier (1951) | §33, ec. (66), pág. 85 (Flamant 1892) | **Leído**; usado solo para comprobar Michell; las componentes de la (67), pág. 87, son las de `strip_by_flamant`. El desplazamiento, §33, ecs. (g), (h), (71) y (72), págs. 89–91: lleva log r y una constante B = (2P/πE)·log d que fija el punto que se toma como inmóvil. **En STR-04 no hay desplazamiento de referencia**: solo se comparan tensiones, como hace la ficha |
| Cavidad esférica (STR-09) | Timoshenko y Goodier (1951) | §121, ecs. (197)–(198), págs. 358–359 (Lamé); ur por la ley de Hooke (§6) | **Leído y comprobado**; coincide con la ficha. La esfera con u(b) = 0, derivación propia |
| Axisimetría: desplazamientos, deformaciones (εθ = u/r), B, D isótropa, rigidez sobre el anillo (2π) | Zienkiewicz y Taylor (2000), 5.ª ed., vol. 1 | §5.2, ecs. (5.5), (5.6), (5.12), (5.13), págs. 112–117; §5.2.2: u ∝ r con v lineal es el único campo de deformación constante | **Leído.** Orden de componentes de la fuente distinto del nuestro (se documenta la correspondencia); 2π en la (5.13) (D2) |
| T3 | Zienkiewicz y Taylor (2000) | §4.2.1–4.2.2, ecs. (4.5a)–(4.5c), (4.8) y (4.10b), págs. 88–90; §2.2, ecs. (2.1)–(2.5), págs. 20–22 | **Leído**: Nᵢ = (aᵢ + bᵢx + cᵢy)/2Δ con aᵢ = xⱼyₘ − xₘyⱼ, bᵢ = yⱼ − yₘ, cᵢ = xₘ − xⱼ, nudos en sentido antihorario; B constante. Es el mismo triángulo que el T6 con funciones de forma lineales en coordenadas de área, y así se programa (una sola geometría isoparamétrica); la (4.10b) es la comprobación |
| Cuadratura en triángulos | Zienkiewicz y Taylor (2000) | §9.10, tabla 9.2, pág. 222 | **Leída**: lineal (centroide), cuadrática (lados, 1/3), cúbica (4 puntos, −27/48), quíntica (7 puntos: centroide 0.225; α₁ = 0.0597158717, β₁ = 0.4701420641, peso 0.1323941527; α₂ = 0.7974269853, β₂ = 0.1012865073, peso 0.1259391805). **La tabla trunca a diez decimales** (no redondea): la quíntica se programa en forma cerrada (α = (9 ∓ 2√15)/21, β = (6 ± √15)/21, w = (155 ± √15)/1200), que no está impresa: se comprueba contra cada dígito de la tabla y contra la integral exacta de los monomios, ec. (8.38), pág. 183 |
| Cargas consistentes, peso propio, tensión inicial | Zienkiewicz y Taylor (2000) | cap. 2, ec. (2.13) y su comentario (pág. 25) | **Leído.** §2.2.4, ecs. (2.10)–(2.13b), págs. 23–25: fᵉ = −∫Nᵀb dV − ∫BᵀDε₀ dV + ∫Bᵀσ₀ dV (el signo, porque Z&T escriben q = K a + f: f es lo que se resta a las cargas); ec. (2.14), fuerzas concentradas en los nudos; ec. (2.15), pág. 25: tracciones, −∫Nᵀt dA sobre el lado. Axisimetría, §5.2.6–5.2.8, ecs. (5.15)–(5.19), págs. 118–119: los mismos términos con 2π r, y la fuerza nodal es la de **toda la circunferencia** (2π r R): confirma D2. **Carga puntual dentro de un elemento: no está impresa.** Se deriva del mismo trabajo virtual de la (2.10): una fuerza P en x_p hace el trabajo uᵀ(x_p)P = aᵀNᵀ(x_p)P, luego fᵢ = Nᵢ(x_p)P (derivación propia, con test: resultante y momento). En axisimetría P es la fuerza total del anillo de radio r_p, coherente con D2 |
| Tensión gravitatoria | Jaeger, Cook y Zimmerman (2007), 4.ª ed. | §13.2, ec. (13.1) (σv = ∫ρg dz), ec. (13.5) (σh = k σv), págs. 400–401 | **Leído.** La (13.5) da un solo k para las dos horizontales; separar K y Kz (D3) es lo que pide S01 (tensiones fuera del plano) y es un caso de la (13.5) con dos coeficientes. Las correlaciones de K0 en suelos (Jâky…, T06) quedan para el material, no para el motor |
| Equilibrio en axisimetría | Timoshenko y Goodier (1951) | §116, ec. (177), pág. 343 | **Leído.** El equilibrio radial lleva (σr − σθ)/r: un campo uniforme en r solo está en equilibrio con σr = σθ, y τrz se anula en el eje. **Anomalía en D3**: con K ≠ Kz el campo gravitatorio no está en equilibrio en axisimetría. Resuelta con la enmienda de D3: en axisimetría, K = Kz; en el campo constante, σr = σθ y τrz = 0 |

**Convenio:** el vector de tensiones sigue siendo (σxx, σyy, σzz, τxy) con tracción positiva; en
axisimetría x es r, y es z (el eje), y σzz es la circunferencial σθθ. Así el Mohr-Coulomb, el
almacenamiento y la interfaz con Rust no cambian de forma, y lo que cambia de significado se
documenta en `docs/motor/entrada.md`.

**Excavación general (RF-8):** en cada fase, la carga desequilibrada es
f_ext(fase) − Σ_activos ∫Bᵀσ dΩ, con σ las tensiones al final de la fase anterior. Con todos los
elementos activos y la tensión inicial en equilibrio es cero; al quitar elementos, es exactamente
el término de la (2.13b) de la spec 001. Los grados de libertad de nudos sin elementos activos se
quitan del sistema.

**Desplazamientos impuestos (D2 de la 001):** en totales; el motor impone en la fase el incremento
(valor de la fase menos el desplazamiento al final de la anterior) por partición del sistema.

## Decisiones de diseño

- **El T6 en deformación plana no cambia de números.** Generalizar es reorganizar: los casos 001 y
  002 deben dar lo mismo a redondeo. Si cambian, se para y se explica (regla 6).
- **Un tipo de elemento por modelo.** Mezclar T3 y T6 exige nudos intermedios colgantes en las
  fronteras; nadie lo ha pedido.
- **La tensión inicial es un tensor por punto.** El motor no sabe de estratos ni de K; el preproceso
  sí, y está fuera (regla 11). Cuando la spec 004 traiga la geometría, la superficie irregular se
  añade al preproceso, no al motor.
- **Identidades exactas antes que casos.** Cada pieza nueva (axisimetría, cargas, gravedad,
  desactivación) tiene una identidad que se cumple a redondeo y que caza un error introducido a
  propósito; los casos de las fichas vienen después.
- **STR-04 con dos geometrías, como STR-01 en la spec 001**: el dominio de la ficha (o el que fije
  el estudio) contra Michell, y una identidad con las tracciones exactas de Michell en el contorno
  del dominio truncado, que mide solo la discretización. Las tracciones se integran en el test con
  una regla de orden alto y entran al motor como cargas nodales (no hace falta una carga «arbitraria»
  en el motor).
- **Mallas estructuradas solo para tests y casos**; el generador general es la spec 003.

## Estrategia de pruebas

| Nivel | Test | Invariante |
|---|---|---|
| Entrada | Cada regla de `validate()` con una entrada que la incumple | el error nombra el sitio y la regla |
| Cuadratura | Cada regla integra exactamente los monomios hasta su grado y no el siguiente | la tabla 9.2 está bien copiada |
| Elemento | Parcela y sólido rígido de T3 y T6, en deformación plana y en axisimetría; en axisimetría, u_r constante **sí** da tensión (εθ = u/r) | los elementos y la axisimetría |
| Elemento | Ningún punto de integración sobre el eje (D1); el eje con u_r impuesto (D1 bis) | el caso límite del eje |
| Cargas | Cargas repartidas uniformes y lineales: suma de fuerzas nodales = resultante, y momento = momento de la carga; peso propio: suma = γ·área (o γ·volumen del anillo) | fuerzas consistentes |
| Global | Σ reacciones + Σ cargas = 0 en x y en y, en cada fase | equilibrio global |
| Gravedad | Superficie y estratos horizontales, rodillos laterales: desplazamiento nulo a redondeo en deformación plana (T3, T6) y en axisimetría con T6; con T3 axisimétrico, desplazamiento que baja como h² (el centroide no integra exactos los términos de grado 2: T1; se espera, se comprobará) | el campo gravitatorio está en equilibrio con el peso propio |
| Fases | Fase sin cambios: incremento nulo; desactivar el anillo interior = malla sin anillo, a redondeo | la excavación general |
| Regresión | Casos 001 y 002 por el motor general: mismos números | no se rompe lo validado |
| Caso | STR-09 y STR-04 con su tolerancia (D4), estudio de convergencia (y de dominio en STR-04) | los casos de las fichas |
| Identidad | Esfera finita con u(b) = 0; semiespacio truncado con las tracciones de Michell | discretización sola |
| Variantes | Referencia = Rust a ~1e-10 en todo lo anterior | Rust calcula lo mismo |

Cada test con su cabecera (qué invariante protege) y con dientes: se comprueba que caza un error
introducido a propósito, y se anota en `tasks.md`.

## Riesgos

| Riesgo | Cómo se detecta |
|---|---|
| Generalizar el T6 cambia sus números sin que se note | el test de regresión de los casos 001 y 002 |
| La quíntica mal copiada (diez decimales a mano) | el test de exactitud de monomios, y la suma de pesos |
| El dominio de 50 × 25 m no basta para STR-04 con 0.01·q | el estudio de dominio; si no basta, hallazgo reportado (D4) |
| El T3 converge despacio en tensiones (deformación constante): STR-09 con T3 necesitaría una malla muy fina | el estudio de convergencia decide; la ficha usa T3, pero el caso puede fijarse con T6 (regla 9) y el T3 con su propia malla. Se pregunta al propietario con los números |
| Un nudo de un elemento excavado se queda con rigidez nula | `validate()` y el test de excavación |
