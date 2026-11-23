# Spec 016 — Interfaz estructural, elementos infinitos y resultados de soporte

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 3 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 016 — Interfaz estructural, elementos infinitos
> y resultados de soporte»). Solo el **qué** y el **porqué**, sin fórmulas ni decisiones tomadas.
> **Antes de abrirla hay que reevaluarla** (sección siguiente); después, plan y tareas con el OK de
> la propietaria.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador (núcleo v0.2.6):
      - Núcleo: `ogr_core/result_rows.py` (los números con que se muestra y exporta un resultado,
        en un solo sitio para el panel, el informe, la API y el HDF5; hoy por rebanada y cara) y
        `project/results_io.py` (ADR-0003); `support/support.py`, `PileMicropile` y `Geosynthetic`
        (propiedades de equilibrio límite, no elementos).
      - Slip2D: `ogr_gui/dialogs/support_force_diagram.py` (diagrama a lo largo de un soporte) y
        `ogr_gui/xy_chart.py` (gráfico x-y), base para los gráficos de bulones, revestimientos y
        juntas; la exportación de tablas de su interpretación.
      - Aquí: la spec `005-resultados` (consultas por línea, exportación, evolución por fase) y la
        `006-interfaz-y-calculo` (menús y ventana de interpretación).
      - Lo observado: `dialogos/D04` §1 (contorno externo fijo o con elementos infinitos) y §6
        (interfaz estructural), `D04` §5, `D05` §3 y `D07` §3 (gráficos y tablas de revestimientos,
        bulones y juntas), `D08` §5 (muelles); `reproducciones/P03`, `P04` y `P22`.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Specs 013 (revestimiento), 014 (bulones) y 015 (elemento junta): la interfaz estructural es una
  junta a cada lado de un revestimiento, y el pilote, un elemento estructural con interfaz.
- Spec 003 (malla; la 003 dejó aquí los elementos infinitos), `004-modelo-y-proyecto` (contorno de
  interfaz y condición del contorno externo), `005-resultados` y `006-interfaz-y-calculo`.

## Contexto y objetivo

Tres piezas que cierran la fase. **La interfaz estructural**: un revestimiento con una junta a uno
o a los dos lados, para que el terreno deslice sobre una pantalla, un geosintético o una placa
(D04 §6). **Los elementos infinitos** en el contorno exterior, para representar un medio infinito
sin alejar el contorno; los piden cinco fichas (STR-03, -07, -11, -21 y -30), y ningún manual de
teoría los formula. **Los resultados de soporte** en la interpretación: gráficos y tablas de
esfuerzos de revestimientos, bulones y juntas por fase. Se añade el **pilote** (`PILOTE`,
STR-31), que es un elemento estructural con interfaz de fuste y punta.

## Usuarios / actores

- **El ingeniero** de pantallas, refuerzos y pilotes; **el ingeniero de túneles** que quiere un
  contorno cercano; **quien lee resultados** en la interfaz, la API o el servidor MCP.

## Historias de usuario

- H1: Como ingeniero quiero una pantalla o un geosintético que deslice sobre el terreno según la
  resistencia del contacto.
- H2: Como ingeniero quiero un contorno exterior con elementos infinitos, para un modelo pequeño
  que se comporte como el medio infinito, y saber en el resultado cuál usé.
- H3: Como ingeniero quiero ver y exportar el axil, el cortante y el momento a lo largo de un
  revestimiento, el axil de un bulón y las tensiones de una junta, por fase.
- H4: Como ingeniero quiero un pilote cargado en cabeza con su resistencia por fuste y por punta.

## Requisitos funcionales (EARS)

**Interfaz estructural y pilote**

- RF-1: EL SISTEMA coloca una interfaz estructural sobre una polilínea, con un revestimiento y una
  junta en el lado positivo, en el negativo o en los dos, con extremos abiertos o cerrados, y parte
  las regiones que atraviesa sin dejar láminas que nadie ha pedido (P22).
- RF-2: EL SISTEMA da los resultados del revestimiento y de cada junta de la interfaz, como en las
  specs 013 y 015.
- RF-3: EL SISTEMA ofrece el pilote con interfaz de fuste y resistencia de punta, con su separación
  fuera del plano a la vista (regla 12), si se decide que entra (duda 3).

**Elementos infinitos**

- RF-4: EL SISTEMA ofrece como condición del contorno exterior la fija y la de elementos infinitos;
  la que se use va con el resultado (regla 12).
- RF-5: CUANDO hay elementos infinitos, EL SISTEMA los hace compatibles con T3 y con T6 y con la
  tensión de campo y la excavación (duda 1); SI el contorno no admite el elemento (por ejemplo, no
  es convexo), ENTONCES error que lo explica.

**Resultados de soporte**

- RF-6: EL SISTEMA da gráficos por fase a lo largo de cada revestimiento (axil, cortante, momento;
  también uno frente a otro), bulón (axil, tensión, con su capacidad) y junta (tensiones y
  desplazamientos frente a la distancia, x o y), con la conversión de signos de la regla 10 en un
  único sitio.
- RF-7: EL SISTEMA exporta esas tablas con el mismo número que se dibuja, y lo que no tiene valor va
  como «sin dato».
- RF-8: Todo texto visible pasa por `tr()` con su traducción (regla 2) y toda acción está en un
  menú (regla 3); cada operación existe también sin Qt, en las operaciones de la 006.

**Motor**

