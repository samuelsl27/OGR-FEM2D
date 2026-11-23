# Spec 012 — Fases de construcción completas

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 3 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 012 — Fases de construcción completas»). Solo
> el **qué** y el **porqué**, sin fórmulas ni decisiones tomadas. **Antes de abrirla hay que
> reevaluarla** (sección siguiente); después, plan y tareas con el OK de la propietaria.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador (núcleo v0.2.6):
      - Aquí: `docs/motor/entrada.md` y `ogr_fem2d/engine/analysis.py`. `Stage.active` por fase;
        un elemento que vuelve a activarse se rechaza (spec 002, T9); `element_material` es uno
        para todo el cálculo; los nudos sin elementos salen del sistema (`removed_nodes`); cargas
        y desplazamientos impuestos ya llegan en totales (spec 001, D2).
      - Spec `004-modelo-y-proyecto`: RF-3 (la fase como dimensión del modelo, factor por fase),
        RF-4 (rechaza reactivar y cambiar de material «hasta la 012») y su duda 11 (qué hereda
        una fase y si un cambio vale solo para ella: la referencia propaga a las siguientes, P20).
      - El núcleo no tiene fases de construcción: solo las de filtración transitoria
        (`ogr_core/fem/seepage.py`, `TransientStage`), que no sirven para esto.
      - Lo observado: carpeta A del análisis de interfaz, `reproducciones/P20` (fases, cambio de material,
        revestimiento diferido, reparto de la tensión de campo), `P19` (columna *Free* de los
        desplazamientos por fase), `P13`; `dialogos/D08` §6 (diálogo de reparto, opciones por
        material), `D03` (propiedades y carga inicial por material), `D04` §3 y `D05` §2
        (instalación y retirada de soportes).
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 002: la excavación por desactivación (Zienkiewicz y Taylor 2000, ec. 2.13b) y las fases en
  totales. Esta spec levanta sus dos límites: reactivar y cambiar de material.
- Spec `004-modelo-y-proyecto`: la fase en el modelo y el contorno de fase; spec 007: escalones y
  fases de carga; spec 008: leyes con estado (lo que se conserva al cambiar de material).
- Las specs 013 a 016 usan el mecanismo de instalación y retirada que se define aquí.

## Contexto y objetivo

El motor ya excava: quita elementos y aplica la carga que dejan. Una obra real también rellena,
vuelve a rellenar lo excavado, mejora el terreno o pone hormigón que cambia de rigidez, relaja la
tensión de campo antes de sostener (el frente de un túnel en 2D) y coloca y retira soportes fase a
fase. Esta spec completa la secuencia constructiva en el motor y en el modelo, sin la interfaz: lo
que activa y desactiva cada fase, el material de cada región en cada fase, el reparto de la tensión
de campo entre fases y el momento en que entra y sale cada elemento estructural.

## Usuarios / actores

- **El ingeniero** que modela un túnel por fases, un relleno por tongadas o una excavación al
  abrigo de una pantalla; **el modelo** (004), que traduce fases a datos discretos; **las specs de
  soporte** (013–016), que heredan la instalación por fase; **los casos de validación**.

## Historias de usuario

- H1: Como ingeniero quiero rellenar por tongadas una región, para seguir la construcción de un
  terraplén o el relleno de una zanja.
- H2: Como ingeniero quiero relajar una parte de la tensión de campo antes de colocar el
  revestimiento, para representar en 2D el avance del frente.
- H3: Como ingeniero quiero cambiar el material de una región en una fase (tratamiento, hormigón),
  para no dibujar dos modelos.
- H4: Como ingeniero quiero cambiar la fase de instalación o de retirada de un soporte sin borrarlo
  (en la referencia no se puede, P20).
- H5: Como ingeniero quiero soltar en una fase una condición que puse en otra, y ver por fase qué
  cambia y con qué factores.

## Requisitos funcionales (EARS)

**Activación y material**

- RF-1: EL SISTEMA activa en una fase elementos que no estaban activos (relleno), y CUANDO lo hace
  fija su tensión y el desplazamiento de referencia de sus nudos según lo que se decida (dudas 1
  y 2), y lo dice con el resultado (regla 12).
- RF-2: EL SISTEMA reactiva elementos excavados en una fase anterior, con el mismo material o con
  otro.
