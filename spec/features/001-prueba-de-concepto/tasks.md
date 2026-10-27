# Tareas — Spec 001, prueba de concepto

Pequeñas y verificables, ordenadas por dependencia. Si una tarea no se puede comprobar, no es una
tarea: es un deseo.

## Antes de programar

- [x] T0. El propietario responde D1–D6 de `spec.md` y aprueba el plan — Hecho cuando: las
      respuestas están anotadas en `spec.md`. (D1–D6 y D3 bis, 2026-10-27.)
- [x] T1. Conseguir y leer las fuentes (D5); comprobar contra ellas cada fórmula que se va a
      programar y las de las fichas `VER-STR-01` y `VER-STR-02` — Hecho cuando: una tabla en
      `plan.md` da, para cada fórmula, autor, año y ecuación o página, y lo que difiere de la ficha.
      (Hecho el 2026-10-27: tabla en «Formulación» y `comprobaciones/soluciones_cerradas.py`. Tres
      hallazgos: el desplazamiento con ψ = 30° no está impreso en Salençon 1969, y se respalda con
      la integración de su modelo; el signo de la (8.92) de Jaeger et al. en el texto extraído; y
      el efecto del contorno a 21 m, que llevó a D3 bis.)
- [x] T2. Licencias de `pyo3`, `numpy` (crate), `ndarray` y `pyinstaller` (D6) — Hecho cuando:
      anotadas y compatibles con AGPL-3.0, y el propietario da el OK. (Hecho el 2026-10-27:
      `spec.md`, D6.)

## Referencia en Python

- [x] T3. `pyproject.toml` (maturin, `ogr-core` fijado a `v0.1.0`) y `tests/_runner.py` con el
      runner de `ogr-core` — Hecho cuando: `python tests/_runner.py` corre en el `.venv` y su
      cabecera nombra el árbol y el núcleo compartido. (Hecho: además, con el Python del sistema
      el runner se niega con un mensaje claro, porque allí `ogr_core` es la copia de Slip2D.)
- [x] T4. Elemento T6: funciones de forma, cuadratura, B, rigidez, fuerzas internas — RF-1 — Hecho
      cuando: pasan la prueba de la parcela, el sólido rígido y la tensión inicial uniforme.
      (Hecho: isoparamétrico, regla cuadrática de la tabla 9.2 de Zienkiewicz y Taylor (2000),
      con los puntos en el centro de los lados; 14 tests.)
- [x] T5. Ley elástica y Mohr-Coulomb con retorno en plano, arista y vértice — RF-2, RF-4 — Hecho
      cuando: pasan los tests de punto material de las tres regiones y la tolerancia del retorno
      está fijada y justificada. (Hecho: `mohr_coulomb.py`, perfectamente plástico y en forma
      cerrada (observación 8.1 de de Souza Neto et al.), construido desde la ec. (8.68) y los
      vectores de flujo; tolerancia 1e-12 relativa, justificada en el código; 10 tests, y una
      comprobación con errores introducidos a propósito: los tests cazan un vector de flujo de
      arista equivocado, el signo del término volumétrico y la elección de arista invertida.
      Con ψ = 0 el retorno al vértice se rechaza con un error, como manda la fuente.)
- [x] T6. Malla radial de T6 de un cuarto de corona, con el radio exterior como parámetro (21 m y
      100 m) — RF-7 — Hecho cuando: área total exacta (a la tolerancia de la cuadratura) y ningún
      elemento degenerado. (Hecho: `ogr_fem2d/engine/mesh_radial.py`. Cada nudo, esquina o
      intermedio, es la imagen exacta de su punto (r, θ): los intermedios de los arcos quedan sobre
      el círculo y los de los lados radiales en su centro; gradación radial geométrica. El área por
      cuadratura coincide a 1e-16 con la cuadratura de la parábola de Arquímedes, y la diferencia
      con π(b² − a²)/4 baja como Δθ⁴; det J > 0 en nudos y puntos de integración; 8 tests, que
      cazan seis errores introducidos a propósito.)
