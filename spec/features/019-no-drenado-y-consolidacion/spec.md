# Spec 019 — No drenado y consolidación acoplada

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 4 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 019 — No drenado y consolidación acoplada»).
> Solo el **qué** y el **porqué**, sin fórmulas ni decisiones tomadas. **Antes de abrirla hay que
> reevaluarla** (sección siguiente); después, plan y tareas con el OK de la propietaria.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador (núcleo v0.2.6):
      - Aquí, `ogr_fem2d/engine/`: motor de desplazamientos (T3 y T6, deformación plana y
        axisimetría, Mohr-Coulomb con T6 en deformación plana), referencia en Python en
        `engine/reference/solver.py`, entrada en `docs/motor/entrada.md` (fases en totales). **No
        hay** grados de libertad de presión, ni tiempo, ni rigidez del fluido. La spec 002 (RF-11,
        D6) rechaza Mohr-Coulomb en axisimetría y con T3.
      - Núcleo: el flujo transitorio y las propiedades hidráulicas (017 y 018).
        `ogr_core/hydraulic/excess_pore_pressure.py` es el exceso por carga **de equilibrio
        límite** (B̄ de Skempton 1954, modelo vertical sin reparto, según su propio texto):
        otra teoría, no un no drenado de elementos finitos. `hydraulic/drawdown_levels.py` y
        `materials/drawdown_envelopes.py` (desembalse rápido de equilibrio límite), lo mismo.
      - **Lo que no hay en ninguna parte**: consolidación acoplada, no drenado con rigidez del
        fluido, coeficiente de Biot, elemento mixto desplazamiento–presión. Es motor (regla 11,
        ADR-0001): se escribiría aquí, con su oráculo en Python, salvo lo que resulte genérico.
      - Teoría: T09 (consolidación de Biot, tal como la resume el manual); T11 §2 (no drenado en
        tensiones efectivas); T00 §3.3 (erratas: término de peso y bloque de la ec. 12 de T09;
        dimensiones de Ku y Kf en T11 §2).
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 002 (motor) y spec 007 (convergencia y escalones), con el **tiempo** como nueva dimensión.
- Spec 008: leyes en tensiones efectivas; Mohr-Coulomb en axisimetría (CON-04) lo rechaza hoy la 002.
- Spec 012: fases de construcción (CON-03, CON-05, STR-32 encadenan carga y consolidación).
- Specs 017 y 018: permeabilidad, condiciones de presión y de caudal, estado inicial; el
  almacenamiento desacoplado, según su duda 6.
- Specs `010-presiones-hidrostaticas` (convenio de la presión y tensión efectiva),
  `004-modelo-y-proyecto` (drenado o no drenado por material y por fase; tiempo de fase) y
  `005-resultados` (historias en el tiempo y perfiles).

## Contexto y objetivo

Hasta aquí la presión del agua es un dato del análisis tensional: hidrostática (010) o de un flujo
(017, 018). En un suelo poco permeable cargado deprisa la presión la genera la propia deformación
(**no drenado**, `UNDR`, 5 casos), y después se disipa con el tiempo mientras el suelo asienta
(**consolidación acoplada**, `CONS`, 12 casos; 10 de ellos del área de consolidación). Las dos
cosas acoplan el motor tensional con el flujo. El plan cierra la fase con CON-01, la columna
unidimensional de Terzaghi. **CON-01 es de consolidación, no de dinámico**: el orden de desbloqueo
del índice la pone en el paso de `DIN` solo porque exige `C-TIEMPO` (una carga en rampa), que llega
en ese paso; no necesita integración dinámica.

## Usuarios / actores

- **Ingeniero de cimentaciones y terraplenes sobre arcillas**, que necesita asientos en el tiempo y
  el estado no drenado al final de la construcción.
- **El investigador**, que contrasta con soluciones clásicas de consolidación.

## Historias de usuario

