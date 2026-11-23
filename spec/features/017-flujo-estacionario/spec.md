# Spec 017 — Flujo FEM estacionario

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 4 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 017 — Flujo FEM estacionario»). Solo el
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
      - `ogr_core/fem/seepage.py`: `SeepageSolver` (saturado y lineal, triángulos de 3 nudos,
        tensor de permeabilidad por material, Dirichlet por eliminación, solver disperso, problema
        singular avisado); `UnsaturatedSeepageSolver` (k(ψ) por Picard con subrelajación y un
        rescate; **cara de rezume** por conmutación nodal, con bandas de histéresis y un tope de
        conmutaciones por nudo, `DEFAULT_MAX_NODE_SWITCHES`; la superficie libre es la isolínea de
        presión nula, `free_surface_points`); `flux_through_segment` (sección de descarga
        **recta**); `default_boundary_conditions` y `solve_project_seepage`, atados al `Project`
        y a la malla del núcleo.
      - `ogr_core/fem/seepage_data.py`: `BCType` (altura total, altura de presión, presión nula,
        caudal nodal, infiltración normal por segmento, desconocida), `NodeBC` y `SegmentBC` con la
        bandera `seepage_face` (falsa por defecto), `SeepageResult`, `element_fluxes`.
      - `ogr_core/fem/mesh.py` (malla propia, solo T3: «T6 can be added later»), `fem/generator.py`
        (la malla de filtración de Slip2D), `fem/bc_targets.py` (perímetro mojado de un embalse por
        cota y lado), `fem/streamlines.py` (líneas de corriente exactas en T3).
      - `ogr_core/hydraulic/hydraulic_properties.py` y `permeability_models.py`: Ks, K2/K1 y
        ángulo; modelos k(ψ), con el constante por defecto y el *Simple*, que el propio núcleo
        declara convención de OGR sin fuente publicada (v0.1.267, D190).
      - **Lo que no tiene, visto**: axisimetría (no aparece en el flujo); T6; infiltración vertical;
        presión intersticial impuesta; altura total que varía linealmente a lo largo de un contorno
        (la spec 005 de Slip2D la dejó fuera); sección de descarga poligonal (P17).
      - Evidencia del solver (cuenta como evidencia del solver, no de su uso aquí): en Slip2D,
        `tests/test_seepage_v126.py` (flujo 1D confinado exacto, campo lineal exacto con tensor
        anisótropo y girado, capas en serie y en paralelo, balance de masa) y
        `tests/test_streamlines_v1332.py` (flujo de punto de remanso); en OGR-Core,
        `tests/test_unsaturated_v127.py` (caudal de Charnyi en un dique rectangular al afilar
        k(ψ)), `test_picard_steep_curve_v1266.py` (presa 2 del problema 9, Bowles 1984),
        `test_rescue_face_v1356.py` y `test_face_bands_v1284.py`. El `validacion/casos/` de Slip2D
        no tiene ningún caso de filtración.
      - Aquí: `ogr_fem2d/mesh/` (mallador propio sobre `ogr_core.fem.refine`, T3 o T6, con salida
        propia, que no es un `ogr_core.fem.Mesh`), `docs/malla/entrada.md`, `docs/motor/entrada.md`.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 003 (malla) y `004-modelo-y-proyecto` (condiciones por segmento, vértice o nudo; fases;
  propiedades hidráulicas por material; ajustes con sus defectos a la vista).
- Spec `010-presiones-hidrostaticas`: tensión efectiva por punto de integración, agua embalsada como
  carga, convenio de la presión intersticial. Esta spec cambia el origen de la presión, no su uso.
- Specs 008 y 009: leyes en tensiones efectivas y SSR con presiones fijas (009, RF-7).
- Specs `005-resultados` y `006-interfaz-y-calculo`: magnitudes del flujo, menú *Agua*, cálculo en
  subproceso.
