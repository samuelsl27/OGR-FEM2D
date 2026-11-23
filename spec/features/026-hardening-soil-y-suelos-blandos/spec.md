# Spec 026 — Hardening Soil y modelos de suelo blando y fluencia

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 5 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Fase 5 — Modelos constitutivos avanzados»). Solo el
> **qué** y el **porqué**, sin fórmulas ni decisiones tomadas. **Antes de abrirla hay que
> reevaluarla** (sección siguiente); después, plan y tareas con el OK de la propietaria.

> **Aviso.** Para cuatro de los modelos de esta spec (los de T07b §2, §3, §6 y §7: endurecimiento
> por rozamiento movilizado, el mismo con casquete y doble fluencia, suelo blando y suelo blando con
> fluencia) el catálogo **solo cita manuales de programas comerciales** (T00 §3.4 y §5.C). **No
> entran sin la publicación científica original**, leída y comprobada: sin ella no hay fórmula, y
> una fórmula sin fuente no entra (plan de desarrollo, «Cómo se trabaja»).

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador (núcleo v0.2.6):
      - Aquí: lo que dejen la 008 (contrato de ley, Mohr-Coulomb con tracción), la 022 (banco de
        ensayos y rigidez dependiente de la tensión, su duda 7), la 023 (casquete de Cam-Clay, base
        del de suelo blando), la 024 (rozamiento movilizado y casquete) y la 019 (no drenado y
        tiempo, para los ensayos no drenados y los modelos con fluencia).
      - Núcleo: ninguna de estas leyes. Las correlaciones de K0 con el OCR (T06) que fijan el estado
        inicial son de la tensión de campo (002, 004).
      - Lo observado: teoría en `C_teoria/T07b` §2 a §8 y la nota común de su cabecera (estos
        modelos, en el programa de referencia, son reproducciones hechas con su interfaz de modelos
        de usuario); erratas en `T00` §3.3 y fuentes en §3.4 y §5; el diálogo, en la carpeta B
        (`modelo/`, materiales de endurecimiento y de usuario). Ninguno tiene reproducción en la
        carpeta A.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Specs 008, 022, 023 y 024 (arriba); spec 007 (Newton con varias superficies y endurecimiento).
- Spec 019 para el no drenado y para el tiempo físico por fase (fluencia y hinchamiento).
- Para `EJ-EXC-01`, además: 010 (nivel freático), 012 (fases de excavación), 013 (pantalla como
  viga) y 014 (puntales, su duda 6).

## Contexto y objetivo

Los suelos reales tienen rigidez que depende de la tensión y del nivel de deformación, distinta en
carga noval y en descarga, y fluencia en el tiempo. El catálogo trae siete modelos para ello (T07b
§2 a §8): **Hardening Soil** (`SUELO-AV`; doble endurecimiento, de corte y de casquete, con
resistencia de Mohr-Coulomb; Schanz, Vermeer y Bonnier 1999), su versión con **rigidez a pequeñas
deformaciones**, los dos de **endurecimiento por rozamiento movilizado** (sin y con casquete), el de
**suelo blando** (casquete de tipo Cam-Clay modificado y Mohr-Coulomb), el de **suelo blando con
fluencia** (viscoplástico) y el de **roca expansiva** (hinchamiento en el tiempo, con elasticidad
transversalmente isótropa). El plan pide, antes de nada, localizar las publicaciones originales.

Esta spec fija qué entra y con qué fuente. Con lo leído, solo Hardening Soil tiene a la vez fuente
citable y algo con que validarlo (`VER-CNS-01` D4 y D5, ensayos de Hostun de Schanz y Vermeer 1996;
`EJ-EXC-01`, medidas de obra). El resto queda condicionado a sus fuentes y a un caso.

## Usuarios / actores

- **El ingeniero de excavaciones y obras en arcilla blanda y arena**, que trabaja con E50, Eur y Eoed.
- **El investigador**, que necesita la formulación auditable de un modelo que conoce por un manual.
- **Los casos de validación**; **la 019**, con la que se combinan el no drenado y la consolidación.

## Historias de usuario

- H1: Como ingeniero quiero usar Hardening Soil con sus parámetros habituales y ver con el resultado
  cada valor que el programa calibró o tomó por defecto.
- H2: Como ingeniero quiero saber, al elegir un modelo, de qué publicación sale y cuál es su caso de
  validación; y que un modelo sin publicación no se me ofrezca.
- H3: Como investigador quiero reproducir un triaxial y un edométrico de Hardening Soil en un punto
  y compararlos con la fuente.

## Requisitos funcionales (EARS)

**Qué entra**

- RF-1: EL SISTEMA solo ofrece un modelo de esta spec cuando su publicación científica original está
  leída, citada en el código por autor y año, y el modelo tiene su prueba en un punto de Gauss contra
  ella (regla 8); hasta entonces no aparece en ningún menú ni diálogo.
