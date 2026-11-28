# Plan de implementación — Spec 007, tolerancia, colapso y escalones

> **Aprobado (2026-11-28)**, con D1–D14 de `spec.md`. Dos
> partes (D13): **A, v0.0.16**, el motor y STR-05; **B, v0.0.17**, el modelo, las operaciones, el
> `.h5` y la interfaz. No se toca `rust/` ni la CI: commits directos en `main`.

## Enfoque

0. **T0, antes de programar.** El OK de D1–D14. Las fuentes que faltan (Crisfield 1991, Hill 1950 o
   Prandtl 1921, Sloan y Randolph 1982), pedidas a la propietaria: ninguna bloquea la parte A, pero
   la búsqueda lineal (D5, 3) y la comprobación de la zapata flexible (D6) dependen de ellas.
1. **Parte A, v0.0.16: el motor.**
   - Primero lo que no cambia ningún número: Tresca en un punto de Gauss (RF-12) y el diagnóstico de
     la robustez (D5, 1), que se reporta antes de tocar nada (regla 6).
   - Después el bucle: el progreso y la cancelación por iteración (D10), los incrementos con su
     estado, el factor alcanzado (D2) y la marca del suelo de redondeo (D12), la lista de factores
     (RF-6). Los casos 001 a 007, bit a bit.
   - Luego STR-05: el caso escrito con sus tolerancias y los criterios de los estudios **antes de
     medir** (en un commit propio), el estudio de dominio y de malla, el estudio de los valores por
     defecto (D1, D3) y los valores nuevos en el motor.
   - Por último la variante de carga (RF-2), las identidades y la robustez (RF-8).
2. **Parte B, v0.0.17: el modelo y la interfaz.** Los ajustes en el `.ogrfem2d` (D9), su operación,
   el `.h5` con los incrementos (D11), el informe, el diálogo, la ventana de cálculo por iteración y
   el cierre.

El bucle sigue en Python para las dos variantes (spec 001, T10). Rust no cambia: la identidad
referencia–Rust se comprueba en STR-05 con una malla gruesa.

## Lo que se reutiliza

| De dónde | Qué | Para qué |
|---|---|---|
| `engine/reference/solver.py` | `solve_stage`, la partición, `NotConvergedError`, `NO_LOAD`, `StageResult.increments` | El bucle que se amplía (D2, D10, D12) |
| `engine/reference/mohr_coulomb.py`, `rust/src/mohr_coulomb.rs` | El Mohr-Coulomb perfecto con su tangente | Tresca con φ = ψ = 0 (D14), sin cambios |
| `engine/analysis.py` | Las fases en totales, los desplazamientos impuestos, las reacciones | Las dos variantes de STR-05 (D6) |
| `engine/mesh_structured.py`, `tests/_strip.py` | La malla graduada de la faja del caso 004 | La malla de STR-05 (D6) |
| `tests/_hole.py`, `comprobaciones/soluciones_cerradas.py` (spec 001) | El anillo y `salencon_edge_finite` | El diagnóstico y RF-8 |
| `results/calculate.py`, `results/store.py`, `api/worker.py`, `gui/compute_window.py` | El progreso (006, D9), la historia en el `.h5`, el trabajo en subproceso | Llevar el progreso por iteración y los incrementos hasta la ventana (D10, D11) |
| `model/ogr_file.py`, `model/edit.py`, `model/translate.py` | El archivo, las ediciones puras, `deciding_values` | Los ajustes del cálculo en el modelo (D9) |
| `ogr_core.progress` (v0.2.13) | El archivo de progreso del trabajo | El progreso por iteración, sin pedir nada al núcleo |

## Archivos que se tocan

**Parte A (v0.0.16)**