- RF-3: EL SISTEMA admite un material por elemento **y por fase**; CUANDO el material cambia,
  conserva o no el estado del punto de integración según la duda 3, y SI el estado no es admisible
  para la ley nueva, ENTONCES actúa como se decida en esa duda y lo informa.
- RF-4: EL SISTEMA admite propiedades por fase de un material (duda 5), cada una con el test que
  demuestra que mueve el número (regla 7).

**Tensión de campo, condiciones y cargas**

- RF-5: EL SISTEMA reparte la tensión de campo entre fases con un factor por fase (duda 4); SI los
  factores no cumplen la regla que se fije (suma, signo), ENTONCES lo rechaza o avisa; el reparto
  usado se escribe con el resultado (regla 12).
- RF-6: EL SISTEMA da a cada condición y carga un valor por fase, como total o como factor sobre
  una magnitud, y permite **liberar** en una fase una condición de otra; el motor sigue recibiendo
  totales y calcula él el incremento (spec 001, D2; S06, duda 12, ya fijada).

**Instalación y retirada**

- RF-7: EL SISTEMA da a todo objeto que se instala (soporte, junta, interfaz, carga, condición) una
  fase de instalación y, si la admite, una de retirada, que se pueden editar sin borrar el objeto;
  SI la retirada es anterior a la instalación o el objeto queda sobre una región excavada, ENTONCES
  error que nombra el objeto y la fase.
- RF-8: CUANDO se retira un elemento cargado, EL SISTEMA devuelve su esfuerzo al terreno como hace
  con la excavación, y lo dice en el resultado.

**Comprobación y motor**

- RF-9: SI una fase deja una parte del modelo sin sujetar o un nudo sin elementos con carga,
  ENTONCES el error nombra la fase y la región, no solo el nudo (spec 002, RF-2).
- RF-10: EL SISTEMA da un resumen por fase de lo que cambia: regiones activadas y desactivadas,
  materiales, factores, objetos instalados y retirados.
- RF-11: EL SISTEMA ofrece todo lo anterior en la referencia en Python y en Rust, con la identidad
  entre las dos (ADR-0001); el motor sigue sin saber de regiones (regla 11).

## Validación numérica

Ningún caso del índice pide de forma explícita relleno, reactivación ni propiedades por fase: con
lo leído, esta spec se valida sobre todo con identidades, y con la variante de STR-07 cuando exista
el revestimiento (013).

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| Variante de `VER-STR-07` con relajación (P20) | Einstein y Schwartz (1979), como el caso | Con terreno y revestimiento elásticos, mitad de la tensión sin sostener y mitad con él: esfuerzos del revestimiento, la mitad de los del caso sin relajación. Necesita la 013 |
| Relajación en un hueco sin sostener | Kirsch (1898), en Jaeger, Cook y Zimmerman (2007), §8.4 | Con un factor f en la fase de excavación, desplazamientos f veces los de Kirsch (la referencia da −0.4 %, P20: no es valor esperado) |
| Excavación en una fase o en varias | — (linealidad) | En elástico, el estado final no depende del número de fases |
| Cambio de material sin cambio de carga | — (equilibrio) | Si el estado se conserva, el incremento de desplazamiento es nulo; si no, no: el test tiene dientes |
| Liberar un apoyo | — (superposición) | Soltar una restricción equivale a aplicar la reacción cambiada de signo |
| Retirar un soporte elástico | — (superposición) | Instalar y retirar sin cambiar nada más devuelve el estado sin el soporte |
| Relleno y reactivación | Por diseñar al abrirla (duda 1) | Identidades que distingan las opciones de las dudas 1 y 2 |
| Variantes | — | Referencia en Python y Rust idénticas a redondeo en todo lo anterior |

Casos del índice con fases y excavación que piden además otras specs, y que esta no cierra:
`VER-JNT-21` (juntas y SSR; solo comparación con otro programa), `EJ-EXC-01` (pantalla, puntales y
forjados por fase, no drenado y modelos de la fase 5; referencia de campo), `VER-XFM-16` y
`EJ-SEE-02`.

## Fuentes por conseguir

- Ningún manual de teoría describe las fases de construcción (`C_teoria/T00`, §3.1). Falta fuente
  para el tratamiento de un elemento que entra en una fase (tensión y desplazamiento de partida) y
  para el reparto de la tensión de campo como representación del frente en 2D; las dos, por
  localizar en la literatura de túneles y de elementos finitos.

