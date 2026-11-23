# Spec 014 — Bulones

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 3 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 014 — Bulones»). Solo el **qué** y el
> **porqué**, sin fórmulas ni decisiones tomadas. **Antes de abrirla hay que reevaluarla** (sección
> siguiente); después, plan y tareas con el OK de la propietaria.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador (núcleo v0.2.6):
      - Núcleo, `ogr_core/support/support.py`: en equilibrio límite los soportes son fuerzas, no
        elementos (S02), pero se aprovechan las definiciones. `SupportType` con registro y lectura
        y escritura; `EndAnchored`, `GroutedTieback`, `GroutedTiebackFriction`, `SoilNail` (sus
        propiedades, no su mecánica); `SupportInstance` (cabeza y cola, separación fuera del plano,
        `intersections_with_polyline`, útil para el cruce con juntas de la 015);
        `SupportPattern.generate_along_segment` (orientación por ángulo, normal o profundidad,
        separación, giro de 180°) y `pattern_id` para desagrupar. `support/bond.py` (adherencia a
        lo largo de un soporte, ligada al equilibrio límite).
      - Slip2D: `ogr_gui/dialogs/support_pattern_dialog.py`, `modify_support_pattern_dialog.py`,
        `define_support_dialog.py` y `support_properties_dialog.py`; las operaciones del servidor
        MCP de tipos y patrones de soporte.
      - Aquí: la entrada del motor (`docs/motor/entrada.md`: sin elementos de una dimensión) y la
        malla de la 003 (`ogr_fem2d/mesh/`), donde habrá que localizar los elementos que cruza
        cada bulón.
      - Lo observado: `dialogos/D05` (cinco tipos con sus valores por defecto, patrón, gráfico y
        tabla), `reproducciones/P04` (STR-21); teoría en `C_teoria/T02` §1 y §3.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 002 (motor), 003 (malla: localizar el cruce de un bulón con los elementos),
  `004-modelo-y-proyecto` (el bulón y el patrón como objetos del modelo), 007 (no linealidad: la
  rotura del bulón y de su adherencia), 012 (instalación, retirada y pretensado por fase).

## Contexto y objetivo

Un bulón es una barra que atraviesa el terreno sin que sus nudos coincidan con los de la malla. La
referencia tiene cinco tipos: anclado en los extremos (un muelle entre dos puntos), totalmente
adherido (unido a lo largo), de cable de cordón simple, de fricción (expansivo o ranurado) y
anclaje con tramo libre y tramo adherido. Esta spec los añade al motor en orden de dificultad
(anclado y adherido; fricción; anclaje; cable), con sus patrones, su pretensado y sus resultados, y
los valida con STR-21, el caso que cierra la fase con ellos. Las fórmulas de la ficha de STR-21 dan
desplazamientos discontinuos en el extremo de los bulones (S06, duda 1, P04): hay que revisarlas
con el artículo antes de usarlas.

## Usuarios / actores

- **El ingeniero** que sostiene un túnel, un talud o una pantalla con bulones, anclajes o clavos;
  **el modelo** (004); **la interpretación** (016); **los casos de validación**.

## Historias de usuario

- H1: Como ingeniero quiero colocar un patrón de bulones a lo largo de un contorno, normal a él o
  radial, con longitud y separación, y que una vuelta completa no duplique el bulón de cierre
  (en la referencia sí, P04).
- H2: Como ingeniero quiero ver el axil a lo largo de cada bulón y si ha roto, para dimensionarlo.
- H3: Como ingeniero quiero pretensar un anclaje en su fase de instalación.
- H4: Como ingeniero quiero clavos en un talud y puntales entre dos pantallas con los mismos
  elementos, instalados y retirados por fase.

## Requisitos funcionales (EARS)

**Elementos**

- RF-1: EL SISTEMA representa un bulón por segmentos entre sus cruces con los lados de la malla, y
  pasa su rigidez y sus fuerzas a los nudos de los elementos que atraviesa (duda 2).
- RF-2: EL SISTEMA ofrece el bulón **anclado en los extremos**, unido al terreno solo en sus dos
  extremos, y el **totalmente adherido**, con la rigidez de su adherencia, cada uno con capacidad
  de pico y residual.