| Archivo | Qué | RF / D |
|---|---|---|
| `tests/test_tresca_point_v0016.py` (nuevo) | Mohr-Coulomb con φ = ψ = 0 frente al retorno de Tresca de dSN §8.1, escrito en el test; corte simple; el vértice nunca pedido; Rust | RF-12, D14 |
| `spec/features/007-convergencia-y-colapso/comprobaciones/diagnostico_robustez.py` (nuevo) | El diagnóstico de D5 (1): el 002 con 16 × 64 y el anillo con 16 × 48, con ψ = 0°; no es un test | D5 |
| `engine/reference/solver.py` | `progress` y `should_stop` (D10); `Cancelled`; los incrementos con su estado (`converged`, `converged at the rounding floor`, `cut: …`); `NotConvergedError` con el factor alcanzado; `factors` como alternativa a `steps` (RF-6) | RF-3, RF-4, RF-6, RF-10 |
| `engine/model.py` | `Stage.factors` (opcional); los valores por defecto del estudio | RF-1, RF-5, RF-6 |
| `engine/analysis.py` | Pasa `progress`, `should_stop` y `factors`; los incrementos en `StageOutcome` | RF-9, RF-10 |
| `validacion/casos/008-prandtl-zapata-tresca/` (nuevo) | `caso.md`, `esperado.json`: las dos variantes, las tolerancias y los criterios de los estudios, antes de medir | D6, D7 |
| `tests/_footing.py` (nuevo), `tests/test_case008_prandtl_v0016.py` (nuevo) | El modelo de la zapata (las dos variantes) y el caso | RF-2, H3 |
| `spec/features/007-convergencia-y-colapso/comprobaciones/estudio_*.py` (nuevos) | Los estudios de dominio, de malla y de los valores por defecto, con su salida en el changelog | D1, D3, D7 |
| `tests/test_solver_settings_v0016.py` (nuevo) | La regla 7 de cada ajuste; las identidades | RF-11 |
| `docs/motor/convergencia.md` (nuevo) | El criterio, el colapso, los escalones, la partición y los valores por defecto, con su fuente y su estudio | RF-1 |

**Parte B (v0.0.17)**

| Archivo | Qué | RF / D |
|---|---|---|
| `model/model.py`, `model/ogr_file.py` | `SolverSettings` en el modelo; `format_version` 2, que lee el 1 con los valores por defecto | D9 |
| `model/edit.py`, `model/translate.py`, `model/report_messages.py` | La edición pura; la traducción al `Stage` del motor; `deciding_values` desde el modelo | D9, regla 12 |
| `api/ops/analysis.py` (o `api/ops/project.py`), `docs/operaciones/catalogo.md` | La operación de los ajustes (nombre en la T12, el de Slip2D si hace lo mismo) | D9 |
| `results/calculate.py`, `api/worker.py` | El progreso por iteración y cancelar dentro de la fase (D10) | RF-10 |
| `results/store.py` | Los incrementos por fase (D11); se siguen leyendo los `.h5` de antes | RF-9 |
| `report/info.py` | Los ajustes usados, los incrementos, las particiones, el factor alcanzado de una fase no convergida | H2, RF-3 |
| `gui/dialogs/solver_settings.py` (nuevo), `gui/main_window.py`, `gui/i18n/` | Análisis → Ajustes del cálculo; los textos con su traducción | D9, reglas 2 y 3 |
| `gui/compute_window.py` | «Escalón i de n, iteración k de máx., residuo»; el registro por iteración; Cancelar dentro de la fase | RF-10 |

## Decisiones de diseño

- **Los incrementos (D2, D11, D12).** `StageResult.increments` ya guarda (factor inicial, final,
  texto). Pasa a un registro con el estado codificado (`converged`, `floor`, `cut`), el motivo de la
  partición (iteraciones agotadas o punto que no se actualiza, con el elemento y el punto) y las
  iteraciones. `NotConvergedError` gana `reached` (el último factor convergido de la fase, entre 0 y
  1) y `smallest` (el incremento más pequeño probado). Con eso la 009 sabe hasta dónde llegó cada
  factor de prueba.
- **La lista de factores (RF-6).** `Stage.factors`, si se da, es la lista creciente de factores de
  carga de la fase, de (0, 1], que termina en 1 (dSN §5.4.1); `steps` es entonces su longitud. Si no
  se da, `steps` iguales. Nada más: ni progresiones ni reglas sin fuente (D3).
- **El progreso y la cancelación (D10).** `progress(evento)` con (escalón, de cuántos, iteración,
  residuo relativo, factor inicial y final, partición); se llama después de cada iteración, y no
  decide nada (bit a bit con y sin él, como la T6 de la 006). `should_stop()`, entre dos
  iteraciones; si dice que sí, `solve_stage` lanza `Cancelled` y `analysis.stages` deja de producir
  fases. El trabajo en subproceso escribe el progreso con el mecanismo de `ogr_core.progress`, como
  mucho cada 100 ms, para no escribir el archivo en cada iteración.
