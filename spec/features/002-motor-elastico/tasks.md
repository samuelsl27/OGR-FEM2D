# Tareas — Spec 002, motor elástico general

Pequeñas y verificables, ordenadas por dependencia. Al terminar cada una: este archivo y el
changelog al día, la suite entera en verde, commit y push.

## Antes de programar

- [x] T0. El propietario responde D1–D7 de `spec.md` y aprueba el plan — Hecho cuando: las
      respuestas están anotadas en `spec.md`. (Hecho el 2026-10-27: las siete, como se propusieron.)
- [x] T1. Fuentes que faltan: el T3 (Z&T cap. 4), los términos de fuerzas de volumen, de superficie
      y la carga puntual de la (2.13) de Z&T, y el desplazamiento de Flamant en T&G §33 — Hecho
      cuando: la tabla «Formulación» de `plan.md` no tiene ningún «por comprobar». (Hecho ya: Michell,
      Flamant, Lamé esférico, axisimetría §5.2, tabla 9.2, JCZ §13.2; soluciones cerradas en
      `comprobaciones/`.) (Hecho el 2026-10-27: T3, Z&T §4.2, ecs. (4.5)–(4.10); cargas, Z&T
      ecs. (2.10)–(2.15) y §5.2.6–5.2.8; desplazamiento de Flamant, T&G §33, ecs. (g)–(72).
      Hallazgos: la carga puntual dentro de un elemento no está impresa y se deriva del trabajo
      virtual de la (2.10); la (5.13) y el §5.2.6 confirman D2; en STR-04 no hay desplazamiento de
      referencia; y en axisimetría con T3 la regla del centroide no integra exactos ni Bᵀσ₀·r ni
      Nᵀb·r (grado 2), así que la identidad gravitatoria solo es exacta con T6 o en deformación
      plana: con T3 axisimétrico se espera un desplazamiento que baje con h², no nulo (se
      comprobará en la T8). **Anomalía en D3, pendiente del propietario**: en axisimetría el
      equilibrio radial lleva (σr − σθ)/r (T&G §116, ec. 177), y un campo gravitatorio con
      K ≠ Kz, o uno constante con σr ≠ σθ o τrz ≠ 0, no está en equilibrio. Resuelta con la
      enmienda de D3: en axisimetría se exige K = Kz, y σr = σθ con τrz = 0.)

## Entrada y elementos (referencia)

- [x] T2. `model.py` y `docs/motor/entrada.md`: esquema y `validate()` — RF-1, RF-2 — Hecho cuando:
      cada regla tiene su test con una entrada que la incumple. (Hecho el 2026-10-27:
      `ogr_fem2d/engine/model.py` con 27 reglas, cada problema con su regla y su sitio, y todos a la
      vez en un `InputError`; el esquema, campo a campo y regla a regla con su porqué, en
      `docs/motor/entrada.md`. 9 tests en `test_engine_input_v002.py`; la tabla de casos cubre
      exactamente las reglas. Dientes: desactivar cada una de las 27 reglas y otras siete
      mutaciones (signo del umbral de área, eje fuera de la axisimetría, restricción en nudo
      excavado, Mohr-Coulomb en todas partes, 3 puntos en vez de 7, x < 0 en deformación plana,
      ψ > φ) hace fallar un test; tres sobrevivían al principio y llevaron a un test más. Decisiones
      de diseño: una restricción en un nudo sin elementos activos se acepta (no sujeta nada) y una
      carga o un desplazamiento impuesto allí no (se perderían); la carga puntual fuera de su
      elemento la detecta la T7, que invierte la transformación del elemento.)
