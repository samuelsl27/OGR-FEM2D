# Spec 023 — Cam-Clay y Cam-Clay modificado

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 5 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Fase 5 — Modelos constitutivos avanzados»). Solo el
> **qué** y el **porqué**, sin fórmulas ni decisiones tomadas. **Antes de abrirla hay que
> reevaluarla** (sección siguiente); después, plan y tareas con el OK de la propietaria.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador (núcleo v0.2.6):
      - Aquí: `ogr_fem2d/engine/reference/mohr_coulomb.py` (el único retorno con tangente
        consistente) y `engine/initial_stress.py` (tensión inicial por punto, de la que sale el
        estado inicial del casquete); el contrato de ley y el banco de ensayos vendrán de la 008 y la
        022.
      - Núcleo: no hay ninguna ley de estado crítico. Lo único cercano son criterios de equilibrio
        límite (`materials/builtin_models.py`: `SHANSEP`, que usa el OCR como dato, sin regla de
        flujo). La sobreconsolidación en la tensión inicial (correlaciones de K0 con el OCR, T06) es
        de la spec 002 o la 004.
      - Lo observado: la reproducción P14 (carpeta A del análisis de interfaz, `reproducciones/`), con
        el diálogo del material y el hallazgo de N; teoría en `C_teoria/T07b` §1; erratas en `T00`
        §3.3 (signo de la ec. 8.5) y signos en §3.2.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 008: el contrato de ley (variables de estado, tangente, modo de rotura) y su RF-10, porque el
  caso de la fase es axisimétrico; spec 007 (escalones, Newton, control por desplazamiento).
- Spec 022: el banco de ensayos de laboratorio (`ENSAYO-LAB`) y las trayectorias (`POST-TRAY`).
- Spec 002 y `004-modelo-y-proyecto`: la tensión inicial efectiva por punto, obligatoria y no
  trivial para inicializar el casquete; las unidades del proyecto (duda 1).
- Spec 010 (tensiones efectivas) y 019 (no drenado y consolidación) para usar la ley con agua; aquí
  solo se valida drenada.

## Contexto y objetivo

Los modelos de estado crítico describen la arcilla con una superficie de fluencia cuyo tamaño, la
presión de preconsolidación, crece al compactar y decrece al dilatar, y con una rigidez volumétrica
que depende de la tensión y del volumen específico (T07b §1). Cam-Clay modificado (`MCC`) es el
modelo de la fase con más fuente: integración implícita publicada (Borja y Lee 1990; Borja 1991) y
soluciones cerradas del triaxial drenado (Peric 2006). El plan cierra la fase con `VER-STR-13`, su
único caso, y le asigna la **duda 9 de S06**: el programa de referencia y el manual usan volúmenes
específicos distintos con los mismos datos, porque la definición de N no está clara. Es también la
base del casquete de los modelos de suelo blando (026) y comparte la ley de endurecimiento con el
casquete de la 024.

## Usuarios / actores

- **El ingeniero de suelos blandos** (terraplenes, excavaciones en arcilla), que trabaja con λ, κ, M
  y el OCR; **el docente**, para quien el triaxial de Cam-Clay es un ejemplo clásico.
- **Las specs 019 y 026**, que usarán esta ley con agua y como casquete; **los casos de validación**.

## Historias de usuario

- H1: Como ingeniero quiero dar λ, κ, M, el volumen específico de referencia y la preconsolidación
  (o el OCR) y saber sin ambigüedad a qué presión y en qué unidades está definido N.
- H2: Como ingeniero quiero ver en cada punto la presión de preconsolidación, el volumen específico
  y si el suelo está del lado húmedo o del seco.
- H3: Como docente quiero reproducir los tres triaxiales drenados clásicos (normalmente consolidado,
  ligera y fuertemente sobreconsolidado) y compararlos con la solución cerrada.

## Requisitos funcionales (EARS)

**Ley**

- RF-1: EL SISTEMA integra Cam-Clay modificado con su línea de consolidación virgen, sus líneas de
  hinchamiento, la pendiente de estado crítico, endurecimiento y ablandamiento por la deformación
  volumétrica plástica, y rigidez volumétrica función de la tensión media y del volumen específico,
  con el módulo de corte constante o el coeficiente de Poisson constante (uno de los dos).
- RF-2: EL SISTEMA integra Cam-Clay original solo si se decide (duda 3), con la errata de la ec. 8.5
  del catálogo resuelta en la fuente (T00 §3.3).
- RF-3: EL SISTEMA define el volumen específico de referencia con su presión de referencia explícita,
  independiente de las unidades del proyecto, y lo muestra con el resultado (S06, duda 9; regla 12):
  el mismo modelo en kPa y en MPa da lo mismo (identidad de la spec 004).
- RF-4: EL SISTEMA guarda por punto la presión de preconsolidación, el volumen específico y la
  deformación volumétrica plástica, con su estado inicial definido (duda 5), y los da como resultado.

