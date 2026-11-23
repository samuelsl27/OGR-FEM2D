# Spec 025 — Roca diaclasada (juntas ubicuas)

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
      - Aquí: lo que dejen la 008 (Mohr-Coulomb y Hoek-Brown generalizado de la matriz, contrato de
        ley), la 015 (los criterios de junta discreta: Coulomb con residual, Barton-Bandis,
        hiperbólico) y la 005 (factor de resistencia, T05).
      - Núcleo: `materials/builtin_models.py` tiene como envolventes de equilibrio límite
        `BartonBandis` e `Hyperbolic` (resistencia frente a tensión normal, sin rigidez ni flujo) y
        los anisótropos `AnisotropicLinear` (que cita a Mercer 2012 y 2013),
        `SnowdenModifiedAnisotropicLinear`, `GeneralizedAnisotropic` y
        `AnisotropicStrengthFunction`; `geometry/anisotropic_surface.py` orienta la estratificación
        punto a punto (regla del punto más cercano); `materials/parameter_calculator.py` da mb, s y a
        de la matriz de Hoek-Brown. Si la envolvente de un plano se comparte con ellos, es genérico.
      - Lo observado: el árbol de menús de interpretación (carpeta A del análisis de interfaz,
        `interpret/00_arbol_menus_interpret.md`, menú *Data*); en la carpeta B,
        `compute_interpret/I02` §4 (el postproceso de juntas ubicuas) y `modelo/M12c` §4 (el
        material con juntas: inclinación, traza desde 3D). Teoría en `C_teoria/T07a` §9 y `T07c` §5.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 008 (la matriz: Mohr-Coulomb y Hoek-Brown generalizado con residual, dilatancia y tracción;
  el contrato de ley) y 007 (convergencia con varias superficies activas).
- Spec 015 (los criterios de los planos, para no tener dos implementaciones de la misma envolvente)
  y 022 (el banco de ensayos; la convención del ángulo de los ejes del material, su duda 3).
- Specs `005-resultados` (factor de resistencia, magnitudes por punto) y `006-interfaz-y-calculo`
  (menús de interpretación), para el postproceso; 009, si los planos se reducen en el SSR.

## Contexto y objetivo

Un macizo con familias de discontinuidades muy próximas no se puede mallar junta a junta. El
modelo de **roca diaclasada** del catálogo (T07a §9) las «difumina»: en cada punto, una matriz
(elástica, Mohr-Coulomb o Hoek-Brown generalizado) y hasta tres familias de planos de debilidad, cada
uno con su criterio (Coulomb, Barton-Bandis o hiperbólico), pico y residual, dilatancia y tracción.
Las fuentes que cita son Zienkiewicz y Pande (1977) y Azami, Yacoub y Curran (2012). T07c §5 lo
generaliza a muchas familias con criterios anisótropos de equilibrio límite.

Aparte está el pendiente de S06 «*Define Ubiquitous Joints*»: en la interpretación, un **postproceso**
que, con las tensiones ya calculadas, da el factor de resistencia frente al deslizamiento en planos
de orientación dada, sin cambiar tensiones ni desplazamientos. Las specs 005 y 006 lo dejaron fuera
sin destino; se recoge aquí porque comparte con la ley la envolvente del plano.

**`VER-STR-06` no es de esta spec**: su ficha es una sola junta discreta (`JUNTA`) y la 015 lo
retiene (su duda 9). Su solución analítica, la de un plano de debilidad (Jaeger y Cook 1979), es la
referencia natural de esta ley con una familia, y se usa aquí como identidad sin quitarle el caso a
la 015. **Ningún caso del índice pide la roca diaclasada** (no hay código de función para ella):
esta spec solo tiene identidades y fuentes (duda 1).

## Usuarios / actores

- **El ingeniero de rocas**, en taludes y túneles en macizos estratificados o con familias densas.
- **La interpretación** (006), que ofrece el postproceso; **el investigador**, que compara la junta
  difuminada con la discreta de la 015.

## Historias de usuario

- H1: Como ingeniero quiero dar a un material una o varias familias de planos con su inclinación y su
  criterio, y ver dónde rompe la matriz y dónde desliza o se abre cada familia.
- H2: Como ingeniero quiero, después de calcular, comprobar la seguridad frente a deslizamiento en
  planos de una orientación dada, sin repetir el cálculo.
- H3: Como investigador quiero saber que la ley con una familia da la resistencia del plano de
  debilidad de la fuente para cualquier inclinación.

## Requisitos funcionales (EARS)

**Ley de roca diaclasada**

- RF-1: EL SISTEMA integra una matriz de la 008 y una o varias familias de planos difuminados (duda
  3), cada una con su inclinación, su criterio de corte (Coulomb, Barton-Bandis, hiperbólico) con
  pico y residual, su dilatancia y su tracción; la plastificación en un plano cambia tensiones y
  desplazamientos.