- [x] T3. `quadrature.py` con las reglas lineal, cuadrática y quíntica — Hecho cuando: cada una
      integra exactos los monomios hasta su grado y falla en el siguiente. (Hecho el 2026-10-27:
      `ogr_fem2d/engine/reference/quadrature.py`, con `rule_for` según D1; el T6 y `model.py` toman
      de ahí la regla y el número de puntos, sin cambiar los de la spec 001. Referencia externa: la
      integral exacta de los monomios en coordenadas de área, Z&T ec. (8.38), pág. 183. 7 tests;
      diez mutaciones (pesos, coordenadas, permutaciones, orden de la regla cuadrática, grado, regla
      de D1) cazadas. Hallazgo: la tabla 9.2 **trunca** a diez decimales, no redondea; la quíntica se
      escribe en forma cerrada, que no está impresa en la fuente: se comprueba contra cada dígito
      impreso y contra los monomios hasta grado 5 a 1e-15.)
- [x] T4. T6 generalizado y T3 en deformación plana — RF-3 — Hecho cuando: parcela, sólido rígido y
      tensión inicial uniforme pasan con los dos, y los casos 001 y 002 dan los mismos números.
      (Hecho el 2026-10-27: `reference/triangle.py`, el triángulo isoparamétrico de n nudos con la
      regla como parámetro; `element_t3.py` (Z&T §4.2, ecs. 4.5–4.10) y `element_t6.py` dan sus
      funciones de forma y delegan en él. El solver, la interfaz (`Geometry` de k nudos y bloques de
      2k × 2k) y el patrón de la rigidez valen para k = 3 y 6, un tipo por modelo; la variante Rust
      dice que solo tiene el T6 hasta la T13. **Los casos 001 y 002 dan exactamente los mismos
      números, bit a bit**, en la referencia y en Rust, comprobado contra lo calculado con el
      código anterior (y el caso 001 recalculado aparte con el código de `HEAD`). 11 tests en
      `test_t3_element_v002.py`: B contra la (4.10b), parcela con el ensamblaje del propio solver,
      bloque traccionado a través de `solve_stage` con T3 y T6 contra la tensión uniforme exacta.
      Diez mutaciones cazadas; una sobrevivía (la rigidez por punto con el ancho del T6, que solo se
      ensambla con plasticidad) y llevó al test de las dos rutas a la misma matriz.)
- [x] T5. Axisimetría de T3 y T6 — RF-3, RF-4 — Hecho cuando: parcela axisimétrica (u = a·r,
      v = b·z), sólido rígido (solo traslación en z), u_r constante con tensión, ningún punto sobre
      el eje. (Hecho el 2026-10-27: Z&T §5.2, ecs. (5.5), (5.6), (5.12)–(5.14). La matriz B gana la
      fila εθ = u/r, el peso de cada punto lleva 2πr (anillo entero, D2) y la D es la de 4 × 4;
      en el solver, el modelo dice su análisis y cada punto guarda Nᵢ/r; la tensión circunferencial
      trabaja en las fuerzas internas. Rust la rechaza hasta la T13; Mohr-Coulomb en axisimetría,
      rechazado (D6). 14 tests en `test_axisymmetry_v002.py`: D contra la (5.12), B del T3 contra la
      (5.6), rigidez del centroide contra la (5.14), volumen de Pappus, parcela A y B con T3 y T6 en
      parcelas que tocan el eje, cilindro traccionado a través de `solve_stage` contra la solución
      exacta, ningún punto sobre el eje y la rigidez punto a punto igual a la del elemento; trece
      mutaciones cazadas, una tras añadir ese último test. **Hallazgo**: el T3 con el centroide, que es la (5.14)
      de la fuente, tiene en el elemento aislado un segundo modo de energía nula, espurio (B es
      4 × 6 en un solo punto); la malla ensamblada no tiene ningún mecanismo, comprobado con
      bloques que tocan el eje y que no lo tocan. Los casos 001 y 002 siguen dando los mismos
      números bit a bit. La imposición automática de u_r = 0 en el eje (D1 bis) va con las
      restricciones, en la T6.)

## Contorno, cargas, tensión inicial y fases (referencia)