- [x] T7. Escalones, iteraciones con rigidez inicial e historia de convergencia — RF-5, RF-6 —
      Hecho cuando: la no convergencia se detecta y se informa en un test. (Hecho:
      `ogr_fem2d/engine/reference/solver.py`, de Souza Neto et al. (2008), §4.2, Box 4.1 y 4.2,
      ecs. (4.60)–(4.77), Newton modificado con la rigidez inicial (§4.2.6); la carga de la
      excavación es el término de tensión inicial de la ec. (2.13b) de Zienkiewicz y Taylor (2000).
      Cargas en totales (D2). El residuo se divide por la norma de la carga de la fase, no por
      ‖f_ext‖ como en la (4.77), que al final de una excavación es cero. `update_points` es la
      llamada por iteración global que sustituirá Rust. 9 tests, que cazan cinco errores
      introducidos a propósito; una sexta mutación sobrevivió (acumular «plastificó alguna vez») y
      ese código se quitó (regla 7). Hallazgo: la rigidez inicial converge muy despacio en
      Mohr-Coulomb y empeora al refinar; ver el changelog. **Resuelto con D7**: Newton completo
      con la tangente consistente de de Souza Neto et al. (2008), §8.2.4, comprobada contra su
      derivada numérica en las cinco regiones y contra la subrutina CTMC (plano y aristas, a
      1e-15); 6–8 iteraciones por escalón con convergencia cuadrática, y la misma solución
      discreta que la rigidez inicial.)
- [ ] T8. Identidad del anillo de 21 m (D3 bis): elástico contra `lame_fixed_outer` y Mohr-Coulomb
      (ψ = 0° y 30°) contra `salencon_finite`, con tres mallas — Hecho cuando: el error baja con
      cada refinamiento y la tasa queda anotada. (Parte elástica hecha:
      `tests/test_ring_identity_v001.py`, tres mallas anidadas que dividen h por dos; el error
      máximo en ur(a) baja 11.0 % → 1.53 % → 0.201 % (→ 0.026 % con una cuarta), orden ≈ 2.9; en
      σθ(a), orden 1.5–1.9; en el campo de ur, igual que en ur(a). La parte de Mohr-Coulomb espera
      la decisión del propietario sobre las iteraciones, hallazgo de la T7.)
- [ ] T9. Casos `001-kirsch-hueco-elastico` y `002-salencon-hueco-mohr-coulomb` (ψ = 0° y 30°),
      con el contorno a 100 m: las tolerancias de D3 (0.5 % y 2 %) escritas en `esperado.json`
      **antes** del estudio de convergencia, que elige la malla que las cumple; y la comprobación
      de que σz es la principal intermedia en los puntos plastificados — Hecho cuando: los tres
      pasan con esa malla, o el incumplimiento queda reportado como hallazgo. (Caso 001 hecho:
      tolerancias en `esperado.json` antes del estudio (commit 962f504), malla 8 × 32 con
      crecimiento 1.69^¼, peor error 0.19 % en ur(a) y en σθ(a); `tests/test_validation_cases_v001.py`
      recorre los casos y declara los pendientes. Caso 002 escrito con sus tolerancias;
      **pendiente de decisión del propietario por un hallazgo**: la hipótesis de Salençon (σz
      intermedia) no se cumple cerca de la pared, ver el changelog.)

## Las otras dos variantes

- [ ] T10. Interfaz común de las variantes — RF-3 — Hecho cuando: la referencia la cumple y un test
      corre los casos con cualquier variante
- [ ] T11. Variante NumPy vectorizada — RF-3 — Hecho cuando: identidad con la referencia en punto
      material y en malla
- [ ] T12. Variante Rust con PyO3 (`rust/`, módulo `ogr_fem2d._engine`), construida con `maturin
      develop` en el `.venv` — RF-3 — Hecho cuando: identidad con la referencia a ~1e-10 en punto
      material y en malla (criterio 1)

## Medidas y distribución

- [ ] T13. Conjunto de medida con semilla (regiones elástica, plano, arista, vértice) y
      `poc/benchmark.py` con A/B en el mismo proceso — RF-8 — Hecho cuando: las tres variantes
      medidas con sus controles; la razón Rust/NumPy anotada (criterio 5)
- [ ] T14. CI de ruedas con `maturin-action` en Windows, macOS ARM y Linux, con los casos — RF-9 —
      Hecho cuando: verde en las tres (criterio 3, primera parte)
- [ ] T15. Congelado con PyInstaller y comprobación del ejecutable — RF-10 — Hecho cuando: el
      ejecutable resuelve los dos casos (criterio 3, segunda parte)
- [ ] T16. Mohr-Coulomb en Rust y en Python lado a lado para el propietario — Hecho cuando: el
      propietario dice si lo entiende al menos igual (criterio 4)

## Cierre

- [ ] T17. Informe de los cinco criterios con sus números y la decisión del propietario sobre el
      ADR-0001 — Hecho cuando: el ADR dice «aceptada» o «reabierta» con las medidas citadas
- [ ] T18. Changelog `CHANGELOG_v0.0.1.md` registrando **qué se encontró**