- H1: Como ingeniero quiero declarar un material no drenado con parámetros efectivos y obtener el
  exceso de presión que genera una carga rápida.
- H2: Como ingeniero quiero aplicar una carga, dejar consolidar y ver el asiento y la presión frente
  al tiempo, y el grado de consolidación.
- H3: Como ingeniero quiero ver con el resultado cada parámetro del agua y del esquema temporal
  tomado por defecto (Kw, Ks, α, θ, pasos), porque cambian el número.

## Requisitos funcionales (EARS)

**No drenado**

- RF-1: EL SISTEMA admite materiales drenados y no drenados, y en consolidación el estado por fase;
  un material no drenado genera exceso de presión con su deformación volumétrica, con parámetros
  efectivos de rigidez y resistencia.
- RF-2: EL SISTEMA guarda en cada punto de integración la presión total y el exceso, y la tensión
  efectiva y la total, con la conversión de signo en un único sitio (regla 10).
- RF-3: EL SISTEMA no tiene valores ocultos del agua: módulo del fluido, módulo del grano,
  porosidad y coeficiente de Biot (automático, dado o desactivado) se muestran con el resultado
  (regla 12).
- RF-4: SI un material casi incompresible hace que el elemento bloquee, ENTONCES EL SISTEMA lo
  evita con la formulación que se decida con fuente (duda 2) o, si no, lo detecta y lo dice.

**Consolidación acoplada**

- RF-5: EL SISTEMA resuelve el equilibrio y la continuidad del agua acoplados, con desplazamientos
  y presión como incógnitas, por fases con su tiempo.
- RF-6: EL SISTEMA admite contornos drenantes e impermeables, presiones y caudales impuestos (017,
  018), y cargas que varían con el tiempo dentro de una fase (`C-TIEMPO`), que entran al motor en
  totales (spec 001, D2; duda 7).
- RF-7: EL SISTEMA integra en el tiempo con el esquema y el parámetro que se decidan (duda 5), los
  muestra con el resultado y deja que cada caso fije su paso, como fija su malla (regla 9).
- RF-8: EL SISTEMA parte de un estado inicial en equilibrio: tensiones de campo y presiones
  hidrostáticas o de un flujo, con exceso inicial nulo o impuesto.
- RF-9: EL SISTEMA da por instante asientos, exceso de presión, tensiones efectivas y grado de
  consolidación, en historias de puntos y en perfiles (`POST-HIST`, `POST-LINEA`).
- RF-10: CON una ley plástica de la 008, EL SISTEMA consolida en tensiones efectivas (CON-04, -05,
  -06).

**Motor y reglas transversales**

- RF-11: El motor recibe nudos, elementos, propiedades mecánicas e hidráulicas, condiciones de
  desplazamiento y de presión, cargas en totales y tiempos; no sabe de contornos ni de unidades de
  usuario (regla 11).
- RF-12: Cada elemento y cada término nuevo tiene su implementación de referencia en Python, que es
  el oráculo de Rust (ADR-0001), y el no drenado se prueba en un punto de Gauss contra su fuente
  antes de usarse en un modelo (regla 8).
