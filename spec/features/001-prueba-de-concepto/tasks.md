# Tareas — Spec 001, prueba de concepto

Pequeñas y verificables, ordenadas por dependencia. Si una tarea no se puede comprobar, no es una
tarea: es un deseo.

## Antes de programar

- [ ] T0. El propietario responde D1–D6 de `spec.md` y aprueba el plan — Hecho cuando: las
      respuestas están anotadas en `spec.md`. **D1–D4 y D6 anotadas (2026-10-27); falta D5.**
- [ ] T1. Conseguir y leer las fuentes (D5); comprobar contra ellas cada fórmula que se va a
      programar y las de las fichas `VER-STR-01` y `VER-STR-02` — Hecho cuando: una tabla en
      `plan.md` da, para cada fórmula, autor, año y ecuación o página, y lo que difiere de la ficha
- [x] T2. Licencias de `pyo3`, `numpy` (crate), `ndarray` y `pyinstaller` (D6) — Hecho cuando:
      anotadas y compatibles con AGPL-3.0, y el propietario da el OK. (Hecho el 2026-10-27:
      `spec.md`, D6.)

## Referencia en Python

- [ ] T3. `pyproject.toml` (maturin, `ogr-core` fijado a `v0.1.0`) y `tests/_runner.py` con el
      runner de `ogr-core` — Hecho cuando: `python tests/_runner.py` corre en el `.venv` y su
      cabecera nombra el árbol y el núcleo compartido
- [ ] T4. Elemento T6: funciones de forma, cuadratura, B, rigidez, fuerzas internas — RF-1 — Hecho
      cuando: pasan la prueba de la parcela, el sólido rígido y la tensión inicial uniforme
- [ ] T5. Ley elástica y Mohr-Coulomb con retorno en plano, arista y vértice — RF-2, RF-4 — Hecho
      cuando: pasan los tests de punto material de las tres regiones y la tolerancia del retorno
      está fijada y justificada
- [ ] T6. Malla radial de T6 de un cuarto de corona — RF-7 — Hecho cuando: área total exacta (a la
      tolerancia de la cuadratura) y ningún elemento degenerado
- [ ] T7. Escalones, iteraciones con rigidez inicial e historia de convergencia — RF-5, RF-6 —
      Hecho cuando: la no convergencia se detecta y se informa en un test
- [ ] T8. Lamé: estudio de convergencia con tres mallas — Hecho cuando: el error baja con cada
      refinamiento y la tasa queda anotada
- [ ] T9. Casos `001-kirsch-hueco-elastico` y `002-salencon-hueco-mohr-coulomb` (ψ = 0° y 30°):
      las tolerancias de D3 (0.5 % y 2 %) escritas en `esperado.json` **antes** del estudio de
      convergencia, que elige la malla que las cumple — Hecho cuando: los tres pasan con esa malla,
      o el incumplimiento queda reportado como hallazgo

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
