# Tareas — Spec 007, tolerancia, colapso y escalones

Pequeñas y verificables, ordenadas por dependencia. Al terminar cada una:
- este archivo y el changelog de su parte, al día;
- la suite entera en verde (`QT_QPA_PLATFORM=offscreen .venv/Scripts/python tests/_runner.py`);
- el commit directo en `main`, sin push hasta que la propietaria lo pida.

Cada test lleva su cabecera y tiene dientes: mutaciones sistemáticas
(`{etiqueta: (archivo, texto, sustituto)}`), anotadas aquí. Las tareas de interfaz cierran además
con la lista por componente de `spec/constitution/guia-de-interfaz.md`.

## Antes de programar

- [x] T0. **Spec, plan y tareas aprobados**, con D1–D14. Va en un commit propio. A la propietaria,
  las fuentes que faltan: Crisfield (1991), Hill (1950) o Prandtl (1921), Sloan y Randolph (1982).

  *Hecho cuando:* la propietaria ha dado el OK y las decisiones están anotadas como aprobadas en
  `spec.md` y `plan.md`. (Hecho el 2026-11-28: OK de la propietaria a D1–D14; las fuentes, pedidas,
  sin respuesta todavía: no bloquean la parte A.)

## Parte A — v0.0.16: el motor y STR-05

- [x] T1. **v0.0.16**, Tresca en un punto de Gauss (RF-12, D14). Empieza `CHANGELOG_v0.0.16.md`.
  Las boxes del retorno de Tresca de dSN §8.1, leídas y anotadas en el plan («Formulación»).

  *Hecho cuando:* Mohr-Coulomb con φ = ψ = 0 coincide con el retorno de Tresca escrito en el test a
  1e-12 en el plano y en las dos aristas; el corte simple en deformación plana llega a τ = c y se
  queda; ningún estado aleatorio pide el vértice; Rust da lo mismo que Python.
  (Hecho el 2026-11-28: a la primera, sin cambiar el motor; también la tangente frente a la derivada
  numérica. 5 tests; 10 mutaciones, 9 cazadas y 1 equivalente con φ = 0.)
- [x] T2. **El diagnóstico de la robustez** (D5, 1; regla 6), en
  `comprobaciones/diagnostico_robustez.py`: el caso 002 con 16 × 64 y el anillo con 16 × 48, ψ = 0°.

  *Hecho cuando:* el changelog dice, para cada uno, en qué incremento falla, por qué (puntos que
  piden el vértice, regiones que oscilan, con cuántos puntos), y qué pasa con 10, 20 y 40 escalones
  y con 4, 8 y 16 particiones; y la propietaria lo sabe antes de la T9. No cambia ningún código.
  (Hecho el 2026-11-28: ninguna de las 32 combinaciones converge; es una barrera de nivel de carga
  (0.86–0.90 en el 002, 0.96 en el anillo), con Newton que oscila y correcciones de hasta 0.65 m.
  Es de ψ = 0: con ψ = 5° los dos convergen sin particiones. **Anomalía**: una tangente singular
  (ψ = 1°) se escapa como `RuntimeError`, sin partir; corrección propuesta para la T3. RF-8,
  propuesto como hallazgo hasta tener Crisfield (1991).)
- [x] T3. `solver.py` y `analysis.py`: el progreso y la cancelación por iteración (D10); los
  incrementos con su estado y el factor alcanzado (D2); la marca del suelo de redondeo (D12); **una
  tangente singular cuenta como incremento que falla** (la anomalía de la T2, con el OK de la
  propietaria del 2026-11-28).

  *Hecho cuando:* bit a bit con y sin `progress` en los casos 001 a 007; `should_stop` para entre
  dos iteraciones y no deja fase a medias; una fase que no converge dice `reached` y `smallest`;
  un incremento que converge por el suelo queda marcado (con el caso de la v0.0.2); la tangente
  singular del 002 con ψ = 1° se parte y, agotadas las particiones, es una no convergencia con su
  motivo, y `calculate` la trata como una fase que falla.
  (Hecho el 2026-11-28: bit a bit con el `solver.py` anterior en el 002 y en los anillos; los
  incrementos son `Increment`, y `test_solver_v001` se adaptó al formato. 9 tests; 13 mutaciones,
  13 cazadas.)
- [x] T4. La lista de factores de carga (RF-6) y **el tamaño automático de Crisfield (1991), ec.
  (9.40)** (D3 modificada) en `Stage` y en `solve_stage`.

  *Hecho cuando:* en elástico, la misma solución que los escalones iguales; en Mohr-Coulomb mueve el
  número (regla 7); una lista que no crece, que no termina en 1 o vacía se rechaza con su motivo; el
  tamaño automático sigue (9.40) con sus límites (un test con las iteraciones conocidas de cada
  incremento) y cada parámetro mueve el número.
  (Hecho el 2026-11-28: la ec. (9.40) leída sobre la página («I_d ≃ 3»); el mínimo acota la regla,
  no las particiones. 7 tests; 15 mutaciones, 15 cazadas tras reforzar 3 que sobrevivían.)