- Spec 002: la axisimetría del motor tensional (el flujo no la tiene; duda 2).
- Spec 018, en parte: la superficie libre del núcleo necesita una función k(ψ) (duda 4).

## Contexto y objetivo

El núcleo ya resuelve el flujo estacionario por elementos finitos, validado en Slip2D, y lo usa
para dar presiones a las rebanadas. Aquí hace falta llevarlo al modelo FEM: condiciones de contorno
sobre la geometría y por fase, el flujo sobre la malla que corresponda, sus resultados (alturas,
caudales, secciones de descarga, líneas de flujo) y, sobre todo, sus presiones en el análisis
tensional y en el SSR. Lo piden `CC-H` (55 casos), `FLU-EST` (39), `CC-REZ` (29), `POST-Q` (19),
`PP-ACOP` (15, de ellos 12 de SSR), `PERM-ANISO` (3) y `PERM-VAR` (3). El plan cierra la fase con
GW-03, GW-04 y GW-15; los tres son de flujo puro.

## Usuarios / actores

- **Ingeniero de presas, taludes y excavaciones** con agua en movimiento.
- **El análisis tensional y el SSR** (009), que reciben las presiones del flujo.
- **OGR Slip2D**, que usa el mismo solver a través del núcleo y no debe notar ningún cambio.

## Historias de usuario

- H1: Como ingeniero quiero imponer alturas, presión nula, caudales y caras de rezume sobre los
  contornos dibujados, y que sobrevivan a un nuevo mallado.
- H2: Como ingeniero quiero ver alturas, presiones, gradientes y velocidades, la línea freática, el
  caudal por una sección y las líneas de flujo, para comprobar la red de flujo.
- H3: Como ingeniero quiero calcular un talud o una presa con las presiones del flujo, en tensiones
  efectivas y en el SSR, para no dibujar a mano un nivel freático que el flujo ya conoce.
- H4: Como ingeniero quiero saber con el resultado qué hizo cada condición desconocida y cada
  casilla de cara de rezume, porque en la referencia una de ellas anuló un bombeo (P18).

## Requisitos funcionales (EARS)

**Flujo**

- RF-1: EL SISTEMA resuelve el flujo estacionario con el solver del núcleo, sin copiarlo, con
  permeabilidad isótropa o anisótropa (K2/K1 y ángulo) por material.
- RF-2: EL SISTEMA admite altura total, altura de presión, presión nula, caudal nodal, infiltración
  por segmento y condición desconocida (rezume), por segmento, vértice o nudo y por fase; un
  contorno sin condición es impermeable, y eso se dice con el resultado (regla 12).
- RF-3: SI ninguna condición fija la altura, ENTONCES EL SISTEMA no calcula y lo dice (problema
  singular).
- RF-4: EL SISTEMA documenta qué hace la cara de rezume sobre una condición de caudal o de
  infiltración, y su valor por defecto se muestra con el resultado (regla 12; duda 3, S06 duda 11).
- RF-5: EN axisimetría, EL SISTEMA resuelve el flujo axisimétrico y dice si los caudales son por
  radián o totales (P17).
- RF-6: SI el flujo no converge (rezume, superficie libre, k(ψ)), ENTONCES EL SISTEMA lo dice con
  sus iteraciones, su tolerancia y los nudos sin asentar, y no pasa sus presiones al análisis
  tensional sin ese aviso.

**Resultados**

- RF-7: EL SISTEMA da altura total, altura de presión, presión intersticial, gradiente, velocidad de
  descarga y permeabilidad por elemento, la línea de presión nula y los nudos que acabaron como
  cara de rezume.
- RF-8: EL SISTEMA integra el caudal a través de una sección de descarga y da el balance de masa
  entre entradas y salidas del modelo.
- RF-9: EL SISTEMA traza líneas de flujo desde un punto o desde varios.

**Presiones del flujo en el análisis tensional**

- RF-10: CUANDO un material toma su presión del flujo, EL SISTEMA la lleva a cada punto de
  integración de la malla tensional (duda 1), con el convenio de signos único y la conversión en un
  único sitio, el mismo de la 010 (regla 10).