## Requisitos no funcionales

- El motor recibe por fase datos discretos: elementos activos, material por elemento, factor de la
  tensión de campo, objetos activos (regla 11). Sin dependencias nuevas.
- Mismo modelo, misma entrada del motor bit a bit (spec 004, RF-12). Los mensajes llevan una clave
  traducible (regla 2).

## Casos límite

- Rellenar sobre un terreno ya deformado; nudos que salieron del sistema al excavar y vuelven.
- Cambiar de ley (elástico a Mohr-Coulomb) en una región ya cargada, o en una plastificada.
- Factores de reparto que no suman uno, negativos o todos nulos; reparto con tensión gravitatoria.
- Soporte instalado y retirado en la misma fase; instalado en una fase en que su región está
  excavada; retirado cuando su región ya no existe.
- Fase sin cambios (incremento nulo, spec 002); una fase que solo cambia un factor.

## Fuera de alcance

- Los elementos estructurales y las juntas (013–016); aquí solo su fase de instalación y retirada.
- Agua por fase (niveles, permeabilidad por fase de `EJ-SEE-04`): 010 y fase 4; tiempo y
  consolidación (019); SSR por fase (009); fases dinámicas (fase 7).
- La interfaz de las fases (pestañas, propagación al editar): 006, con la semántica que fije la 004.

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Todos los RF con su test en verde, y la regla 7 en cada ajuste nuevo
- [ ] Las identidades de la tabla, en verde y con dientes; la de P20, cuando exista la 013
- [ ] Referencia y Rust idénticas a redondeo
- [ ] Changelog con lo encontrado; fichas tocadas con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. Desplazamiento de partida de lo que se rellena**: (a) los nudos nuevos
  parten de cero y se informa el desplazamiento desde su activación; (b) heredan el de la
  superficie sobre la que se apoyan; (c) los dos, como magnitudes distintas. Afecta a los
  asientos que se comparan en los casos de terraplén.
- [NECESITA ACLARACIÓN] **2. Tensión de partida de un elemento que se activa**: (a) nula; (b) la de
  la tensión de campo o la gravitatoria; (c) por material, como la «carga inicial» que la
  referencia elige por material (D03). La regla 12 pide que se vea.
- [NECESITA ACLARACIÓN] **3. Cambio de material**: (a) se conservan tensiones y variables internas;
  (b) se conservan las tensiones y se reinician las variables; (c) se parte de cero. Si el estado
  queda fuera de la superficie nueva: retorno en la primera iteración, error o aviso.
- [NECESITA ACLARACIÓN] **4. Qué se reparte**: (a) la tensión de campo, como la referencia (P20:
  «inicializar» en la primera fase y «añadir» en las demás); (b) la carga de excavación de la ec.
  (2.13b). ¿Reparto por material y opciones de fuerzas de masa y tensiones de elemento (D08 §6)?
  ¿Qué hacer si los factores no suman uno?
- [NECESITA ACLARACIÓN] **5. Propiedades por fase**: factores sobre los parámetros (la referencia
  usa factores por fase) o valores; qué parámetros; aquí o en cada spec de ley. Pendiente de S06:
  el diálogo de propiedades por fase con varias fases no se llegó a observar.
- [NECESITA ACLARACIÓN] **6. La instalación de soportes antes de que existan** (el plan la pone aquí
  y la 012 va antes que la 013): (a) mecanismo genérico aquí, probado con regiones y cargas, y cada
  spec de soporte añade su test; (b) pasarla a cada spec de soporte.
- [NECESITA ACLARACIÓN] **7. Retirada automática**: la referencia elimina una junta si se excava uno
  de sus lados (D07) y no permite retirar una interfaz estructural (D04 §6). ¿Qué hace este
  programa con cada objeto cuya región desaparece: error, aviso o retirada?
- [NECESITA ACLARACIÓN] **8. Condiciones y cargas «en totales»** ya son del motor (spec 002): lo que
  queda aquí es el modelo (total o factor por fase, liberar). ¿Esta viñeta del plan sigue siendo
  de la 012 o ya la cubre la 004 (RF-3)?

Las referencias D03, D04, D05, D07 y D08 son de la carpeta A del análisis de interfaz
(`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/`, `dialogos/`); P13, P19 y P20, de
`reproducciones/`.