- [ ] T5. **El caso 008 escrito antes de medir** (D6, D7), en un commit propio: `caso.md`,
  `esperado.json` con la tolerancia del 2 % y los protocolos de los estudios de dominio, de malla y
  de los valores por defecto (D1, D3); `tests/_footing.py` con las dos variantes.

  *Hecho cuando:* el commit está hecho antes de la primera medida, y el modelo de la malla más
  gruesa se resuelve en sus dos variantes con la referencia y con Rust, iguales a 1e-12.
- [ ] T6. **Los estudios de dominio y de malla** de la variante (a) (D7).

  *Hecho cuando:* la curva carga–asiento de tres mallas anidadas y de dos dominios está en el
  changelog; la malla y el dominio del caso son los primeros que cumplen el protocolo; la meseta
  está dentro del 2 %. Si no hay meseta o no cumple, es un hallazgo (plan, «Anomalías»): se para y
  se reporta.
- [ ] T7. **El estudio de los valores por defecto** (D1, D3): tolerancia, escalones, iteraciones
  máximas y particiones, con el protocolo de la T5. Los valores elegidos, en `engine/model.py` y en
  `docs/motor/convergencia.md`.

  *Hecho cuando:* las tablas del barrido están en el changelog; los valores salen del protocolo sin
  retocarlo; los casos 001 a 007 siguen bit a bit; cada ajuste tiene su test que mueve el número en
  STR-05 (RF-11).
- [ ] T8. **La variante (b) y las identidades** (RF-2, D2).

  *Hecho cuando:* con los valores por defecto, las fases a 0.4, 0.8, 0.9 y 0.95 (2 + π) c convergen y
  la de 1.05 no, y dice hasta qué factor llegó; las identidades de la tabla (una iteración en
  elástico, independencia de escalones en elástico, descarga en una iteración, equilibrio de
  reacciones) en verde.
- [ ] T9. **La robustez** (RF-8, D5), con lo que dijo la T2: la búsqueda lineal de Crisfield (1991),
  §9.2, medida A/B.

  *Hecho cuando:* el caso 002 con 16 × 64 y el anillo con 16 × 48, ψ = 0°, convergen con los valores
  por defecto y cumplen su tolerancia; o el hallazgo está en el changelog con el diagnóstico, y la
  propietaria decide (la búsqueda lineal, con Crisfield, o otra spec).
- [ ] T10. **Cierre de la parte A**: el coste A/B del bucle nuevo frente al de la v0.0.15, en el
  mismo proceso; la ficha STR-05 con su «Seguimiento»; `CHANGELOG_v0.0.16.md` con lo encontrado.

  *Hecho cuando:* todo lo de la parte A está en verde y los casos 001 a 008 dentro de su tolerancia.

## Parte B — v0.0.17: el modelo, las operaciones y la interfaz

- [ ] T11. **v0.0.17**, los ajustes del cálculo en el modelo (D9): `SolverSettings`, el archivo
  versión 2 (que lee la 1), la edición pura, la traducción y `deciding_values` desde el modelo.

  *Hecho cuando:* un archivo de la v0.0.15 se abre con los valores por defecto; la huella cambia con
  cada ajuste; cada ajuste llega al `Stage` del motor; deshacer lo devuelve.
- [ ] T12. La operación de los ajustes (con el nombre de Slip2D si hace lo mismo), en la línea de
  órdenes y en el servidor MCP; el catálogo al día.

  *Hecho cuando:* un argumento desconocido o inválido da su error con su nombre; las herramientas
  siguen siendo exactamente el catálogo.
- [ ] T13. El `.h5` con los incrementos (D11), el progreso por iteración y la cancelación dentro de
  la fase en `calculate` y en el trabajo (D10), y el informe (H2).

  *Hecho cuando:* los incrementos del `.h5` son los del motor; un `.h5` de la v0.0.15 se sigue
  leyendo; cancelar dentro de una fase deja `cancelled` con las fases anteriores; el informe dice los
  ajustes, las particiones y el factor alcanzado de una fase no convergida; `StageOutcome.increments`
  vuelve a entrar en la comparación (`compare=True`, lo dejó fuera la T3).
- [ ] T14. La interfaz: Análisis → Ajustes del cálculo; la ventana de cálculo con escalón, iteración
  y residuo, el registro por iteración y Cancelar dentro de la fase.

  *Hecho cuando:* pasan los censos (todo texto por `tr()` y traducido; toda acción en un menú); el
  diálogo lee del modelo y aplica por su operación; la ventana no se para más de 0.25 s con el
  progreso por iteración.
- [ ] T15. **El cierre de la spec**: el barrido de las reglas 7 y 12 sobre lo nuevo; los casos 001 a
  008; `CHANGELOG_v0.0.17.md`; la hoja de ruta al día.

  *Hecho cuando:* todos los criterios de finalización de `spec.md` están marcados.