**Estado inicial**

- RF-5: CUANDO un material tiene esta ley, EL SISTEMA exige una tensión inicial efectiva de
  compresión y fija la superficie inicial con la preconsolidación o con el OCR, con la definición de
  OCR escrita junto al resultado.
- RF-6: SI el estado inicial queda fuera de la superficie, ENTONCES EL SISTEMA hace lo que se decida
  (duda 7) y lo dice por material y por número de puntos; no la reajusta en silencio, como hace el
  programa de referencia (T07b §1.4).

**Cada ley y su uso**

- RF-7: La ley tiene su referencia en Python, su tangente (la consistente de la fuente que se elija,
  comprobada contra la derivada numérica), su prueba en un punto de Gauss contra la solución cerrada
  (regla 8), su identidad con Rust del orden de 1e-10 (ADR-0001) y un test de signo con las
  ecuaciones reescritas en tracción positiva (regla 10: el catálogo escribe ln(−p)).
- RF-8: SI la tensión media efectiva de un punto deja de ser de compresión, o el volumen específico
  sale fuera de su dominio, ENTONCES EL SISTEMA lo dice con el elemento y la fase; no sigue con una
  rigidez nula o negativa.
- RF-9: CUANDO un punto plastifica del lado seco, EL SISTEMA lo marca; el resultado avisa de que el
  ablandamiento hace la respuesta dependiente de la malla en un problema de contorno (lo advierte el
  propio manual, T07b §1.1), sin regularizarla en esta spec.
- RF-10: SI se pide reducción de resistencia (009) con esta ley, ENTONCES EL SISTEMA hace lo que se
  decida con fuente (duda 9) o la rechaza con un mensaje; no reduce nada en silencio.
