# Spec 011 — Rendimiento del bucle global

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 2 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 011 — Rendimiento del bucle global (P4)»).
> Solo el **qué** y el **porqué**, sin fórmulas ni decisiones tomadas. **Antes de abrirla hay que
> reevaluarla** (sección siguiente); después, plan y tareas con el OK de la propietaria.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador:
      `ogr_fem2d/engine/interface.py` (la frontera: `update(start, du)` una vez por iteración, con
      la rigidez de cada punto en un patrón fijo, `stiffness_pattern`);
      `ogr_fem2d/engine/reference/solver.py` (`solve_stage`: ensamblaje disperso y factorización
      con SuperLU de SciPy en Python); `ogr_fem2d/engine/compiled.py` y `rust/src/lib.rs` (la
      variante Rust); la medida A/B de la spec 001 (tarea T13: conjunto con semilla y controles
      repetidos; `docs/changelog/CHANGELOG_v0.0.1.md`). En el núcleo, ninguno: su solver de
      filtración (`ogr_core/fem/seepage.py`) usa también SciPy y podría beneficiarse de lo que se
      mida aquí, pero eso se pide a OGR-Core, no se toca.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Specs 007 y 009: el bucle que se mide es el de escalones, iteraciones y pruebas del SSR, con su
  criterio ya fijado; medir antes sería medir un bucle que va a cambiar.
- Spec 008: la integración de las leyes nuevas entra en el coste por iteración.
- No depende de la interfaz; la 006 solo muestra el progreso.

## Contexto y objetivo

ADR-0001 fijó la frontera en una llamada por iteración global y dejó el solver lineal en SuperLU de
SciPy, con `faer` «solo tras medirlo». La decisión P4 del plan lo trae a la fase 2 con un dato: en
la malla del caso 002 la factorización en Python (75–94 ms) ya pesa más que la llamada de Rust
(5–9 ms). El SSR multiplica ese coste por el número de pruebas (P05: ocho pruebas de diez escalones,
cada una con sus iteraciones), y la fase 6 lo multiplicará otra vez.

El objetivo es decidir con medidas, no con supuestos: comparar SuperLU con `faer` en el mismo proceso
y con el método de la spec 001, mirar si el paralelismo de la integración compensa, y llevar a Rust
el bucle de escalones e iteraciones solo si la medida lo pide. Ningún cambio de esta spec puede
mover un resultado más allá de la identidad: la referencia en Python sigue siendo el oráculo.

## Usuarios / actores

- **La propietaria**, que decide con las medidas qué solver y qué parte del bucle van a Rust.
- **Ingeniero**, que espera un SSR en minutos y no en horas.
- **Los tests**, que comprueban que el camino rápido da lo mismo que la referencia.

## Historias de usuario

- H1: Como propietaria quiero medidas A/B en el mismo proceso del ensamblaje, la factorización y la
  solución, con SuperLU y con `faer`, en mallas de casos reales, para decidir con números.
- H2: Como ingeniero quiero que un SSR de un talud de la fase 2 termine en un tiempo razonable, sin
  cambiar su factor crítico.
- H3: Como auditora quiero poder repetir cualquier cálculo con la referencia en Python y obtener lo
  mismo, para que el código compilado nunca sea la única verdad (ADR-0001).

## Requisitos funcionales (EARS)

**Medida**

- RF-1: EL SISTEMA mide, con el método A/B en el mismo proceso de la spec 001 y controles repetidos,
  el tiempo del ensamblaje, la factorización, la solución y la integración, por separado, en mallas
  fijadas de casos de la fase 2 (al menos STR-02, STR-05 y un SSR de talud).
- RF-2: Los umbrales que deciden un cambio se fijan **antes** de medir, por la propietaria, como en
  el ADR-0001; si los controles difieren tanto como el efecto, la medida no decide.

**Solver lineal**

- RF-3: CUANDO `faer` supere el umbral fijado y su licencia se haya comprobado (AGPL-3.0), EL SISTEMA
  lo usa como solver; si no, se queda SuperLU y la medida queda anotada.
- RF-4: EL SISTEMA resuelve también la tangente no simétrica (flujo no asociado) con el solver
  elegido, como hace hoy SuperLU (spec 001, D7).

**Paralelismo y bucle**

- RF-5: SI el paralelismo de la integración por puntos (`rayon`) compensa en la medida, ENTONCES EL
  SISTEMA lo usa, con resultados reproducibles entre ejecuciones (o la desviación acotada y
  documentada).