- RF-2: EL SISTEMA usa para cada plano la misma envolvente que la junta discreta de la 015, con el
  mismo convenio de signo y la misma comprobación de parámetros.
- RF-3: EL SISTEMA guarda por punto el mecanismo activo (matriz, corte o tracción de cada familia) y
  el deslizamiento acumulado de cada familia, y los da como resultado (005).
- RF-4: CUANDO los planos son mucho más resistentes que la matriz, EL SISTEMA da la ley de la matriz
  de la 008 a redondeo; CUANDO la familia es una sola, la resistencia en compresión simple y triaxial
  frente a la inclinación es la del plano de debilidad de la fuente (identidades con dientes).
- RF-5: EL SISTEMA define la inclinación con un único convenio en todo el programa (el de la 022) y,
  si se decide, la obtiene de una orientación en 3D o de la superficie anisótropa del núcleo (duda 6).

**Postproceso de juntas ubicuas (pendiente de S06)**

- RF-6: CUANDO el usuario define hasta tres familias de planos con su orientación y su criterio
  (Mohr-Coulomb o Barton-Bandis), EL SISTEMA da en cada punto el factor de resistencia frente al
  deslizamiento sobre ellas, el menor de las familias y, si se pide, el menor entre juntas y roca,
  sin tocar los resultados calculados.
- RF-7: SI la tensión normal sobre el plano es de tracción, ENTONCES EL SISTEMA da lo que se decida
  (duda 8) y lo dice en la leyenda; no un número que parezca un factor.
- RF-8: La acción está en el menú de interpretación (regla 3), todo texto pasa por `tr()` (regla 2) y
  los planos definidos se guardan con el modelo y se dibujan donde se decida.

**Reglas transversales**

- RF-9: La ley tiene su referencia en Python, su tangente (o la que permita la fuente con varias
  superficies), su prueba en un punto de Gauss contra la fuente (regla 8), su identidad con Rust
  (ADR-0001) y un test de signo (regla 10: T07a §9.2 escribe los planos con tracción positiva y
  Barton-Bandis con un logaritmo de la tensión normal cambiada de signo).
- RF-10: EL SISTEMA deja que el SSR reduzca o no la matriz y cada familia, y el resultado dice qué se
  redujo (009; para las juntas discretas la referencia no las reduce por defecto, P21).
- RF-11: Cada opción (número de familias, criterio, residual, dilatancia, tracción, reducción en el
  SSR) lleva su test que mueve el número (regla 7).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| Compresión simple con una familia, barrido de la inclinación | Jaeger y Cook (1979), plano de debilidad; Jaeger, Cook y Zimmerman (2007), §3.5 | Resistencia frente a inclinación: deslizamiento por el plano o rotura de la matriz |
| Lo mismo con confinamiento | Jaeger, Cook y Zimmerman (2007), §3.5 | Tensión de rotura frente a inclinación para varios confinamientos |
| Dos familias perpendiculares | La misma teoría aplicada a cada familia (comprobación del catálogo, T07a §9.6) | El mínimo por las dos familias |
| `VER-STR-06` con la ley difuminada | Jaeger y Cook (1979), como en la 015 | Identidad con su solución analítica; frente a la junta discreta de la 015, comparación interna |
| Planos muy resistentes | Identidad (RF-4) | Igual a la matriz de la 008 |
| Plano Barton-Bandis en un punto | Barton y Choubey (1977); Bandis, Lumsden y Barton (1983) | Envolvente y dilatancia frente a la fuente |
| Postproceso de juntas ubicuas | La misma teoría del plano de debilidad, en un estado de tensión uniforme | Factor sobre el plano frente al calculado a mano desde las tensiones |
| Ensayo en un punto y con un elemento | Identidad (spec 022, RF-10) | Las mismas curvas |
| Regla 7 | — | Cada opción de RF-11 mueve el número |

Ningún caso del índice cierra esta spec. Los de juntas con SSR que hablan de «estratificación»
(`VER-JNT-09`, `-10`, `-15`) la modelan con juntas discretas: son de la 015.

## Fuentes por conseguir

- Zienkiewicz y Pande (1977), *Int. J. Numer. Anal. Meth. Geomech.* 1(3), 219–247: el modelo
  multilaminar (es dependiente del tiempo; por comprobar si sirve para un cálculo estático).
- Azami, Yacoub y Curran (2012), 65.ª Conferencia Geotécnica Canadiense: lo que hace el modelo.
- Bandis, Lumsden y Barton (1983); Barton y Choubey (1977); Barton (1973, 1976), incompletas (T00
  §5.B); Hoek (1983); Hoek y Brown (1980b). La envolvente hiperbólica de los planos no tiene fuente en
  T07a §9; T07c §4 cita para una hiperbólica a Esterhuizen, Filz y Duncan (2001): por comprobar si
  es la misma.
- T07c §5: los memorandos en que se basa no son citables (T00 §5.C); el núcleo cita a Mercer (2012,
  2013) para el anisótropo lineal: por comprobar si basta para llevarlo a elementos finitos.