- RF-13: Cada parámetro nuevo (Kw, Ks, α, n, θ, paso de tiempo) lleva su test que mueve el número
  (regla 7); los textos pasan por `tr()` y las acciones están en un menú (reglas 2 y 3).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-CON-01`, columna unidimensional | Terzaghi (1923; reimpreso en 1960, según la ficha) | U frente a Tv (malla uniforme) e isócronas de presión en cinco Tv (malla graduada) |
| `VER-CON-02`, capa entre placas rígidas | Mandel (1953) | Presión y asiento frente al tiempo |
| `VER-CON-03`, faja flexible sobre capa finita | Booker (1974) | Asiento frente a Tv |
| `VER-CON-04`, cilindro grueso, axisimétrico | Yu (1992); Small (1977); Hill (1950) | Presión frente a desplazamiento, drenado y no drenado; colapso no drenado |
| `VER-CON-05`, faja no drenada | Small (1977, tesis; numérica según la ficha); Prandtl (1924) | Curva carga–asiento; carga de colapso |
| `VER-CON-06`, faja con flujo asociado y no asociado | Manoharan y Dasgupta (1995), numérica; Prandtl (1924) | Curvas carga–asiento |
| `VER-CON-10`, experimento de Liakopoulos | Lewis y Schrefler (1998), §5.7 (experimental y numérica) | Presión y saturación en la columna (necesita la 018) |
| `VER-CON-07`, `-08`; `VER-STR-32` | Sin referencia: comparación interna entre enfoques | Acoplado frente a desacoplado; no es validación |
| Ensayo no drenado en un punto | B de Skempton (fuente por comprobar) | Exceso de presión frente a carga isótropa |
| Fin de la consolidación, en elástico | Identidad | Desplazamientos del análisis drenado con la misma carga |
| Carga instantánea | Identidad (por comprobar en la fuente) | Respuesta igual a la del análisis no drenado |
| Regla 7 | — | Cada parámetro de RF-13 mueve el número |

Se proponen como los que la cierran **CON-01** (del plan), **CON-02** y **CON-03** (analíticas), y
CON-05 para el no drenado con plasticidad. El único no drenado con referencia analítica es CON-04,
que pide Mohr-Coulomb en axisimetría.

## Fuentes por conseguir

- Ninguna de consolidación ni de no drenado en `Referencias/Bibliografia`.
- Formulación: Biot (1941), que el plan nombra y **T09 no cita**; Lewis (1998), que T09 da con un
  solo autor, y Lewis y Schrefler (1998), que da la ficha de CON-10 (T00 §5 duda si es la misma
  obra); Zienkiewicz et al. (1990), escrito con erratas en el manual. Las erratas de T00 §3.3 solo
  se resuelven con ellas.
- No drenado: Terzaghi (tensión efectiva, en la 010) y Skempton (B), que T11 §2 nombra sin
  referencia; el núcleo cita Skempton (1954) para otra cosa. Los «elementos especiales» que la
  referencia activa con el no drenado no están descritos (T11 §2.4): hace falta una fuente para el
  elemento mixto o para el tratamiento de la incompresibilidad. Zienkiewicz y Taylor (2000), vol. 1,
  está en la carpeta; no se comprobó si lo trata.
- Las de los casos: Terzaghi (1923), Mandel (1953), Booker (1974), Yu (1992), Small (1977), Hill
  (1950), Prandtl (1924), Manoharan y Dasgupta (1995).

## Requisitos no funcionales

- El sistema acoplado deja de ser simétrico con no saturado (T09); la 011 ya prevé tangentes no
  simétricas (su RF-4).
- Unidades de tiempo y de permeabilidad (conductividad en m/s o permeabilidad intrínseca con la
  viscosidad, T09 §1.3) convertidas en un único sitio.

## Casos límite

- Primer paso de tiempo muy corto frente al tamaño de los elementos (la rampa de CON-01 dura
  Tv = 0.0001).
- Permeabilidad nula (no drenado puro) o muy alta (drenado puro) en el mismo modelo.
- Material no drenado en una fase drenada; contorno drenante en una región excavada.
- Coeficiente de Biot igual a 1, o cercano a la porosidad; ν' cercano a 0.5.
- Carga retirada antes de terminar la consolidación (descarga).

## Fuera de alcance

- Dinámico y licuefacción (`DIN`, `LICUEF`: VER-DYN-18, fase 7); los modelos de suelo avanzados de
  EJ-EXC-01 (fase 5).
- Consolidación no saturada (CON-10, EJ-UNS-01), salvo que la duda 9 la traiga.
- SSR con consolidación acoplada (EJ-UNS-01; la referencia lo ofrece, M24 §20).
- Drenes de mecha (`DREN`, VER-XFM-13, XFEM); fluencia secundaria.

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Todos los RF con su test en verde, y la regla 7 en cada parámetro nuevo
- [ ] El no drenado, probado en un punto contra su fuente (regla 8)
- [ ] Referencia en Python y Rust con su identidad (ADR-0001)
- [ ] Los casos que la cierran dentro de tolerancia, con su malla y su paso fijados
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. CON-01 y `C-TIEMPO`.** El plan no asigna las cargas en el tiempo a
  ninguna spec anterior a la fase 7. Opciones: (a) aquí, limitadas a lo que piden CON-01, -04, -05 y
  -06 (rampa y velocidad de carga); (b) una spec propia antes de esta. La ficha no da q0, el peso del
  agua, la porosidad, los módulos del fluido y del grano ni el ancho de la columna: ¿se fijan como
  datos propios del caso, sabiendo que la referencia está adimensionalizada?
- [NECESITA ACLARACIÓN] **2. El elemento.** Opciones vistas: (a) mixto, con la presión en un orden
  menor que el desplazamiento; (b) el mismo orden con estabilización; (c) para el no drenado sin
  consolidación, sumar la rigidez del fluido a la del esqueleto (la vía de T11 §2), con el riesgo de
  bloqueo. Ninguna sin fuente leída.
- [NECESITA ACLARACIÓN] **3. No drenado sin consolidación** (material no drenado en un análisis
  estático, STR-32) **y no drenado como límite** de una consolidación con carga rápida (CON-04, -05):
  ¿los dos?, ¿con qué identidad entre ellos?
- [NECESITA ACLARACIÓN] **4. Valores por defecto del agua.** La referencia fija Ks en 69 GPa
  (atribuido a «Terzaghi et al.», cita incompleta) y Kw en 2·10⁶ kN/m² (T11 §2); la ficha de STR-32
  da 2.20·10⁶ kPa. ¿Qué defectos, con qué fuente, y cómo se muestran?
- [NECESITA ACLARACIÓN] **5. Esquema temporal**: el manual usa un esquema θ sin dar su valor (T09
  §1.4); ¿cuál, expuesto o fijo, y con qué control del paso (la referencia: automático o fijo)?
- [NECESITA ACLARACIÓN] **6. Erratas de la fuente secundaria** (T00 §3.3): el término de peso de T09
  (escrito con n − 1), los signos de los bloques de su ec. 12 y su término independiente; las
  dimensiones de Ku y la de Kf en T11 §2. Se resuelven leyendo las fuentes, no el manual.
- [NECESITA ACLARACIÓN] **7. S06, duda 12, con tiempo**: las cargas entran en totales al final de la
  fase (spec 001, D2), pero una rampa o una velocidad de carga (CON-01, CON-04) define la carga
  dentro de la fase. ¿Totales en cada instante?
- [NECESITA ACLARACIÓN] **8. Convenio de signos** (regla 10; S06 duda 14): T11 §2.8 escribe la
  tensión efectiva con la presión positiva en compresión sin declararlo. Se usa la conversión que
  fije la 010, no la del manual.
- [NECESITA ACLARACIÓN] **9. Consolidación desacoplada y no saturada.** La desacoplada (CON-07, -08,
  modelos 2a y 3a de STR-32) puede ir en la 018 (su duda 6); la no saturada (CON-10, EJ-UNS-01) hace
  el sistema no simétrico y no lineal (T09). ¿Aquí, o en una spec posterior?
- [NECESITA ACLARACIÓN] **10. Conductividad o permeabilidad intrínseca**: T09 usa la intrínseca con
  la viscosidad; T11 y el núcleo, la conductividad en m/s. ¿Qué pide el usuario y dónde se
  convierte?

Las referencias T00, T09 y T11 son de la carpeta C del análisis de interfaz
(`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/C_teoria/`); M24, de la carpeta B
(`modelo/M24_agua_subterranea.md`).
