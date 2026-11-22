# Tareas — Spec 003, malla

Pequeñas y verificables, ordenadas por dependencia. Al terminar cada una: este archivo y el
changelog al día, la suite entera en verde y el commit directo en `main` (sin push hasta que la
propietaria lo pida). Cada test con su cabecera y con dientes: mutaciones sistemáticas
(`{etiqueta: (archivo, texto, sustituto)}`), anotadas aquí.

## Antes de programar

- [x] T0. Spec y plan aprobados, con D1–D13 y la enmienda de RF-5 — Hecho cuando: anotados en
      `spec.md` y `plan.md`. (Hecho el 2026-11-22.)
- [x] T1. **v0.0.7: la fijación sube a `ogr-core` v0.2.3** (D1) — `pyproject.toml`; las líneas de
      `AGENTS.md`, `README.md`, `tech-stack.md` y ADR-0002 que dicen cuál es la fijación de hoy (las
      que cuentan historia, no); el `.venv` reinstalado con `--no-deps --force-reinstall`; versión
      0.0.7 en `pyproject.toml` y `ogr_fem2d.__version__` — Hecho cuando: la suite entera da
      `shared: ogr_core 0.2.3 … (installed, no git tree)` y sale en verde, la corrida con
      `--dev-core` contra `../../Core/OGR-Core` (`0.2.4.dev0`) también, `CHANGELOG_v0.0.7.md`
      escrito, commit hecho y la propietaria avisada de la fila de `docs/consumidores.md` (OGR-Core)
      y de `suite.toml` (OGR_Suite), que no se tocan desde aquí. (Hecho el 2026-11-22: 205 de 205
      en las dos corridas, sin fugas; dos mutaciones de los tests de la fijación, cazadas;
      `CHANGELOG_v0.0.7.md`.)
- [ ] T2. **La petición a OGR-Core** (D2a) — un escrito en `Promts_desarrollo/` con lo de `plan.md`,
      «Lo que se pide a OGR-Core»: entrada, algoritmo con sus fuentes y páginas, salida, medidas de
      calidad, determinismo, los tests que lo demostrarían y el hallazgo de `generate_mesh` como
      nota — Hecho cuando: el escrito está y la propietaria lo ha llevado a la sesión del núcleo.
      (Escrito el 2026-11-22: `Promts_desarrollo/2026_11_22_peticion_ogr_core_mallador_de_calidad.md`,
      que vale pegado tal cual, con el sondeo dentro y comprobado. La sesión del núcleo no puede leer
      `Promts_desarrollo` ni la bibliografía: los tres PDF hay que dárselos aparte. Falta que la
      propietaria lo lleve.)

## Lo que no espera al núcleo

- [x] T3. `ogr_fem2d/mesh/geometry.py` y `docs/malla/entrada.md`: la entrada (regiones, segmentos con
      arco opcional, parámetros) y su validación — RF-1 — Hecho cuando: cada regla tiene su test con
      una entrada que la incumple y el error dice el sitio. La versión pasa a 0.0.8 y empieza
      `CHANGELOG_v0.0.8.md`. (Hecho el 2026-11-22: 25 reglas, la tabla de casos las cubre
      exactamente; 19 tests en `test_mesh_input_v008.py`; 36 mutaciones, dos sobrevivían al
      principio: una era una comprobación redundante, que se quitó, y la otra llevó a
      `test_a_region_given_twice`; al final, 35 de 35 cazadas. Suite entera 224 de 224.)
- [x] T4. `discretize.py`: paso 1, con número de divisiones repartido o forzado por segmento y los
      arcos con sus nudos sobre la circunferencia — RF-2, D5, D10 — Hecho cuando: los nudos por
      segmento, los extremos compartidos y \|x − c\| = R a redondeo tienen su test. (Hecho el
      2026-11-22: 15 tests en `test_mesh_discretize_v008.py`; 18 mutaciones, cuatro sobrevivían al
      principio y llevaron a tres tests y a un caso de desempate; al final, 18 de 18.)
- [x] T5. `quadratic.py`: T3 → T6, un nudo intermedio por lado, en el punto medio o en el punto
      medio del arco — RF-10, D4 — Hecho cuando: unicidad por lado, posición, y área = rectilíneo
      ± 2/3·cuerda·flecha, probados sobre mallas T3 que ya existen. (Hecho el 2026-11-22: 6 tests en
      `test_mesh_quadratic_v008.py`, sobre el rectángulo de la spec 002, el cuarto de corona de la
      001 y el generador del núcleo; 8 mutaciones, 8 cazadas.)
- [x] T6. `checks.py`: jacobiano del T6 en los seis nudos y en los puntos de integración (Z&T §9.2,
      §9.5), conformidad, Euler (V − E + T = 1 − H), conexión y regiones unidas por un nudo — RF-13,
      RF-14 — Hecho cuando: un nudo intermedio fuera de la mitad central se rechaza con su motivo y
      cada comprobación caza su malla rota a propósito. (Hecho el 2026-11-22: 13 tests en
      `test_mesh_checks_v008.py`; 17 mutaciones, 17 cazadas al final. **Anomalía corregida, para
      revisar**: nudos y puntos de integración no bastan; se halla el mínimo exacto de det J en
      todo el elemento, y se enmendó el plan.)