- **STR-05 en el motor (D6).** `tests/_footing.py` construye el `EngineModel` con la malla de
  `_strip.py`: medio modelo 0 ≤ x ≤ W, −D ≤ y ≤ 0, u = 0 en x = 0 y en x = W, u = v = 0 en y = −D.
  Variante (a): v impuesto en los nudos de la superficie con 0 ≤ x ≤ b, u libre (lisa), en fases de
  asiento creciente; la presión media de cada fase es −Σ R_y / b. Variante (b): carga repartida
  normal sobre 0 ≤ x ≤ b, una fase por nivel. El asiento en el eje, el del nudo (0, 0).
- **Los estudios, antes de medir (D1, D3, D7).** El `esperado.json` del caso 008 lleva, además de
  la tolerancia, el **protocolo** de cada estudio (qué se barre, qué se compara, con qué umbral y qué
  se elige), en el mismo commit y antes de la primera medida. El resultado de cada estudio va al
  changelog con sus tablas; lo que elige se escribe en el caso o en el motor en el commit siguiente.
- **Los valores por defecto (RF-1).** Los de `engine/model.py`, `Stage`, que hoy no tienen fuente,
  se cambian por los del estudio. Los casos 001 a 004 dan sus ajustes explícitos; los 005 a 007 son
  elásticos: el número no se mueve (una iteración con cualquier tolerancia), y se comprueba bit a
  bit.
- **Los ajustes en el modelo (D9).** `SolverSettings(tolerance, max_iterations, steps, factors,
  max_cuts)`, con los valores por defecto del motor; uno por modelo, el mismo para todas las fases.
  `format_version` 2; un archivo de la versión 1 se lee con los valores por defecto y se guarda como
  2. La huella del modelo los incluye: cambiar un ajuste deja los resultados obsoletos, como debe
  (mueven el número).
- **La interfaz.** Un diálogo pequeño en Análisis, con cada campo y su unidad, el valor por defecto a
  la vista y la nota «en elástico no cambia el resultado» (la guía de interfaz, §8 y §12). La ventana
  de cálculo ya tiene la línea del escalón: pasa a decir escalón, iteración y residuo mientras la
  fase corre.

## Formulación

| Qué | Fuente | Dónde | Estado |
|---|---|---|---|
| Criterio de convergencia en fuerza | dSN (2008), ec. (4.77), §4.2.4; Box 4.2 (x) | pág. 98 (PDF 123); pág. 100 (PDF 125) | **Leído** (spec 001); el denominador, el de la v0.0.1 |
| Escalones con los factores como dato | dSN, §5.4.1 | pág. 120 (PDF 145) | **Leído** |
| Partición automática del incremento | dSN, §5.4.3 y fig. 5.2 | págs. 121–124 (PDF 146–149) | **Leído** (spec 001) |
| Carga de colapso con carga impuesta | dSN, §7.5.3 (y §7.5.1, §7.5.2, §8.4.2) | pág. 251 (PDF 276) | **Leído**; «suficientemente pequeño» sin definir (D2) |
| Carga de Prandtl, (2 + π) c | Prandtl (1921) y Hill (1950), en dSN ec. (7.178), §7.5.4 | págs. 252–255 (PDF 277–280) | **Leído** en dSN; el original, por conseguir |
| La zapata de Tresca rígida y lisa con el asiento impuesto | dSN, §8.4.3 | págs. 346–349 (PDF 371–374) | **Leído**: el montaje, no su número (5.19 es su malla) |
| Retorno de Tresca; Mohr-Coulomb con φ = ψ = 0 | dSN, §8.1 (boxes del retorno) y Remark 8.2 | Remark 8.2, pág. 300 (PDF 325) | Remark **leída**; las boxes de §8.1, **al programar la T2** |
| Más escalones con ψ = 0 y mallas densas | Clausen (2007), apéndice B, §6.1 | págs. 150–151 (PDF 164–165) | **Leído** |
| Búsqueda lineal | Crisfield (1991) | — | **No está**: no entra sin ella (D5) |

**Convenio**: el del motor, tracción positiva; la presión de la zapata y el asiento se dan positivos
hacia abajo solo en el caso y en el changelog, convertidos en un único sitio (`tests/_footing.py`).

## Anomalías que se vigilan (regla 6)

- **Que el T6 se bloquee con el flujo incompresible de Tresca**: la curva no hace meseta o la hace
  muy por encima de (2 + π) c. La v0.0.1 ya vio una firma de bloqueo en el anillo. Si pasa, es un
  hallazgo con su medida, y se propone qué hacer (con Sloan y Randolph 1982 leído); no se afloja la
  tolerancia ni se cambia el caso.