- El algoritmo de retorno con hasta siete mecanismos activos: ninguno de los manuales lo describe.
- Disponibles en `../Referencias/Bibliografia/`: Jaeger, Cook y Zimmerman (2007), §3.5 (un plano de
  debilidad), §4.9 (rocas anisótropas) y cap. 12 (rigidez equivalente de un macizo con familias de
  fracturas); de Souza Neto, Perić y Owen (2008), cap. 8 (retorno con varias superficies en
  Mohr-Coulomb), y la tesis de Clausen (2007), como contraste del retorno.

## Requisitos no funcionales

- El motor recibe la orientación de cada familia ya en su sistema y los parámetros por punto o por
  material (regla 11); con varias familias la integración no debe disparar el tiempo (A/B, 011).

## Casos límite

- Plano paralelo o perpendicular a la carga; familias casi paralelas; inclinación de ±90° y fuera de
  −90…90°.
- Activación simultánea de la matriz y de varias familias; esquina corte–tracción en un plano.
- Barton-Bandis con tensión normal nula o de tracción (logaritmo sin definir); residual igual a pico.
- Postproceso sobre un material sin resistencia definida, o en un punto con tensión hidrostática.

## Fuera de alcance

- La junta discreta, las redes de juntas y `VER-STR-06`, `-26`, `-27` (015).
- La rigidez propia de los planos (el modelo del catálogo solo tiene resistencia, duda 4).
- Los modelos anisótropos de equilibrio límite de T07c §5 como leyes de elementos finitos, salvo lo
  que decida la duda 3; la presión de agua en los planos.

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria; el pendiente de S06, cerrado
- [ ] Todos los RF con su test en verde, y la regla 7 en cada opción nueva
- [ ] La ley probada en un punto contra el plano de debilidad, con identidad Python–Rust
- [ ] Las identidades de la tabla, en verde y con dientes, con la tolerancia fijada antes de medir
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. ¿Se abre sin caso?** El plan pone la roca diaclasada en la fase 5 y su
  único caso con ese nombre (`VER-STR-06`) es una junta discreta. Opciones: (a) abrirla con las
  identidades de la tabla; (b) solo el postproceso de juntas ubicuas; (c) esperar a que un caso la
  pida.
- [NECESITA ACLARACIÓN] **2. `VER-STR-06`** (spec 015, duda 9): se propone dejarlo en la 015 y usar su
  solución aquí como identidad.
- [NECESITA ACLARACIÓN] **3. Número de familias y T07c §5**: hasta tres (T07a §9) o tantas como se
  quiera (T07c §5); los criterios anisótropos de T07c §5 (lineal, el modificado, el generalizado por
  rangos de ángulo) sin fuente citable salvo la de Mercer que cita el núcleo. ¿Aquí, en otra spec o
  fuera?
- [NECESITA ACLARACIÓN] **4. Rigidez de los planos**: solo resistencia, como el catálogo, o también
  la rigidez equivalente de Jaeger, Cook y Zimmerman (2007), cap. 12, con la elasticidad anisótropa
  de la 022.
- [NECESITA ACLARACIÓN] **5. Algoritmo**: el de Zienkiewicz y Pande (1977) es viscoplástico; las
  alternativas son un retorno implícito con varias superficies (de Souza Neto et al. 2008, cap. 8) o
  por mecanismos sucesivos. El orden de comprobación no está documentado (T07a §9.4).
- [NECESITA ACLARACIÓN] **6. Orientación**: el convenio observado (−90° a 90° desde el eje x,
  antihorario) o el de la 022; traza a partir del buzamiento y su dirección; orientación variable
  con la superficie anisótropa del núcleo.
- [NECESITA ACLARACIÓN] **7. Barton-Bandis** (T07a §9.8): base del logaritmo, signo de τ y la errata
  «JCR»; una sola implementación con la 015 y, si es genérica, con el núcleo.
- [NECESITA ACLARACIÓN] **8. Postproceso**: con tracción normal la documentación da factor nulo;
  ¿nulo, «sin dato» o un indicador aparte? «Juntas y roca» combina con el factor de resistencia de
  T05, que no tiene fuente científica (spec 005, duda 4). ¿Vive aquí, en la 005 o en la 016?
- [NECESITA ACLARACIÓN] **9. SSR**: qué se reduce por defecto (matriz, planos o los dos) y cómo se
  dice con el resultado (regla 12; spec 009).
- [NECESITA ACLARACIÓN] **10. Residual en los planos**: cuándo cae (tras la primera plastificación del
  plano, con desplazamiento) — la misma pregunta que la 008 para el frágil-plástico.

Las referencias de la carpeta A y la B son del análisis de interfaz
(`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/`); T00, T07a y T07c, de la carpeta C
(`C_teoria/`); S06, de la carpeta D (`D_sintesis/`); P21, de la carpeta A (`reproducciones/`).