- RF-3: EL SISTEMA ofrece el bulón **de fricción**, con la rigidez y la resistencia de su interfaz
  (duda 9), y el **anclaje** con tramo libre y tramo adherido.
- RF-4: EL SISTEMA ofrece el **cable de cordón simple** solo si se consigue su formulación (duda 3).
- RF-5: EL SISTEMA reparte la rigidez de un bulón por su separación fuera del plano, y la separación
  usada va con el resultado (regla 12).
- RF-6: CUANDO el axil supera la capacidad, EL SISTEMA lo lleva a la residual según la ley que se
  decida (duda 8) y marca el segmento.

**Patrón, pretensado y fases**

- RF-7: EL SISTEMA genera patrones a lo largo de un contorno con orientación normal al segmento,
  radial a un punto o con ángulo fijo, longitud y separación; en un contorno cerrado, sin
  duplicados; el patrón se puede desagrupar.
- RF-8: EL SISTEMA aplica un pretensado en la fase de instalación, mantenido o no en las siguientes
  según se decida (duda 4; la referencia lo mantiene por defecto, D05).
- RF-9: EL SISTEMA instala y retira cada bulón por fase (spec 012).

**Comprobación, resultados y motor**

- RF-10: SI un bulón sale del modelo, cae entero en una región excavada o tiene longitud nula,
  ENTONCES error que nombra el bulón y la fase.
- RF-11: EL SISTEMA da por fase el axil y la tensión de cada segmento, la fuerza en la adherencia y
  el estado (elástico, roto), con el convenio interno (tracción positiva, regla 10).
