# ADR-0001 — Lenguaje del motor de cálculo

- **Estado:** ACEPTADA CON CONDICIÓN (2026-10-27, propietario). Se reabre si la prueba de concepto
  no cumple los criterios de aceptación de abajo.
- **Contexto completo:** `../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/D_sintesis/S04_decision_lenguaje_motor.md`
  y el informe de investigación `S05_investigacion_lenguaje_motor.md` (fuera del repositorio).

## Contexto

La interfaz, el modelo y la orquestación se escriben en Python (reutilizando OGR Slip2D). El motor
numérico debe integrar leyes elastoplásticas punto a punto, repetir el análisis completo muchas veces
(reducción de resistencia, probabilístico, fases) y, en el futuro, ejecutar métodos explícitos
(diferencias finitas, elementos discretos) con millones de pasos. Lo desarrolla una persona con ayuda
intensiva de agentes de IA, y debe distribuirse con instaladores en Windows, macOS y Linux.

## Decisión

Núcleo numérico en **Rust**, expuesto a Python con **PyO3** y empaquetado con **maturin**. Frontera:
**una llamada por iteración global**. Solver lineal inicial SuperLU (SciPy); `faer` solo tras medirlo.

**Implementación de referencia en Python de cada elemento y de cada ley constitutiva, sin
excepciones** (también los modelos avanzados). Es el oráculo de los tests del núcleo Rust: el mismo
punto de Gauss y el mismo incremento de deformación deben dar el mismo resultado hasta el redondeo.
El código compilado nunca es la única verdad, y cualquier resultado se puede leer en Python.

## Criterios de aceptación de la prueba de concepto

Fijados **antes** de medir (`S05`, «Primer paso concreto»). La prueba: triángulo de 6 nudos,
elasticidad y Mohr-Coulomb en Python de referencia, NumPy vectorizado y Rust, sobre STR-01 y STR-02.

1. Python de referencia y Rust coinciden en punto material y en malla con tolerancia relativa del
   orden de 1e-10.
2. Los casos con solución cerrada cumplen la tolerancia fijada en su `esperado.json`.
3. Las ruedas se instalan y ejecutan en Windows, macOS ARM y Linux (CI con maturin-action) y pasan
   una prueba de congelado con PyInstaller.
4. El propietario lee y entiende el Mohr-Coulomb en Rust al menos tan bien como en Python.
5. **Rust es al menos ×10 más rápido que NumPy vectorizado en la integración constitutiva.** El
   umbral es una decisión del propietario, no una cifra publicada: es lo que debe ganar un segundo
   lenguaje para compensar su coste.

Si fallan 3 o 4, la alternativa es **C++ con nanobind** (o Numba para un motor sin horizonte DEM).
Si falla 5, se reabre esta decisión con las medidas delante.

## Alternativas

- **Python + NumPy/SciPy**: insuficiente para *return mapping* heterogéneo y para los métodos
  explícitos futuros.
- **Numba**: válido para prototipos; sin comprobación de límites por defecto, carreras de datos no
  detectadas y empaquetado pesado.
- **C++ (nanobind)**: ecosistema más rico; descartado en primera opción por seguridad de memoria y
  concurrencia en un proyecto desarrollado con IA y por el coste de distribuir dependencias nativas.
  Queda como alternativa si la prueba de concepto falla.

## Consecuencias

- Hay que aprender y mantener un segundo lenguaje en un núcleo pequeño y estable.
- Cada elemento y cada ley constitutiva existe dos veces (Rust y Python de referencia): el doble de
  trabajo, pero un oráculo independiente para los tests.
- Primer paso obligatorio: la **prueba de concepto** con los criterios de arriba.

## Resultado de la prueba de concepto (spec 001, 2026-10-27)

Medido con la implementación de referencia en Python validada antes contra soluciones cerradas
(Kirsch; Salençon con la zona de arista, D8), y las variantes NumPy (`poc/vectorized.py`) y Rust
(`rust/`, módulo `ogr_fem2d._engine`) detrás de la misma interfaz (`ogr_fem2d/engine/interface.py`).
El detalle, en `spec/features/001-prueba-de-concepto/tasks.md` y en `docs/changelog/CHANGELOG_v0.0.1.md`.

| # | Criterio | Resultado | ¿Cumple? |
|---|---|---|---|
| 1 | Python de referencia y Rust coinciden a ~1e-10 | 7e-16 en tensiones y 5e-16 en tangentes en punto material (todas las regiones del retorno); 1e-14 en malla, con las mismas iteraciones | **Sí** |
| 2 | Los casos cumplen la tolerancia de su `esperado.json` | 001 (Kirsch): 0.19 % en el peor punto (tolerancia 0.5 %); 002 (Salençon): 1.10 % con ψ = 0° y 1.47 % con ψ = 30° (tolerancia 2 %), R0 dentro de un elemento. La referencia de ur(a) en 002 es la solución exacta del modelo, porque la hipótesis de Salençon no se cumple con los datos de la ficha (D8) | **Sí** |
| 3 | Ruedas en Windows, macOS ARM y Linux, y congelado con PyInstaller | 15 trabajos de CI en verde: tres ruedas abi3; suite entera con los casos en Python 3.11, 3.12 y 3.13 en cada plataforma; el ejecutable congelado resuelve los dos casos fuera del árbol en las tres | **Sí** |
| 4 | El propietario entiende el Mohr-Coulomb en Rust al menos como en Python | Página lado a lado generada desde las fuentes; respuesta del propietario: «Rust se entiende perfectamente» | **Sí** |
| 5 | Rust ≥ ×10 más rápido que NumPy vectorizado en la integración constitutiva | **≈ ×9.6**: A/B en el mismo proceso, 9.3–9.9 (después de revisar las dos variantes por igual; 9.5–9.9 antes); medida oficial 10.2 (control 9.2). En la llamada completa por iteración (integración, fuerzas internas y rigidez) sobre la malla del caso 002, **unas 16 veces**. Equipo con carga de fondo constante del 32–39 % que no se podía cerrar; las medidas, limpias dentro del proceso (proporción CPU/reloj 0.97–1.01) | **No, por poco** |

Por la regla de este ADR, el criterio 5 sin cumplir **reabre la decisión con las medidas delante**.
La decisión del propietario: **pendiente**.