- RF-11: Cada opción (Poisson o módulo de corte constante, preconsolidación u OCR, la dependencia del
  ángulo de Lode si entra) lleva su test que mueve el número (regla 7); los textos pasan por `tr()` y
  las acciones están en un menú.

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-STR-13`, triaxial drenado en MCC (tres ejemplos, G o ν constante, control de carga y de desplazamiento) | Peric (2006), solución cerrada del triaxial drenado | q, εa y εv en cada escalón. **No** contra las tablas «analíticas» del manual: según la reproducción P14 corresponden a un volumen inicial que no sale de sus datos (S06, duda 9). La solución se programa desde el artículo, no desde la ficha (que repite un factor: posible errata) |
| Compresión isótropa y descarga | Definición del modelo en la fuente (Wood 1990; Roscoe y Burland 1968) | El volumen sigue la línea virgen con pendiente λ y la de hinchamiento con κ |
| Estado crítico | Wood (1990) | Con deformación de corte grande, q/p′ tiende a M sin cambio de volumen, en los tres ejemplos |
| Ensayo en un punto y con un elemento | Identidad (spec 022, RF-10) | Las mismas curvas; el ejemplo 3 (ablandamiento) solo con control de desplazamiento |
| Unidades | Identidad (RF-3) | El mismo ensayo en kPa y en MPa da las mismas deformaciones |
| Signo | Regla 10 | Una compresión isótropa endurece; una descarga queda elástica |
| Triaxial no drenado (si la duda 10 lo trae) | La solución cerrada que dé Wood (1990), por comprobar | Trayectoria de tensiones efectivas y exceso de presión |
| Regla 7 | — | Cada opción de RF-11 mueve el número |

Se propone `VER-STR-13` como el caso que la cierra, con la tolerancia fijada antes de medir. La
reproducción P14 mostró que εa cerca de la línea de estado crítico es muy sensible al tamaño del
escalón: el caso tiene que fijar su número de escalones como fija su malla (regla 9).

## Fuentes por conseguir

- Peric (2006), *Int. J. Numer. Anal. Meth. Geomech.*, 30, 363–387 (T00 §5.A): la referencia del caso.
- Borja y Lee (1990), *CMAME* 78(1), 49–72, y Borja (1991), *CMAME* 88, 225–240 (T00 §5.A): la
  integración implícita, con predictor elástico no lineal en el segundo.
- Wood (1990), que cita S06 (duda 9) sin título; por completar la referencia. Roscoe y Burland (1968)
  (T00 §5.A, citado en otro contexto) y Roscoe y Schofield (1963) (T00 §5.B, incompleta), para la
  formulación original de los dos modelos.
- Disponibles en `../Referencias/Bibliografia/`: de Souza Neto, Perić y Owen (2008), §10.1, «A
  modified Cam-Clay model for soils» (modelo e implementación) y §10.2 (Drucker-Prager con casquete,
  útil para la 024); la tesis de Clausen (2007) lo menciona (alcance sin comprobar). Ninguna trae
  Cam-Clay original.

## Requisitos no funcionales

- El motor recibe N con su presión de referencia en las unidades del motor (regla 11); la conversión
  de unidades se hace en un único sitio.
- Una ley con estado por punto (preconsolidación, volumen) no debe hacer más lentas las demás: A/B.

## Casos límite

- Estado inicial justo sobre la superficie (OCR = 1), dentro, fuera; tensión inicial no isótropa.
- κ igual o mayor que λ; M nula; volumen específico inicial menor que uno.
- Tensión media que se acerca a cero (rigidez volumétrica que se anula) o pasa a tracción.
- Escalón que cruza la línea de estado crítico; pico y ablandamiento dentro de un escalón (ejemplo 3).
- Descarga desde el lado seco; recarga hasta volver a tocar la superficie.

## Fuera de alcance

- Consolidación acoplada y no drenado con generación de presión (019), salvo el ensayo a volumen
  constante si la duda 10 lo trae.
- Los modelos de suelo blando y fluencia que usan este casquete (026); el casquete sobre
  Mohr-Coulomb y el de endurecimiento-ablandamiento (024).
- La regularización del ablandamiento (no local, gradiente) y la localización.

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria; la 9 de S06, cerrada con la
      fuente y anotada en S06
- [ ] Todos los RF con su test en verde, y la regla 7 en cada opción nueva
- [ ] La ley probada en un punto de Gauss contra Peric (2006), con identidad Python–Rust
- [ ] `VER-STR-13` dentro de la tolerancia fijada antes de medir, con su malla y sus escalones
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. Definición de N** (S06, duda 9). P14: el programa de referencia coincide
  con una integración propia con el volumen inicial que da N a presión unidad en kPa; las tablas del
  manual solo se reproducen con otro volumen, que no sale de sus datos. Opciones: (a) N a una presión
  de referencia fija y declarada; (b) N a presión unidad del proyecto (rompe la identidad de unidades
  de la 004); (c) pedir el volumen o el índice de poros iniciales y deducir lo demás. Contrastar con
  Peric (2006) y Wood (1990) antes de elegir.
- [NECESITA ACLARACIÓN] **2. Qué se compara en `VER-STR-13`**: la solución de Peric calculada por
  nosotros desde el artículo (propuesta), con los mismos parámetros; las columnas del programa de
  referencia del manual quedan como comparación. En control de carga el manual va un escalón por
  detrás desde la fila 6 del ejemplo 2 (observación de la ficha).
- [NECESITA ACLARACIÓN] **3. Cam-Clay original**: ningún caso lo pide y la ec. 8.5 del catálogo tiene
  un signo que no cuadra (T00 §3.3). ¿Entra con su fuente y un ensayo propio, o se deja fuera?
- [NECESITA ACLARACIÓN] **4. Algoritmo**: Borja y Lee (1990), Borja (1991) o de Souza Neto et al.
  (2008), §10.1; cómo se integra la rigidez no lineal en el escalón (cambia el número con escalones
  grandes, P14).
- [NECESITA ACLARACIÓN] **5. Volumen específico**: cómo se inicializa en cada punto (no documentado,
  T07b §1.3) y si se actualiza con el del escalón anterior, como la ec. 8.8 del catálogo, o con otro
  esquema que dé la fuente.
- [NECESITA ACLARACIÓN] **6. Ángulo de Lode y deformación plana**: Peric (2006) es un modelo de tres
  invariantes; el catálogo no dice si M depende del ángulo de Lode. ¿M constante (superficie de
  revolución), o con la dependencia de la fuente? ¿Cómo se fija M en deformación plana?
- [NECESITA ACLARACIÓN] **7. Estado inicial fuera de la superficie**: (a) rechazarlo; (b) agrandar la
  superficie y decirlo (RF-6); (c) aceptarlo como plastificación inmediata.
- [NECESITA ACLARACIÓN] **8. Signo del endurecimiento y de la deformación volumétrica plástica**
  (T07b §1.8): el catálogo no declara su convenio; se resuelve al reescribir en tracción positiva.
- [NECESITA ACLARACIÓN] **9. Reducción de resistencia con Cam-Clay**: no hay c ni φ que reducir.
  ¿Reducir M, rechazarla, o dejarla hasta que un caso la pida? Ninguno del índice la pide.
- [NECESITA ACLARACIÓN] **10. Ensayo no drenado**: el triaxial a volumen constante es el uso clásico
  de la ley con agua. ¿Aquí, con el banco de la 022 a volumen impuesto, o en la 019?
- [NECESITA ACLARACIÓN] **11. Relación con el casquete de la 024 y el de T07a §5**: los dos comparten
  ley de endurecimiento con MCC y definen λ como una diferencia de pendientes sin el factor del
  volumen (T07a §5.8, T07c §1.8). ¿Una pieza común de casquete, o cada ley la suya?

La referencia P14 es de la carpeta A del análisis de interfaz
(`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/`, `reproducciones/`); T00, T07a y T07b,
de la carpeta C (`C_teoria/`); S06, de la carpeta D (`D_sintesis/`).