- RF-12: EL SISTEMA tiene cada tipo en la referencia en Python, oráculo de Rust, con su identidad
  (ADR-0001); cada opción (placa de reparto, residual, pretensado mantenido) con su test (regla 7).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-STR-21`, túnel con 72 bulones (anclados y adheridos) | Carranza-Torres (2002) | σr, σθ y ur a lo largo de un radio. Antes, revisar las ecuaciones con el artículo (S06, duda 1). La solución reparte los bulones de forma continua: la diferencia con 72 bulones discretos tiene una razón física y hay que estimarla antes de fijar la tolerancia |
| `VER-STR-20`, bulón adherido a tracción | Farmer (1975) | Tensión tangencial a lo largo del bulón. La rigidez de la lechada de la ficha sale del manual de otro programa: no es fuente |
| `VER-STR-12`, arranque de un bulón de fricción | Farmer (1975); Hyett, Moosavi y Bawden (1996); Cook, Malkus y Plesha (año y edición por comprobar) | Axil a lo largo del bulón, avance de la rotura de la interfaz y curva fuerza-desplazamiento; el manual no tabula la solución teórica |
| Barra con interfaz lineal | La solución cerrada de la ecuación de la barra en medio elástico (T02 §1.6), con su fuente | Lo que la regla 8 pide a una ley: un bulón solo, con su interfaz, contra la solución |
| Bulón anclado en un bloque | — (equilibrio) | La fuerza del muelle y la reacción coinciden; axil constante a lo largo |
| Patrón | — | Número y posición de los bulones en un contorno cerrado (72, no 73, P04) |
| `VER-SLP-99`, muro claveteado (clavos) | Pockoski y Duncan (2000), numérica publicada | **Comparación**: factor del SSR frente a los programas del estudio; necesita la 009; las propiedades de los clavos, de otra fuente |

Otros con bulones: `EJ-SEE-02` (sin referencia, fase 4) y `EJ-EXC-01` (puntales; referencia de
campo, con no drenado y modelos de la fase 5).

## Fuentes por conseguir

- Carranza-Torres (2002), el artículo original de la solución de STR-21 (duda 1).
- Farmer (1975); Hyett et al. (1995, 1996); Moosavi (1997), tesis, para el cable (el manual solo
  lo describe); Cook, Malkus y Plesha (el catálogo da «1981» con «3.ª edición», que no casan).
- El acoplamiento del bulón con la malla y la transferencia por funciones de forma: el manual solo
  lo esboza (T02 §1.8); partir de las funciones de forma de Zienkiewicz y Taylor (2000), que sí
  está en la bibliografía.
- El anclaje, el pretensado y la ley de la interfaz del bulón de fricción: sin fuente. La tesis de
  T02 §3 no tiene autor, año ni lista de referencias.

## Requisitos no funcionales

- El motor recibe cada bulón como segmentos con sus nudos de anclaje y los elementos que cruza, ya
  resueltos fuera del motor (regla 11). Sin dependencias nuevas.
- Lo genérico (propiedades, patrones) se pide a OGR-Core si hace falta cambiarlo; aquí no se copia.

## Casos límite

- Bulón que pasa exactamente por un nudo, sigue un lado o termina sobre él; bulón dentro de un solo
  elemento; bulones que se cruzan.
- Bulón que atraviesa una región excavada después de su instalación; cabeza en un contorno que se
  excava.
- Pretensado mayor que la capacidad; capacidad residual mayor que la de pico.
- Patrón en un tramo con vértices; orientación radial con el punto sobre el contorno.

## Fuera de alcance

- La interacción bulón-junta (Dight 1982): spec 015. El pilote: spec 016.
- Los gráficos de bulones en la interpretación (016); los bulones en el SSR (con la 009).
- Bulones en axisimetría; el bulón helicoidal y las fuerzas de equilibrio límite del núcleo.

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Ecuaciones de STR-21 revisadas contra el artículo (S06, duda 1)
- [ ] Todos los RF con su test en verde, y la regla 7 en cada ajuste nuevo
- [ ] STR-21 (las dos variantes), STR-20 y STR-12 dentro de la tolerancia fijada antes de medir,
      con la malla y el estudio de convergencia que la justifican (regla 9)
- [ ] Las identidades de la tabla, en verde y con dientes; referencia y Rust idénticas
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. Las ecuaciones de STR-21** (S06, duda 1): el manual escribe ρb = rb/a,
  la ficha ve que las fórmulas de la zona no reforzada casan con a/rb, y aun así ur no es continuo
  en rb (P04).
  Revisar con Carranza-Torres (2002); sin eso, STR-21 no se valida.
- [NECESITA ACLARACIÓN] **2. Acoplamiento con la malla**: el manual escribe una matriz por bloques
  sin los términos cruzados de la forma débil (T02 §1.8); funciones de forma del lado o del
  elemento; qué pasa con el T6.
- [NECESITA ACLARACIÓN] **3. Tipos y orden**: (a) los cinco aquí; (b) anclado, adherido y fricción
  aquí, anclaje y cable después. El cable no tiene formulación en el manual.
- [NECESITA ACLARACIÓN] **4. Pretensado**: cómo se aplica y si se mantiene después de la fase de
  instalación (la referencia: «fuerza constante en la fase de instalación», marcada por defecto).
- [NECESITA ACLARACIÓN] **5. Clavos (`CLAVO`, `VER-SLP-99`)**: se proponen aquí, como bulón adherido
  con resistencia de adherencia; su caso es una comparación y necesita la 009.
- [NECESITA ACLARACIÓN] **6. Puntales (`PUNTAL`, `EJ-EXC-01`)**: se proponen aquí, como barra entre
  dos puntos que trabaja también a compresión, instalada y retirada por fase. Los forjados del mismo
  caso son «apoyos»: ¿restricción, viga (013) o puntal?
- [NECESITA ACLARACIÓN] **7. Patrón**: «normal al contorno» es normal al segmento del polígono en la
  referencia (P04), no radial; ¿se ofrecen las dos? ¿Qué hace un bulón en un vértice?
- [NECESITA ACLARACIÓN] **8. Rotura**: frágil a la residual o plástica; cómo entra en Newton (no
  documentado en el manual); efecto de la partición del incremento.
- [NECESITA ACLARACIÓN] **9. Bulón de fricción**: el manual no da límite a su interfaz, la tesis de
  T02 §3 sí muestra deslizamiento a carga constante. ¿Con límite o sin él?
- [NECESITA ACLARACIÓN] **10. Unidades de la rigidez de la adherencia**: fuerza por unidad de
  longitud y de desplazamiento, no «rigidez a cortante» (T02 §1.8); cómo se muestra.