- RF-6: SI la medida lo pide, EL SISTEMA lleva a Rust el bucle de escalones e iteraciones, con la
  misma interfaz hacia Python y la referencia en Python intacta como oráculo.

**Identidad**

- RF-7: Con cualquier combinación nueva, EL SISTEMA da los mismos resultados que la referencia en
  Python dentro de la tolerancia de identidad del ADR-0001, con el mismo número de iteraciones, y
  los casos de validación siguen dentro de su tolerancia sin tocar su `esperado.json`.
- RF-8: La elección de solver y de paralelismo no es un ajuste visible si no cambia el número; si lo
  cambia, se muestra con el resultado (regla 12) y tiene su test (regla 7).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| Identidad entre solvers | — | Desplazamientos, tensiones e iteraciones con SuperLU y con `faer`, en punto material y en malla |
| Identidad entre bucles | — | Bucle en Python y en Rust: mismos escalones, iteraciones, particiones y resultado |
| `validacion/casos/001` y `002` | Kirsch (1898); Salençon (1969) (spec 001) | Siguen dentro de su tolerancia |
| STR-05 (spec 007) y los casos de SSR de la 009 | Los de su spec | Mismo factor crítico y misma tabla de pruebas |

No hay cálculo nuevo que validar: esta spec se cierra con identidades y con los casos ya validados.

## Fuentes por conseguir

- La documentación de `faer` y de `rayon` (licencias y garantías de reproducibilidad), por comprobar.
- Si se cambia el reordenamiento de la matriz, la fuente del método que use cada solver.

## Requisitos no funcionales

- Ruedas en Windows, macOS ARM y Linux, con la CI en verde; el congelado con PyInstaller sigue
  resolviendo los casos.
- Sin dependencias nuevas sin el OK de la propietaria y su licencia comprobada.
- Memoria: la malla más grande de la fase 2 cabe en un equipo normal; medirlo.

## Casos límite

- Matriz singular (restricciones insuficientes o mecanismo): el error llega igual de claro que hoy.
- Tangente no simétrica y mal condicionada cerca del colapso.
- Malla pequeña, donde el coste fijo de la llamada domina y el paralelismo empeora.
- Equipo con carga de fondo (la medida de la spec 001 la tuvo): controles que lo detecten.

## Fuera de alcance

- Cambiar la frontera de una llamada por iteración salvo que la medida lo exija (ADR-0001).
- Solvers iterativos, GPU, PARDISO o MKL (excluidos por licencia, `tech-stack.md`).
- El rendimiento del mallador (spec 003) y del flujo del núcleo.

## Criterios de finalización

- [ ] Medidas A/B anotadas con sus controles y la decisión de la propietaria con ellas delante
- [ ] Identidades en verde y casos de validación dentro de su tolerancia
- [ ] Licencias de las dependencias nuevas comprobadas y aceptadas
- [ ] Ruedas y congelado en las tres plataformas
- [ ] Changelog registrando qué se encontró

## Dudas abiertas

- [NECESITA ACLARACIÓN] **Umbrales**: ¿qué ganancia justifica cambiar de solver o llevar el bucle a
  Rust? El ×10 del ADR-0001 era para la integración constitutiva; aquí puede ser otro.
- [NECESITA ACLARACIÓN] **Mallas de medida**: ¿cuáles fijan la decisión? Las de STR-02 son pequeñas;
  la de un SSR de talud fino o de STR-05 puede invertir el resultado.
- [NECESITA ACLARACIÓN] **Reproducibilidad con paralelismo**: sumar en otro orden cambia el redondeo;
  ¿se exige igualdad al bit entre ejecuciones o una tolerancia?
- [NECESITA ACLARACIÓN] **Reutilizar la factorización** cuando la matriz no cambia (fases elásticas,
  pruebas del SSR que empiezan igual): ¿es un ajuste del motor o una optimización invisible?
- [NECESITA ACLARACIÓN] **Orden**: el plan pone la 011 al final de la fase; si el SSR de la 009 resulta
  inservible en tiempo, ¿se adelanta la medida del solver?
- [NECESITA ACLARACIÓN] **Variante NumPy**: la spec 002 (D4) dejó de mantenerla; ¿se usa en las
  medidas como en la spec 001 o se compara solo Python de referencia con Rust?