- [x] T7. Parcela sobre mallas generadas (Z&T §9.7, teorema 3): campo lineal exacto con T3 y T6 de
      lados curvos, en deformación plana y en axisimetría, a través del motor — Hecho cuando: en
      verde y con dientes. (Hecho el 2026-11-22: 3 tests en `test_mesh_patch_v008.py`; 3 mutaciones
      de `quadratic.py` contra ellos, 3 cazadas.)
- [x] T8. `radial.py`: el anillo completo — RF-8, D8 — Hecho cuando: los radios siguen la
      progresión y el anillo a 100 m da σθ(a) y ur(a) a menos del 0.5 % de `lame_fixed_outer`.
      (Hecho el 2026-11-22: 0.020 % y 0.159 % con 32 × 32; 8 tests en
      `test_mesh_radial_v008.py`; 10 mutaciones, 10 cazadas. El hueco no se malla.)
- [x] T9. Salida para el motor: `EngineModel` (nudos, elementos, material por elemento) y el mapa
      segmento → nudos y lados — RF-15 — Hecho cuando: probado con las mallas de T5 y T8. (Hecho el
      2026-11-22, antes que la T8, que la usa: 5 tests en `test_mesh_output_v008.py` con la malla
      del núcleo de la T5, T3 y T6; la de T8 la prueba la propia T8; 6 mutaciones, 6 cazadas.)
- [x] T10. `comprobaciones/soluciones_cerradas.py`: Kirsch no hidrostático, el desplazamiento que
      causa la excavación (JCZ ecs. 8.121–8.125) — Hecho cuando: con σ1 = σ2 da la (8.90), y sus
      deformaciones por la ley de Hooke dan el cambio de tensión de las (8.113)–(8.115). (Hecho el
      2026-11-22: las dos cosas, a 10⁻¹⁴ y a 10⁻⁶; 5 tests en `test_kirsch_closed_v008.py`; 8
      mutaciones, 8 cazadas.)

## Con el generador del núcleo (`--dev-core` hasta que esté etiquetado)

- [ ] T11. `sizing.py`: cotas uniforme (h o N), graduada (cota máxima opcional) y de ventanas y
      polígonos — RF-5 a RF-7, D5, D9 — Hecho cuando: cada cota cumplida en la malla resultante y
      cada opción mueve la malla (regla 7). (2026-11-22, parte hecha: `sizing.py` y sus tests como
      función; falta comprobarla sobre la malla, con el núcleo.)
- [ ] T12. `mesher.py`: los dos pasos de principio a fin; los vértices añadidos sobre cuerdas llevados
      al arco (D13); las notas con cada valor por defecto (regla 12); determinismo — RF-3, RF-11,
      RF-15 — Hecho cuando: cada segmento es unión de lados, D13 comprobado con el jacobiano, y dos
      mallados iguales bit a bit. (2026-11-22, parte hecha: `pslg.py`, el PSLG para el núcleo con
      semillas y vacíos, y la proyección de D13. **Hallazgo: D13 puede invertir elementos; D14
      abierta en la spec.** Falta el mallador de dos pasos, con el núcleo.)
- [ ] T13. Las garantías vistas desde FEM2D y el resumen de calidad: cota B (teorema 4), cota de
      tamaño, Delaunay final, teorema 8 con B = 1.93, teorema 12 y terminación con un ángulo de
      entrada de 5°; medidas de calidad (1, 0, < 0, invariantes) — RF-4, RF-9, RF-12 — Hecho cuando:
      en verde y con dientes.
- [ ] T14. La fijación sube a la versión del núcleo que trae la petición, en un commit propio — Hecho
      cuando: la suite entera la nombra en `shared:` y sale en verde, y la propietaria está avisada
      de la fila de `docs/consumidores.md`.

## El caso y el cierre

- [ ] T15. Caso `005-kirsch-malla-general`: `esperado.json` con las tolerancias **antes de medir**
      (malla a `null`), estudio con 16, 32, 64 y 128 divisiones del hueco, la malla que fija la
      tolerancia, y la identidad de Kirsch (hidrostática y p2 = p1/2) sobre la misma malla — D12 —
      Hecho cuando: el caso cumple el 0.5 % en σθ(a) y ur(a) con la malla del estudio.
      (2026-11-22, parte hecha: `caso.md` y `esperado.json` con las tolerancias antes de medir y la
      malla a `null`; el caso, en `PENDING` de `test_validation_cases_v001.py`.)
- [ ] T16. Rendimiento: tiempo de mallado del caso 005 y del mayor caso de la fase 1, medido con la
      máquina sola — Hecho cuando: anotado en el changelog, y si pide Rust, propuesto (no hecho).
- [ ] T17. Cierre: cada fórmula de «Formulación» citada en el código; casos 001 a 004 bit a bit;
      ficha STR-01 con su «Seguimiento»; changelog v0.0.8 completo — Hecho cuando: los criterios
      de finalización de `spec.md`, todos marcados.