- Que el estudio de D1 no encuentre ninguna tolerancia que cumpla (i): la carga a 1.05 (2 + π) c
  converge con todas, o la de 0.95 no converge con ninguna. Se reporta antes de elegir nada.
- Que cambiar los valores por defecto mueva un caso de 001 a 007: no debe (o dan los suyos, o son
  elásticos).
- Que el progreso o la cancelación muevan un número: bit a bit con y sin ellos.
- Que la partición «converja» por debajo del colapso con incrementos cada vez más pequeños sin
  terminar: `max_cuts` cuenta en toda la fase, así que termina; se vigila el tiempo.

## Estrategia de pruebas

| Parte | Test | Invariante |
|---|---|---|
| A | Tresca: Mohr-Coulomb con φ = ψ = 0 igual al retorno de §8.1 a 1e-12 en el plano y en las aristas; corte simple hasta τ = c; ningún estado pide el vértice; Rust igual a Python | RF-12 |
| A | El bucle: bit a bit con y sin `progress`; `should_stop` para entre iteraciones; los incrementos dicen su estado; el factor alcanzado de una fase que no converge; la marca del suelo | RF-3, RF-4, RF-10 |
| A | Lista de factores: la misma solución elástica que con escalones iguales; en Mohr-Coulomb mueve el número; una lista mal formada se rechaza con su motivo | RF-6, regla 7 |
| A | Cada ajuste mueve el número en STR-05 (malla gruesa): tolerancia, iteraciones máximas, escalones, factores, particiones | RF-11 |
| A | Caso 008 (a): la meseta dentro del 2 % de (2 + π) c, el error bajando con la malla | D6 |
| A | Caso 008 (b): las fases a 0.4–0.95 (2 + π) c convergen; la de 1.05 no, y dice hasta dónde llegó | RF-2, D2 |
| A | Identidades: una fase elástica en una iteración con cualquier tolerancia; elástico igual con 1, 5 y 20 escalones; una fase de descarga en una iteración; Σ reacciones + Σ cargas = 0 | identidades |
| A | Caso 002 con 16 × 64 y anillo de 16 × 48, ψ = 0°: convergen con los valores por defecto (o el test documenta el hallazgo, y se salta con su motivo) | RF-8 |
| A | Casos 001 a 007: bit a bit | regresión |
| B | El archivo: la versión 1 se lee con los valores por defecto; la 2 guarda y lee los ajustes; la huella cambia con cada ajuste | D9 |
| B | La operación: argumento desconocido o inválido, error con su nombre; un paso de deshacer; el ajuste llega al `Stage` del motor y al `.h5` | D9 |
| B | El `.h5`: los incrementos de cada fase, iguales a los del motor; un `.h5` de la v0.0.15 se sigue leyendo | D11 |
| B | El informe y la interpretación: los ajustes usados, las particiones y el factor alcanzado | H2, regla 12 |
| B | La interfaz: el diálogo lee del modelo y aplica por su operación; cada campo con su traducción; en un menú; la ventana de cálculo dice escalón, iteración y residuo y cancela dentro de la fase sin congelarse | reglas 2, 3; RF-10 |

Cada test lleva su cabecera (qué invariante protege) y tiene dientes: una mutación sistemática por
invariante (`{etiqueta: (archivo, texto, sustituto)}`), anotada en `tasks.md`.

## Riesgos

| Riesgo | Cómo se detecta o se acota |
|---|---|
| Bloqueo del T6 con Tresca (arriba) | La curva de la variante (a) con tres mallas; si no hay meseta, hallazgo antes de seguir |
| El tiempo de STR-05 con mallas finas en la referencia de Python | Los estudios con la variante de Rust (la de por defecto); la identidad con la referencia, en la malla gruesa. Se mide y se anota |
| La partición no basta para RF-8 y Crisfield no está | RF-8 queda como hallazgo con su diagnóstico (D5); la búsqueda lineal, a una spec con la fuente |
| La zapata flexible no tiene la misma carga límite que la rígida | La variante (b) se juzga con la banda de ±5 %, no con la meseta; Hill o Prandtl lo dirán (Fuentes) |
| El progreso por iteración inunda el archivo del trabajo | Se escribe como mucho cada 100 ms; un test mide que la ventana no se para |