- RF-2: CUANDO el usuario elige un modelo, EL SISTEMA muestra su fuente y su caso de validación, o
  que no tiene caso.

**Hardening Soil**

- RF-3: EL SISTEMA integra Hardening Soil con su endurecimiento de corte y de casquete, su
  resistencia de Mohr-Coulomb, su corte a tracción, su rigidez dependiente de la tensión y su regla
  de dilatancia, según Schanz, Vermeer y Bonnier (1999).
- RF-4: EL SISTEMA no tiene calibraciones ocultas: los parámetros del casquete que se deduzcan de un
  ensayo edométrico simulado, el límite inferior de la tensión media y cualquier otro valor interno
  se calculan de forma reproducible, se guardan con el modelo y se muestran con el resultado
  (regla 12; T07b §4.4 los describe sin documentarlos).
- RF-5: EL SISTEMA fija el estado inicial del casquete con la definición que dé la fuente (OCR u otra)
  a partir de la tensión inicial, y SI el estado inicial queda fuera de alguna superficie, ENTONCES
  lo dice; no lo reajusta en silencio.

**Los demás modelos (según las dudas 2 a 5)**

- RF-6: SI se adopta la rigidez a pequeñas deformaciones, ENTONCES EL SISTEMA guarda por punto la
  historia de deformación que la fuente exija y detecta las inversiones de carga como ella diga.
- RF-7: SI se adopta un modelo con tiempo (fluencia, hinchamiento), ENTONCES EL SISTEMA lo integra
  en el tiempo físico de cada fase (019) y muestra el paso y el esquema con el resultado.

**Cada ley**

- RF-8: Cada ley tiene su referencia en Python, oráculo de Rust con identidad del orden de 1e-10
  (ADR-0001), su tangente, su prueba en un punto de Gauss contra la fuente y un test de signo con las
  ecuaciones reescritas en tracción positiva (regla 10: el catálogo no declara el convenio salvo en
  el de fluencia, en compresión positiva; T07b §4.8 mezcla σ1 y σ3).
- RF-9: Cada opción (regla de dilatancia, corte de dilatancia, límite de tensión, variante) lleva su
  test que mueve el número (regla 7); los textos pasan por `tr()` y las acciones están en un menú.