- [x] T6. Restricciones, desplazamientos impuestos en totales y reacciones — RF-5 — Hecho cuando:
      equilibrio global de reacciones en cada fase. (Hecho el 2026-10-27: `ogr_fem2d/engine/analysis.py`
      resuelve un `EngineModel` fase a fase; `solve_stage` gana los desplazamientos impuestos
      (incremento de la fase, repartido entre escalones como la carga) y las reacciones
      R = f_int − f_ext en cada grado de libertad restringido o impuesto. El driver convierte los
      totales en incrementos, impone u_r = 0 en los nudos del eje y lo dice (D1 bis), comprueba
      antes de resolver que las restricciones paran los movimientos de sólido rígido y nombra el
      que queda libre (traslación, giro alrededor de un punto, traslación axial), y no resuelve una
      fase que no cambia nada. Rechaza lo que aún no está: peso propio y cargas repartidas y
      puntuales (T7), elementos inactivos (T9). 8 tests en `test_analysis_v002.py`: equilibrio de
      fuerzas y momentos en cada fase con T3 y T6, y axial en axisimetría; cargas e impuestos en
      totales; bloque comprimido contra la solución exacta y la suma de reacciones; el eje; el modo
      libre por su nombre. Catorce mutaciones cazadas (dos tras añadir comprobaciones). Casos 001
      y 002, idénticos bit a bit. **Dos hallazgos**, en el changelog: el umbral de «fase sin carga»
      y el suelo de redondeo de la convergencia.)
- [x] T7. Cargas nodales, puntuales, repartidas y peso propio — RF-6 — Hecho cuando: resultante y
      momento de cada carga, y peso propio, contra su valor cerrado. (Hecho el 2026-10-27:
      `reference/loads.py` y `analysis.stage_load`: peso propio por la regla del elemento (Z&T
      ecs. 2.13b y 5.19), cargas repartidas por Gauss-Legendre de 10 puntos (tabla 9.1, ec. 2.15),
      carga puntual con la transformación del elemento invertida (trabajo virtual de la ec. 2.10,
      derivación propia); en axisimetría, sobre el anillo. 13 tests en `test_loads_v002.py`: tabla
      9.1 dígito a dígito, trapecio de carga (resultante, momento, reparto), carga normal en lado
      curvo contra la cuerda girada, anillo, peso contra área y volumen, reparto del T6 por la
      ec. (8.38), carga puntual (nudo, resultante, momento, inversión), y a través del análisis la
      columna confinada bajo su peso, exacta con T6 en deformación plana y en axisimetría, y todas
      las cargas a la vez equilibradas por las reacciones. Quince mutaciones cazadas (dos tras
      afinar los tests). Hallazgos en el changelog.)
- [ ] T8. Preproceso de tensión inicial, constante y gravitatoria — RF-7 — Hecho cuando: campo
      gravitatorio más peso propio con estratos horizontales da desplazamiento nulo.
- [ ] T9. Fases y excavación por desactivación — RF-8, RF-9 — Hecho cuando: desactivar el anillo
      interior da lo mismo que la malla sin él, y una fase sin cambios da incremento nulo.

## Casos

- [ ] T10. Mallas estructuradas de prueba (rectángulo graduado T3/T6; cuarto de corona T3) —
      Hecho cuando: área exacta y ningún elemento degenerado.
- [ ] T11. Caso 003, STR-09 en axisimetría, con su estudio de convergencia y la identidad de la
      esfera finita — Hecho cuando: dentro de la tolerancia de D4 con la malla que la fija.
- [ ] T12. Caso 004, STR-04, con los estudios de convergencia y de dominio y la identidad del
      semiespacio truncado — Hecho cuando: dentro de la tolerancia de D4 con la malla y el dominio
      que la fijan.

## Rust y distribución

- [ ] T13. T3 y axisimetría en Rust; Mohr-Coulomb rechazado fuera de lo validado (D6) — RF-10,
      RF-11 — Hecho cuando: referencia = Rust a ~1e-10 en elemento, malla y casos.
- [ ] T14. CI de ruedas y congelado con los casos 003 y 004 — Hecho cuando: CI verde en las tres
      plataformas y el ejecutable resuelve los cuatro casos.
- [ ] T15. Cierre: `CHANGELOG_v0.0.2.md`, fichas STR-04 y STR-09 («Seguimiento») y criterios de
      finalización de `spec.md` marcados.
