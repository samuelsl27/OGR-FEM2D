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
- [x] T8. Identidad del anillo de 21 m (D3 bis): elástico contra `lame_fixed_outer` y Mohr-Coulomb
      (ψ = 0° y 30°) contra `salencon_finite`, con tres mallas — Hecho cuando: el error baja con
      cada refinamiento y la tasa queda anotada. (Parte elástica:
      `tests/test_ring_identity_v001.py`, tres mallas anidadas que dividen h por dos; el error
      máximo en ur(a) baja 11.0 % → 1.53 % → 0.201 % (→ 0.026 % con una cuarta), orden ≈ 2.9; en
      σθ(a), orden 1.5–1.9; en el campo de ur, igual que en ur(a). Parte de Mohr-Coulomb, contra
      `salencon_edge_finite` y no `salencon_finite` (D8: la hipótesis de Salençon no se cumple
      cerca de la pared), con Newton (D7), cinco escalones: el error máximo en ur(a) baja 70.7 % →
      11.0 % → 1.13 % (ψ = 0°) y 143.8 % → 52.8 % → 9.45 % (ψ = 30°; con las dos mallas siguientes
      de la familia, 1.84 % y 0.34 %), orden ≈ 2.4 con las finas; R0 dentro de un elemento; y las
      regiones del retorno, arista dentro de r_e y plano fuera, salvo en un elemento a cada lado.)
- [x] T9. Casos `001-kirsch-hueco-elastico` y `002-salencon-hueco-mohr-coulomb` (ψ = 0° y 30°),
      con el contorno a 100 m: las tolerancias de D3 (0.5 % y 2 %) escritas en `esperado.json`
      **antes** del estudio de convergencia, que elige la malla que las cumple; y la comprobación
      de que σz es la principal intermedia en los puntos plastificados — Hecho cuando: los tres
      pasan con esa malla, o el incumplimiento queda reportado como hallazgo. (Caso 001 hecho:
      tolerancias en `esperado.json` antes del estudio (commit 962f504), malla 8 × 32 con
      crecimiento 1.69^¼, peor error 0.19 % en ur(a) y en σθ(a); `tests/test_validation_cases_v001.py`
      recorre los casos y declara los pendientes. Caso 002 hecho: la hipótesis de Salençon (σz
      intermedia) no se cumple para r < 1.2814 m, y por D8 ur(a) se compara con la solución
      exacta del modelo (Salençon más la zona de arista), con los valores cambiados antes del
      estudio (commit d9adb26); cada variante con la primera malla de la familia que cumple el
      2 %: ψ = 0°, 8 × 32 (1.10 %; la de 16 × 64 no converge con Newton); ψ = 30°, 16 × 64
      (1.47 %); cinco escalones; R0 dentro de un elemento. La comprobación de σz intermedia se
      sustituyó por la de regiones (arista dentro de r_e, plano fuera), que el modelo cumple.)

## Las otras dos variantes

- [x] T10. Interfaz común de las variantes — RF-3 — Hecho cuando: la referencia la cumple y un test
      corre los casos con cualquier variante. (Hecho: `ogr_fem2d/engine/interface.py`. Una sola
      llamada por iteración, `update(start, du)`, que devuelve tensiones, fuerzas internas,
      plasticidad, tangentes y la rigidez w·Bᵀ D B de cada punto en un patrón fijo (el ensamblaje
      también queda dentro de la variante; Python solo factoriza y resuelve); `integrate` para la
      integración constitutiva sola (identidad en punto material y criterio 5); arrays de NumPy
      como transporte. `solve_stage(..., variant=)`; `ReferenceVariant` la cumple.
      `tests/test_variants_v001.py`: el contrato (comprobado contra Bᵀ D B construida con la B
      entera, con tangentes no simétricas para que se note una rigidez traspuesta), una variante
      que cuenta llamadas ve exactamente una por iteración, y los casos corren con cualquier
      variante.)
- [x] T11. Variante NumPy vectorizada — RF-3 — Hecho cuando: identidad con la referencia en punto
      material y en malla. (Hecho: `poc/vectorized.py`, sin bucles por punto en Python: cada
      región del retorno se calcula para todos los puntos y se elige con máscaras, en el orden y
      con la tolerancia de la referencia. Identidad a 6e-16 en tensiones y 2e-15 en tangentes en
      punto material (todas las regiones, también estados sobre la superficie donde solo decide la
      tolerancia) y a 1e-13 en malla, con las mismas iteraciones; los dos casos pasan con ella en
      7 s frente a 47 s de la referencia. 4 tests, que cazan cuatro errores introducidos a
      propósito.)
- [x] T12. Variante Rust con PyO3 (`rust/`, módulo `ogr_fem2d._engine`), construida con `maturin
      develop` en el `.venv` — RF-3 — Hecho cuando: identidad con la referencia a ~1e-10 en punto
      material y en malla (criterio 1). (Hecho: `rust/src/` con `elastic.rs`, `mohr_coulomb.rs` y
      `t6.rs`, gemelos de la referencia función a función y con los mismos nombres (para la T16),
      y `lib.rs` con la frontera (`integrate`, `internal_forces`, `update`); pyo3 0.30 con abi3
      para Python ≥ 3.11 y numpy 0.30 (D6; ndarray llega a través de numpy, no hizo falta
      declararlo); `ogr_fem2d/engine/compiled.py` la pone detrás de la interfaz. Construida con
      `maturin develop --release --skip-install`, que deja el módulo en el árbol sin reinstalar
      nada. **Criterio 1 cumplido**: 7e-16 en tensiones y 5e-16 en tangentes en punto material, y
      1e-14 en malla, con las mismas iteraciones; los dos casos de validación pasan con Rust.
      5 tests, uno de ellos contra un módulo más viejo que sus fuentes; cazan dos errores
      introducidos en el código de Rust.)