- RF-11: EL SISTEMA formula de un solo modo la acción del agua sobre el esqueleto en presencia de
  flujo, con fuente (duda 7), y comprueba con una identidad que no cuenta dos veces el peso del agua.
- RF-12: MIENTRAS dura un SSR, EL SISTEMA mantiene fijas las presiones del flujo (009, RF-7).
- RF-13: SI una altura total impuesta sobre el terreno y el agua embalsada de la 010 no describen el
  mismo nivel, ENTONCES EL SISTEMA lo avisa (en la referencia son independientes, M24 §20).
- RF-14: El flujo recibe nudos, elementos, propiedades y condiciones por nudo y lado; el motor
  tensional, presiones por punto. Ninguno sabe de contornos ni de menús (regla 11).

**Reglas transversales**

- RF-15: Cada opción nueva (tolerancia, iteraciones, relajación, tope de conmutaciones, cara de
  rezume, peso específico del agua, modelo k(ψ) por defecto) lleva su test que mueve el número
  (regla 7) y su valor a la vista con el resultado (regla 12); su texto pasa por `tr()` y su
  acción está en el menú *Agua* (reglas 2 y 3).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-GW-03`, flujo confinado bajo una presa | Rushton y Redshaw (1979) | Altura total en la horizontal 1-1 y en la vertical 2-2 (duda 6: las curvas pueden ser numéricas y solo se leen en una figura) |
| `VER-GW-15`, pozo en acuífero confinado, axisimétrico | Davis y DeWiest (1966) | Altura frente al radio; caudal en una sección igual al bombeo |
| `VER-GW-04`, presa con dren de pie, superficie libre | Parábola de Kozeny, en Harr (1990) y Raudkivi y Callander (1976) | x1 e y1 del dren (duda 5: referencia aproximada y fórmula del manual con errata) |
| `VER-GW-16`, pozo en acuífero libre, axisimétrico | Davis y DeWiest (1966), Dupuit | Freática frente al radio, lejos del pozo (duda 3) |
| `VER-GW-12` y `-13`, zanjas sobre capa drenante | Vedernikov (1934), en Harr (1990) | Caudal y anchura de la zona de filtración |
| `VER-GW-02`, flujo alrededor de un cilindro | Streeter (1948) | Altura total en puntos del dominio |
| `VER-GW-01`, flujo libre con recarga | Harr (1990) | Posición y cota del punto más alto de la freática |
| `VER-SLP-36` (= `-110`), `-37`, `-40`, `-114`, SSR con flujo | Duncan y Wright (2005), factores de equilibrio límite publicados | Factor crítico; el de Slip2D en el mismo modelo es una comparación independiente, no una validación |
| Flujo 1D confinado y campo lineal con tensor anisótropo | Identidad (Darcy) | Alturas y velocidades exactas a redondeo, también en axisimetría con el campo que la fuente dé por exacto |
| Dique rectangular sobre base impermeable | Charnyi, como en el núcleo (por comprobar) | El caudal tiende al de la fórmula al afilar k(ψ) |
| Flujo sin gradiente frente a nivel freático | Identidad | Mismas presiones por punto y mismo factor que con el nivel horizontal de la 010 |
| Columna con flujo vertical | Identidad de equilibrio (fuente de la duda 7) | Tensiones efectivas iguales con las dos formas de escribir la acción del agua |
| Regla 7 | — | Cada opción de RF-15 mueve el número |

Se proponen como los que la cierran **GW-03 y GW-15** (del plan), **SLP-36** para las presiones en
el SSR, y GW-04 según la duda 5. Cada caso fija su malla y su elemento con su estudio (regla 9).
GW-05, GW-09 y GW-11 solo tienen otro programa como referencia: serían comparaciones.

## Fuentes por conseguir

- `Referencias/Bibliografia` no tiene ninguna fuente de agua (`00_LEEME.md`, 2026-11-22).
- Las de la tabla: Rushton y Redshaw (1979); Davis y DeWiest (1966); Harr (1990) (las fichas de
  GW-01 y GW-04 escriben «Haar»); Raudkivi y Callander (1976) (la ficha escribe «Raukivi»);
  Vedernikov (1934); Streeter (1948); Duncan y Wright (2005); la de Charnyi que cite el núcleo.
- La formulación: Fredlund y Rahardjo (1993), que T11 §1 cita sin año; la conmutación nodal de la
  cara de rezume, Neuman (1973) y Bathe y Khoshgoftaar (1979), que cita el núcleo.
- La acción del agua sobre el esqueleto con flujo (duda 7): sin fuente localizada; el principio de
  tensión efectiva se trata en la 010.

## Requisitos no funcionales

- El flujo se calcula una vez por fase, no en cada factor del SSR ni en cada iteración tensional.
- Unidades: el núcleo trabaja en metros, kPa y m/s, con el peso del agua de sus ajustes; el modelo
  FEM puede ir en MPa. La conversión, en un único sitio.
- Slip2D sigue bit a bit: lo que se pida al núcleo no cambia su `generate_mesh` ni su solver.

## Casos límite

- Ninguna condición de altura; todo impermeable; dos condiciones en un nudo; un embalse por encima
  de la coronación; una cara de rezume que no se asienta (nudos congelados por el tope).
- Anisotropía extrema; material sin propiedades hidráulicas (el núcleo lo avisa); nudo sobre el eje.
- Región excavada en una fase (spec 012); punto de integración fuera de la malla de flujo.

## Fuera de alcance

- Retención, almacenamiento, transitorio, condiciones en el tiempo y tensión efectiva no saturada
  (spec 018); no drenado y consolidación (spec 019).
- Drenes y pozos: `DREN` solo lo pide VER-XFM-13 (XFEM, fase 7) y `POZO`, ningún caso.
- Juntas permeables (`JUNTA-HID`, ningún caso); flujo con cuadriláteros (spec 021).
- Permeabilidad función de la deformación (EJ-SEE-02, sin referencia).

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Todos los RF con su test en verde, y la regla 7 en cada opción nueva
- [ ] Los casos que la cierran dentro de tolerancia, con su malla y su elemento fijados
- [ ] El solver usado desde el núcleo; lo pedido a OGR-Core, en una versión etiquetada y fijada aquí
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. La malla del flujo y la tensional.** El flujo del núcleo usa su propia
  malla de T3; la tensional es la de la 003, que puede ser T6. Opciones: (a) una sola malla: el
  flujo sobre los vértices de los T6, o sobre cada T6 partido en cuatro T3, o con T6 pedido al
  núcleo; (b) dos mallas y la presión interpolada a los puntos de integración (el núcleo tiene
  `Mesh.locate` e `interpolate`); (c) otra. Cada una cambia la precisión de `PP-ACOP` y lo que fija
  un caso (regla 9).
- [NECESITA ACLARACIÓN] **2. Axisimetría y T6 en el flujo.** GW-15 y GW-16 son axisimétricos y sus
  fichas usan T6. Son genéricos, pero solo los usaría este programa: (a) pedirlos a OGR-Core; (b)
  escribirlos aquí, que contradice «aquí no se rodea»; (c) casos propios con T3 y su estudio.
- [NECESITA ACLARACIÓN] **3. S06, duda 11 (P18).** En la referencia, con la casilla de cara de
  rezume marcada (su defecto) sobre una infiltración negativa, toda la pared del pozo quedó a
  presión nula y el bombeo no se impuso; sin ella, Dupuit a ±1 % lejos del pozo. Su ayuda dice que
  la altura calculada no puede superar la cota del nudo (M24 §13). El núcleo trata un nudo con la
  bandera como desconocido (`solve_unsaturated`, `_switch_seepage_face`) y la deja falsa por
  defecto. Opciones: (a) el defecto del núcleo, mostrado; (b) el de la referencia; (c) sin defecto,
  que el usuario elija. Antes, averiguar la regla exacta de la referencia.
- [NECESITA ACLARACIÓN] **4. Superficie libre y k(ψ): la frontera con la 018.** En el núcleo la
  superficie libre sale de un flujo saturado y no saturado; con k(ψ) constante la zona de encima
  conduce entera (lo que mide su test de Charnyi). GW-04, GW-16 y GW-01 la necesitan, y sus fichas
  no dan la función. Opciones: (a) traer aquí los modelos k(ψ) del núcleo, solo para la superficie
  libre; (b) mover esos casos a la 018; (c) cerrar la superficie libre con una identidad que no
  dependa de k(ψ). En todo caso, qué modelo por defecto: el núcleo usa el constante; la referencia,
  *Simple* (P08), que el núcleo reproduce con números propios sin fuente.
- [NECESITA ACLARACIÓN] **5. GW-04 como caso de cierre.** La referencia es aproximada (parábola de
  Kozeny con el punto a 0.3 L de la ficha); la fórmula impresa en el manual da 1.85 m y no los
  0.484 m de su tabla (errata probable, según la ficha); el programa de referencia queda un 18 % por
  debajo en y1; k(ψ) no está documentada. Opciones: (a) mantenerlo, con la tolerancia fijada antes
  de medir; (b) dejarlo como comparación; (c) sustituirlo por GW-12 y GW-13 y la identidad de
  Charnyi.
- [NECESITA ACLARACIÓN] **6. Tipo de referencia de GW-03.** La ficha la da por analítica, pero el
  manual no dice si las curvas son de una red de flujo o de un cálculo numérico, y solo se leen en
  una figura. ¿`analitica` o `publicada`, y con qué tolerancia?
- [NECESITA ACLARACIÓN] **7. La acción del agua sobre el esqueleto con flujo**: peso total y presión,
  o peso sumergido y fuerzas de filtración. Tienen que dar lo mismo; falta la fuente que lo diga
  para elementos finitos y la decisión de cuál se programa.
- [NECESITA ACLARACIÓN] **8. Convenio de la presión intersticial** (regla 10; S06 duda 14): el núcleo
  da la presión positiva en compresión y el motor trabaja en tracción positiva. Lo decide la 010
  para las hidrostáticas; esta spec tiene que usar la misma conversión, no otra.
- [NECESITA ACLARACIÓN] **9. Valores por defecto del solver.** Los del núcleo (tolerancia 1e-4, 200
  iteraciones, relajación 0.5, 25 conmutaciones) y los observados en la referencia (1e-6 y 500,
  P08) son distintos. ¿Cuáles, cómo se justifican y dónde se muestran? Y las condiciones que el
  núcleo no tiene (antes de abrirla): ¿se piden solo si un caso las exige? No se vio ninguno.
- [NECESITA ACLARACIÓN] **10. Flujo y fases**: ¿se recalcula en cada fase?, ¿qué hace una región
  excavada o un material que cambia (EJ-SEE-02, -04)?, ¿«solo esta fase», como la referencia?
- [NECESITA ACLARACIÓN] **11. Dónde se guardan la malla y el resultado del flujo.** El `Project` del
  núcleo los guarda dentro del `.ogr` (`fem_mesh`, `seepage_result`); ADR-0003 manda los resultados
  al `.h5`. Se cruza con la duda 4 de la 004.
- [NECESITA ACLARACIÓN] **12. Permeabilidad variable en el espacio** (`PERM-VAR`, EJ-SEE-03 y -04):
  solo tiene otro programa o ninguna referencia. ¿Entra con una identidad (un campo por capas igual
  a materiales por capas) o queda fuera?

Las referencias P08, P17 y P18 son de la carpeta A del análisis de interfaz
(`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/`, `reproducciones/`); M24, de la
carpeta B (`modelo/M24_agua_subterranea.md`).