- RF-10: SI se pide reducción de resistencia (009) con una de estas leyes, ENTONCES EL SISTEMA hace
  lo que se decida con fuente o la rechaza con un mensaje.

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-CNS-01` D4 y D5, Hostun densa y suelta, triaxiales drenados a 300 kPa (de la 024) | Schanz y Vermeer (1996), experimental; los parámetros de Hardening Soil, de Schanz, Vermeer y Bonnier (1999) si los publica para esa arena | q y εv frente a εa. Las curvas que el manual da de otro programa son **comparación**, no referencia |
| Triaxial drenado en un punto | Schanz, Vermeer y Bonnier (1999) | La relación hiperbólica de la fuente hasta la rotura, y su módulo de descarga |
| Edométrico en un punto | Schanz, Vermeer y Bonnier (1999) | La rigidez edométrica de referencia y el K0 normalmente consolidado que la calibración promete (RF-4) |
| `EJ-EXC-01`, excavación profunda en arcilla (enfoque con Hardening Soil) | Ou, Shiau y Wang (2000), medidas de obra; parámetros de Ou, Liao y Cheng (2000) y Lim, Ou y Hsieh (2010) | Deformada de la pantalla y asientos por fase. Referencia **de campo**, débil; faltan parámetros (exponente, presión de referencia, Rf, K0) |
| Ensayo en un punto y con un elemento | Identidad (spec 022, RF-10) | Las mismas curvas |
| Arena de Berlín (T07b §4.6 y §5.6) | Solo otro programa | No se usa: comparación sin datos de confinamiento |
| Regla 7 | — | Cada opción de RF-9 mueve el número |

Los demás modelos no tienen ningún caso en el índice: el catálogo solo los compara con el programa
del que salen (T07b §2.6 a §8.6).

## Fuentes por conseguir

- Schanz, Vermeer y Bonnier (1999), *Beyond 2000 in Computational Geotechnics*, 281–296 (T00 §5.A),
  para Hardening Soil y la base del de pequeñas deformaciones. Rowe (1962), incompleta (T00 §5.B),
  para la regla de dilatancia.
- Pequeñas deformaciones: Benz (2006), Hardin y Drnevich (1972), Masing (1926) y Santos y Correia
  (2001), todas solo con autor y año (T00 §5.B).
- Hinchamiento: Anagnostou (1993), *Rock Mech. Rock Eng.* 26(4), 307–331; Wittke-Gattermann y Wittke
  (2004), *Proc. ITA 2004*; la ley de Grob, sin referencia.
- **Por localizar, sin pista en el catálogo**: la publicación original de los modelos de T07b §2, §3,
  §6 y §7. Hasta tenerla, no entran (aviso de la cabecera).
- `EJ-EXC-01`: Ou, Shiau y Wang (2000); Ou, Liao y Cheng (2000); Lim, Ou y Hsieh (2010).
- Disponibles en `../Referencias/Bibliografia/`: de Souza Neto, Perić y Owen (2008), §10.1
  (Cam-Clay modificado, base del casquete de suelo blando), §10.2 (casquete sobre Drucker-Prager) y
  cap. 11 (viscoplasticidad: marco general y su integración). Ninguna trata Hardening Soil.

## Requisitos no funcionales

- El motor recibe parámetros ya en sus unidades, incluida la presión de referencia (regla 11); un
  parámetro calibrado se calcula una vez por material y se guarda, no en cada punto.
- Un modelo con historia por punto (tensor de memoria, fluencia) no hace más lentos a los demás: A/B.

## Casos límite

- Tensión media que se acerca a cero (rigidez nula; el límite inferior de RF-4).
- Estado inicial fuera del casquete; OCR alto con K0 pequeño; tensión inicial no isótropa.
- Rotura alcanzada dentro de un escalón; esquinas corte–casquete y corte–tracción.
- Descarga y recarga repetidas (pequeñas deformaciones: memoria); paso de tiempo grande frente a la
  viscosidad (fluencia).

## Fuera de alcance

- **El modelo de usuario cargado desde código externo**: T00 §4 propone diseñar la interfaz de
  materiales con su contrato, y la 008 ya lo recoge como contrato común (su RF-8, con la copia para
  el SSR); cargar leyes ajenas en tiempo de ejecución no lo pide ningún caso.
- Cam-Clay (023), el endurecimiento y ablandamiento del catálogo (024), Finn-Martin y la
  licuefacción (fase 7), los modelos citados sin manual (NorSand, superficie límite, T00 §3.1).

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Cada modelo que entre, con su publicación original leída, su prueba en un punto y su identidad
      Python–Rust; los que no, fuera de los menús y anotados en el changelog
- [ ] Todos los RF con su test en verde, y la regla 7 en cada opción nueva
- [ ] Hardening Soil dentro de la tolerancia fijada antes de medir en D4 y D5 de `VER-CNS-01`
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. Qué modelos entran y en qué orden.** Propuesta del borrador: Hardening
  Soil primero (fuente citable y dos casos); los demás, cada uno cuando tenga fuente y caso. ¿Una spec
  por modelo cuando se abran?
- [NECESITA ACLARACIÓN] **2. Los cuatro sin fuente** (aviso de la cabecera): ¿se buscan las
  publicaciones antes de abrir la spec, o se dejan fuera del alcance hasta que aparezcan?
- [NECESITA ACLARACIÓN] **3. Pequeñas deformaciones**: sus fuentes son incompletas; el tamaño del
  tensor de historia en deformación plana no está documentado (T07b §5.8). ¿Entra con Hardening Soil
  o después?
- [NECESITA ACLARACIÓN] **4. Modelos con tiempo** (fluencia, hinchamiento): necesitan tiempo físico
  por fase, que trae la 019. ¿Aquí, o en una spec posterior a la 019?
- [NECESITA ACLARACIÓN] **5. Roca expansiva**: es una ley de roca con elasticidad anisótropa (022) y
  dos formulaciones (sin y con acoplamiento entre direcciones). ¿Aquí, con la 025, o fuera?
- [NECESITA ACLARACIÓN] **6. Calibración del casquete de Hardening Soil**: el programa de referencia
  la hace con un ensayo edométrico interno no documentado (T07b §4.4). ¿Se toma el procedimiento de la
  fuente, se piden los parámetros como dato, o los dos con su test de regla 7?
- [NECESITA ACLARACIÓN] **7. Erratas del catálogo** (T00 §3.3; T07b §4.8): el denominador de sin φcv
  en los de rozamiento movilizado y en Hardening Soil; la ec. 15.10 con 1 − e; el factor de la 15.13;
  la 18.4 del de fluencia; la 19.5 del de hinchamiento. Solo se resuelven con la fuente.
- [NECESITA ACLARACIÓN] **8. `EJ-EXC-01`**: referencia de campo, cuatro modelos y muchas specs
  previas; la tabla de Hardening Soil tiene rótulos ambiguos y le faltan parámetros. ¿Caso de
  validación, comparación cualitativa o solo ejemplo?
- [NECESITA ACLARACIÓN] **9. Ensayos no drenados de Hardening Soil**: el catálogo los muestra
  (T07b §4.6). ¿Con el banco de la 022 a volumen constante o con el no drenado de la 019?
- [NECESITA ACLARACIÓN] **10. Frontera con la 024**: los de rozamiento movilizado comparten mecanismo
  con el endurecimiento y ablandamiento; si aparece su fuente, ¿se implementan allí?

Las referencias T00 y T07b son de la carpeta C del análisis de interfaz
(`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/C_teoria/`); la carpeta B es la de la
documentación de la interfaz del programa de referencia, en el mismo sitio.