## Medidas y distribución

- [x] T13. Conjunto de medida con semilla (regiones elástica, plano, arista, vértice) y
      `poc/benchmark.py` con A/B en el mismo proceso — RF-8 — Hecho cuando: las tres variantes
      medidas con sus controles; la razón Rust/NumPy anotada (criterio 5). (Hecho: conjunto de
      100 000 puntos de Mohr-Coulomb, ψ = 0°, 15° y 30°, con 40 % elástico, 30 % plano, 10 % cada
      arista y 10 % vértice, la región decidida por la referencia; A/B en el mismo proceso, una
      ronda y la ronda de control; un hilo para todos. Resultado en
      `poc/resultados/benchmark_2026-10-27.*`. Integración constitutiva: referencia 166 µs/punto,
      NumPy 4.9 µs/punto, Rust 0.52 µs/punto; **NumPy / Rust = 9.5 (control 8.6)**. Llamada por
      iteración en la malla del caso 002: 1.6 s, 85 ms y 7.6–9.2 ms; ensamblaje 40 ms,
      factorización 75–94 ms, solución 3 ms. **Esa medida no es válida**: se hizo con el equipo
      cargado (los demás programas usaban del 36 % al 99 % de la CPU), y por eso el mismo código
      dio 9.5 en una ejecución y 10.4–12.3 en otra. El benchmark registra ahora el estado del
      equipo y la proporción CPU/reloj de cada medida, y se niega a medir sin el equipo en reposo.
      Repetida con Chrome cerrado (el resto de la carga, 19–29 %, no se puede cerrar): **NumPy /
      Rust = 9.6 (control 9.6)** con proporción CPU/reloj 0.96–0.99, y en otra ejecución **8.6
      (control 10.9)**, con la primera ronda de Rust interrumpida (0.93). Después, por indicación
      del propietario, **revisión de las dos variantes por igual** antes de volver a medir: en
      NumPy la tangente se calcula entrada a entrada (sin matrices 3 × 3 por punto ni productos de
      matrices por lotes); en Rust, sin reservas de memoria por punto. A/B en el mismo proceso
      (`poc/resultados/revision_variantes_AB_2026-10-27.txt`): las dos ganan lo mismo (×1.3–1.4)
      y NumPy / Rust queda en **9.3–9.9**, igual que antes de revisar (9.5–9.9); medida oficial
      (`benchmark_2026-10-27_195205`): **10.2 (control 9.2)**, y unas 16 veces en la llamada por iteración. **Criterio
      5: en torno a ×9.6 en la integración constitutiva, justo por debajo del ×10**; decisión del
      propietario (T17).)
- [x] T14. CI de ruedas con `maturin-action` en Windows, macOS ARM y Linux, con los casos — RF-9 —
      Hecho cuando: verde en las tres (criterio 3, primera parte). (Hecho:
      `.github/workflows/wheels.yml`: una rueda abi3 por plataforma (Linux x86_64 manylinux,
      Windows x64, macOS ARM); cada una se instala con sus dependencias (`ogr-core` desde su
      etiqueta), se comprueba fuera del árbol (`.github/scripts/wheel_check.py`: el paquete
      instalado, y Rust igual que la referencia) y la suite entera, con los dos casos de
      validación, corre sobre su módulo compilado con Python 3.11, 3.12 y 3.13: los 12 trabajos
      en verde (https://github.com/samuelsl27/OGR-FEM2D/actions/runs/40568629109). La primera ejecución falló en macOS en un solo test, el de la lectura
      del estado del equipo del benchmark, que no sabía leerlo allí; los casos pasaban. **Criterio
      3, primera parte, cumplido.**)
- [x] T15. Congelado con PyInstaller y comprobación del ejecutable — RF-10 — Hecho cuando: el
      ejecutable resuelve los dos casos (criterio 3, segunda parte). (Hecho: `poc/freeze/casos.py`
      resuelve los dos casos de validación con la variante Rust y los compara con su
      `esperado.json`, como el test de validación (peor nudo y punto, R0 y regiones del retorno);
      `poc/freeze/build.py` lo congela con PyInstaller 6.22.3 (carpeta, con los `esperado.json`
      dentro) y ejecuta el programa desde una carpeta temporal fuera del árbol, sin `PYTHONPATH`
      ni `PYTHONHOME`, exigiendo que esté congelado, que use el motor que va dentro y que salga
      con 0. Resuelve los dos casos en Windows en local y en la CI en las tres plataformas
      (https://github.com/samuelsl27/OGR-FEM2D/actions/runs/40570492239): Windows 3.4 s y 119 MB, macOS ARM 2.7 s y 83 MB, Linux 2.3 s y 228 MB. Una
      tolerancia estrechada a propósito dentro del ejecutable lo hace fallar. **Criterio 3
      cumplido entero.**)
- [ ] T16. Mohr-Coulomb en Rust y en Python lado a lado para el propietario — Hecho cuando: el
      propietario dice si lo entiende al menos igual (criterio 4). (Preparado: `poc/lado_a_lado.py`
      genera la página desde las fuentes tal cual, catorce pares de piezas con la nota de lo que
      cambia entre los dos lenguajes y una guía de la sintaxis de Rust que aparece; publicada para
      el propietario el 2026-10-27. **Pendiente de su respuesta.**)

## Cierre

- [ ] T17. Informe de los cinco criterios con sus números y la decisión del propietario sobre el
      ADR-0001 — Hecho cuando: el ADR dice «aceptada» o «reabierta» con las medidas citadas
- [ ] T18. Changelog `CHANGELOG_v0.0.1.md` registrando **qué se encontró**