- RF-9: EL SISTEMA tiene la interfaz, el pilote y los elementos infinitos en la referencia en
  Python, oráculo de Rust, con su identidad (ADR-0001).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-STR-07` y `VER-STR-21` con elementos infinitos | Las de sus casos (013, 014) | Con contorno cercano e infinitos, lo mismo que con el contorno lejano y fijo con que se validaron, dentro de la tolerancia del caso |
| Hueco circular con elementos infinitos | Kirsch (1898), en Jaeger, Cook y Zimmerman (2007), §8.4 | El caso 005 (STR-01) con contorno cercano: σθ(a) y ur(a) |
| `VER-STR-03`, `-30` y `-11` | Las de sus fichas | Igual que STR-07, cuando existan sus leyes (008); STR-11 es una **comparación** |
| Interfaz muy rígida y muy resistente | — | Igual que el revestimiento adherido de la 013 |
| Interfaz sin rigidez tangencial | — | Placa lisa: sin tensión tangencial en el contacto |
| `VER-STR-31`, pilote en arena | Cernica (1995) | Carga última por fuste y por fuste y punta. La ficha toma las ecuaciones del manual de otro programa: hay que leerlas en Cernica |
| `VER-SLP-24`, terraplén con geosintético | Borges y Cardoso (2002), numérica publicada | Factor del SSR; falta la rigidez del refuerzo (S06, duda 13): no vale como validación hasta tener el dato |
| Resultados | — | La tabla exportada es el valor del motor, con la conversión de signos documentada; un elemento excavado da «sin dato» |
| Regla 7 | — | Cada opción (lado de la junta, extremos, condición del contorno), con el test que mueve el número |

Otros con interfaz: `VER-CON-02` (placa rígida sobre una junta lisa; fase 4), `VER-XFM-16`
(revestimiento compuesto con junta; fase 7), `EJ-THM-08` (sin referencia).

## Fuentes por conseguir

- Elementos infinitos: los manuales no los formulan. Zienkiewicz y Taylor (2000), vol. 1, §9.13
  («infinite domains and infinite elements», con su función de transformación), está en la
  bibliografía: por leer y comprobar si basta para elementos lineales y cuadráticos.
- Cernica (1995), para el pilote; Borges y Cardoso (2002), para SLP-24.
- La interfaz estructural no tiene manual de teoría: hereda las fuentes de la 013 y la 015.

## Requisitos no funcionales

- Los resultados de soporte van en `modelo.h5` con la huella (ADR-0003) y se leen desde un solo
  sitio para la interfaz, la API y el informe, como `result_rows` en el núcleo.
- El motor no sabe de gráficos ni de contornos (regla 11). Sin dependencias nuevas.

## Casos límite

- Interfaz que cruza un contorno de material o una excavación; interfaz con un extremo en el
  contorno exterior; dos interfaces que se cortan.
- Elementos infinitos en un contorno rectangular (esquinas), junto a una carga o con peso propio.
- Revestimiento o bulón sin fases activas en la fase pedida; junta toda excavada; gráficos de
  varios soportes a la vez.

## Fuera de alcance

- **Muelles**: el índice solo los pide en `VER-DYN-08` (dinámico, fase 7). Sin caso estático, un
  muelle sería un ajuste sin test que mueva un número validado (regla 7): fuera.
- Contornos absorbentes y de campo libre (fase 7); la presión de agua en la interfaz (fase 4).
- El geosintético como elemento, mientras la 010 no decida dónde va (su duda 13).

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Todos los RF con su test en verde, y la regla 7 en cada ajuste nuevo
- [ ] STR-07 y STR-21 con elementos infinitos dentro de la tolerancia de su caso, con la malla y el
      estudio de convergencia (regla 9); STR-31, si entra el pilote
- [ ] Las identidades de la tabla, en verde y con dientes; referencia y Rust idénticas
- [ ] Textos traducidos y acciones en menús; changelog con lo encontrado; fichas con su
      «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. ¿Hacen falta los elementos infinitos?** Los cinco casos que los piden
  se pueden validar con el contorno lejano y fijo y su identidad (spec 001, D3 bis; la 008 hace lo
  mismo con STR-03 y STR-30). Opciones: (a) entran aquí; (b) se aplazan hasta que un caso no se
  pueda hacer sin ellos. Si entran: qué formulación, y cómo tratan la tensión de campo.
- [NECESITA ACLARACIÓN] **2. Interfaz estructural, revestimiento compuesto con junta y
  geosintético**: CON-02 y XFM-16 hablan de «revestimiento compuesto» unido por una junta, P22 de
  interfaz con geosintético. ¿Un solo mecanismo? ¿Se puede retirar? (en la referencia, no).
- [NECESITA ACLARACIÓN] **3. El pilote**: (a) aquí, como revestimiento con interfaz y punta; (b) en
  una spec propia. Solo lo pide STR-31, en deformación plana con 15 m de separación fuera del
  plano.
- [NECESITA ACLARACIÓN] **4. Dónde van los resultados de soporte**: las specs 013 a 015 necesitan
  sus esfuerzos para validar STR-07, -21 y -28. Se propone que cada una dé sus magnitudes (motor y
  `.h5`) y que aquí queden solo los gráficos, las tablas y los menús.
- [NECESITA ACLARACIÓN] **5. La marca de «sin dato»**: NaN o un campo de estado aparte (D07).
- [NECESITA ACLARACIÓN] **6. Muelles**: se dejan fuera (solo dinámico). ¿De acuerdo?
