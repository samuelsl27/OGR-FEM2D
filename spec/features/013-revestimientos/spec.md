# Spec 013 — Revestimientos

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 3 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 013 — Revestimientos»). Solo el **qué** y el
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
      - Aquí: `docs/motor/entrada.md` (dos grados de libertad por nudo, un tipo de elemento por
        modelo; una viga añade el giro), `ogr_fem2d/engine/reference/` (oráculo; no hay
        elementos de una dimensión) y el mapa segmento → nudos y lados de la malla (spec 003), que
        dice sobre qué nudos va un revestimiento colocado en un contorno.
      - Núcleo: `ogr_core/support/support.py` es de equilibrio límite (los soportes son fuerzas):
        sirve el patrón de tipos con registro y lectura y escritura (`SupportType`,
        `register_support`, `to_dict`, `from_dict`) y el `Geosynthetic`, no la mecánica.
      - Slip2D: `ogr_gui/dialogs/define_support_dialog.py` y `support_properties_dialog.py`
        (propiedades por tipo), `support_force_diagram.py` y `ogr_gui/xy_chart.py` (diagramas a lo
        largo de un soporte, para la 016).
      - Lo observado: `dialogos/D04` (cuatro tipos y sus valores por defecto, *Add Liner* con
        instalación y retirada, gráfico y tabla de esfuerzos), `reproducciones/P03` (STR-07) y
        `P20` (instalación diferida); teoría en `C_teoria/T03` y `T01` §4 (convenios).
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 002 (motor y entrada), 003 (nudos de cada segmento), `004-modelo-y-proyecto` (el
  revestimiento como objeto del modelo), 007 y 008 (no linealidad, para la plastificación), 012
  (fase de instalación y retirada).
- Spec 001, D1 (tracción positiva): el convenio interno vale también para los esfuerzos de la viga
  (regla 10).

## Contexto y objetivo

Un revestimiento de hormigón proyectado, una cercha o una pantalla trabajan a axil y a flexión: en
2D son vigas colocadas sobre un contorno y unidas al terreno. Esta spec añade al motor ese elemento,
elástico y con plastificación de la sección, su sección compuesta, sus rótulas y su instalación y
retirada por fase, y lo valida con STR-07, el caso que cierra la fase con él. Ningún manual de
teoría formula la viga del revestimiento (`C_teoria/T00`, §3.1 y T03): solo su plastificación por
capas. El signo del momento en la reproducción de STR-07 salió opuesto al de la expresión
analítica (S06, duda 4): el convenio se fija antes de programar.

## Usuarios / actores

- **El ingeniero de túneles y de excavaciones**; **el modelo** (004) y **la interpretación**
  (016), que leen los esfuerzos; **los casos de validación**.

## Historias de usuario

- H1: Como ingeniero quiero colocar un revestimiento sobre el contorno de una excavación y ver su
  axil, su cortante y su momento a lo largo de él, para dimensionarlo.
- H2: Como ingeniero quiero que el revestimiento plastifique cuando su sección se agota y ver dónde,
  para saber si resiste.
- H3: Como ingeniero quiero una sección compuesta (cercha y hormigón), con el reparto de esfuerzos
  entre las dos.
- H4: Como ingeniero quiero rótulas en el revestimiento y extremos articulados o empotrados.
- H5: Como ingeniero quiero saber qué convenio de signos tiene cada esfuerzo, sin adivinarlo.

## Requisitos funcionales (EARS)

- RF-1: EL SISTEMA coloca un revestimiento sobre segmentos de contorno, unido a los nudos de la
  malla de esos segmentos, con un tipo de viga que se elige (duda 1); el tipo usado va con el
  resultado (regla 12).
- RF-2: EL SISTEMA calcula, por elemento de revestimiento y fase, axil, cortante y momento en los
  puntos que se fijen, con **un único convenio interno** documentado (regla 10; duda 2) y la
  conversión a la costumbre del usuario en un solo sitio.
- RF-3: EL SISTEMA define la sección por espesor o por área e inercia, con el ancho fuera del plano
  que se decida (por metro, o con separación); en axisimetría, lo que se decida en la duda 7.
- RF-4: EL SISTEMA admite revestimiento elástico y con plastificación de la sección por capas
  (Owen y Hinton, por comprobar), con resistencias de pico y residual a compresión y a tracción, y
  marca los elementos plastificados.
- RF-5: EL SISTEMA admite una sección compuesta de dos o más componentes y da el reparto de
  esfuerzos entre ellas.
- RF-6: EL SISTEMA admite rótulas (momento nulo) en un punto del revestimiento y condiciones de giro
  en sus extremos.
- RF-7: EL SISTEMA instala y retira el revestimiento por fase (spec 012) y permite cambiar las dos
  fases sin borrarlo (en la referencia no se puede, P20).
- RF-8: SI un revestimiento queda sobre un contorno que no tiene terreno a ningún lado, o con un
  extremo sin sujeción, ENTONCES error que nombra el revestimiento y la fase.
- RF-9: EL SISTEMA tiene cada tipo de viga en la referencia en Python, oráculo de Rust, con su
  identidad (ADR-0001).
- RF-10: Las opciones que se admitan (peso propio, pretensado, holgura de deslizamiento,
  propiedades por fase, tipos de hormigón armado y de cercha de cable, ver la duda 6) entran cada
  una con el test que demuestra que mueve el número (regla 7).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-STR-07`, túnel revestido en medio elástico | Einstein y Schwartz (1979) | Axil y momento a lo largo de un cuadrante del revestimiento. Contorno lejano y fijo con su identidad de dominio finito (como la D3 bis de la spec 001), si los elementos infinitos (016) no están. El 12 % de error en el momento de la referencia no es valor esperado |
| `VER-STR-16`, cinco vigas clásicas | Estática de vigas (la ficha no cita autor: fuente de resistencia de materiales por elegir) | Cortante y momento de vigas isostáticas e hiperestáticas, con rótulas; sin terreno. Es para la viga lo que la regla 8 es para una ley |
| Sección por capas | Owen y Hinton (1986 o 1980), cap. 5 | Sección sola con axil y momento conocidos: capas plastificadas y esfuerzos resistentes frente a la teoría de la sección |
| Variante de `VER-STR-07` con relajación (P20) | La de STR-07 | Mitad sin revestir y mitad con él: esfuerzos, la mitad (con la 012) |
| Signos | Spec 001, D1 | En STR-07, el signo del momento en el hastial y en la clave, con la cara traccionada que diga la solución (S06, duda 4) |
| Límites de rigidez | Kirsch (1898), en Jaeger, Cook y Zimmerman (2007), §8.4 | Con rigidez del revestimiento que tiende a cero, el hueco sin sostener |
| Identidades de elemento | — | Sólido rígido con giro; equilibrio de un tramo libre; referencia y Rust idénticas |
| `VER-STR-10`, cúpula esférica (axisimetría) | Zingoni (1997), aproximación de Hetényi | Solo si entra la axisimetría (duda 7); referencia **aproximada** |
| `VER-STR-11`, túnel revestido en medio plástico | — (otro programa) | **Comparación**, no validación; necesita Drucker-Prager (008) |

Otros que piden `VIGA` y son de otras fases: `VER-CON-02` (fase 4), `VER-DYN-03`, `-04`, `-15` y
`VER-THM-16` (fase 7), `VER-XFM-16` (XFEM), `EJ-EXC-01` (campo, con no drenado) y `EJ-SEE-02`
(sin referencia).

## Fuentes por conseguir

- La formulación del elemento viga (Euler-Bernoulli y Timoshenko) y su unión a una malla de
  triángulos: sin manual de teoría. Zienkiewicz y Taylor (2000), vol. 1, está en la bibliografía,
  pero las vigas no son de ese volumen (por comprobar); el vol. 2 no está.
- Einstein y Schwartz (1979), «Simplified analysis for tunnel supports» (de la ficha).
- Owen y Hinton, *Finite Elements in Plasticity*, cap. 5.5: el catálogo lo fecha en 1986 y en 1980
  (T03 §1.8); por comprobar si son dos ediciones.
- La sección compuesta: la única fuente es una nota técnica no publicada (Carranza-Torres 2004,
  T03 §2); la deducción es de equilibrio y compatibilidad, pero hay que decidir si se cita o se
  busca una publicación.
- Zingoni (1997), *Shell Structures in Civil and Mechanical Engineering*, si entra STR-10.
- Hormigón armado y holgura de deslizamiento: sin fuente en el catálogo.

## Requisitos no funcionales

- Un único convenio de signos interno para los esfuerzos, documentado en `docs/motor/` (regla 10).
- El motor recibe vigas como datos discretos (nudos, sección, material, fase), sin contornos
  (regla 11). Sin dependencias nuevas.

## Casos límite

- Revestimiento cerrado (anillo) y abierto; extremos libres; tres revestimientos en un nudo.
- Revestimiento sobre un arco con T6 (nudo intermedio sobre el arco, spec 003, D14).
- Revestimiento en el contacto de dos regiones activas, o sobre una que se excava después.
- Viga muy esbelta con la formulación de Timoshenko (bloqueo por cortante, por comprobar con la
  fuente); rótula en un extremo; espesor nulo; sección compuesta con un componente nulo.

## Fuera de alcance

- La interfaz estructural (junta entre revestimiento y terreno) y el pilote: spec 016. Aquí el
  revestimiento comparte los nudos del terreno.
- Bulones (014), juntas (015), los gráficos de esfuerzos en la interpretación (016).
- El geosintético como revestimiento, mientras la 010 no decida dónde va (su duda 13).
- Dinámico, térmico y XFEM (fase 7).

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Convenio de signos de los esfuerzos fijado y documentado antes de programar
- [ ] Todos los RF con su test en verde, y la regla 7 en cada ajuste nuevo
- [ ] STR-07 y STR-16 dentro de la tolerancia fijada antes de medir, con la malla y el estudio de
      convergencia que la justifican (regla 9)
- [ ] Las identidades de la tabla, en verde y con dientes; referencia y Rust idénticas
- [ ] Changelog con lo encontrado; fichas STR-07 y STR-16 con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. Euler-Bernoulli o Timoshenko** (el plan: «por decidir con fuente»):
  (a) los dos, a elegir; (b) uno. ¿Cuál por defecto? En la referencia, Timoshenko (D04), y STR-07
  se hizo con Euler-Bernoulli: el defecto cambia el número (regla 12).
- [NECESITA ACLARACIÓN] **2. Convenio de signos de N, V y M** (S06, duda 4): axil de tracción
  positivo, coherente con el motor; el momento, según la cara traccionada respecto al sentido del
  revestimiento o respecto al terreno. La referencia no dice qué cara es positiva (T01 §4, T03 §3).
- [NECESITA ACLARACIÓN] **3. Unión a la malla**: con T6, el lado tiene tres nudos; (a) viga de tres
  nudos; (b) dos vigas por lado; (c) otra. El giro es un grado de libertad nuevo: la entrada del
  motor deja de tener dos por nudo.
- [NECESITA ACLARACIÓN] **4. Hipótesis de contacto en STR-07**: la ficha no la dice; la fuente
  trata, por comprobar, el contacto adherido y el deslizante. Aquí el revestimiento va adherido; el
  deslizante pide la interfaz (016).
- [NECESITA ACLARACIÓN] **5. Plastificación por capas**: criterio de cada capa, papel del cortante,
  residual distinta de cero y número de capas por defecto (la referencia usa 100: regla 12); todo
  `[NO DOCUMENTADO]` en T03 §1.4.
- [NECESITA ACLARACIÓN] **6. Qué tipos y opciones entran**: viga estándar sí; hormigón armado,
  cercha de cable, geosintético, peso, pretensado, holgura, propiedades por fase: ¿aquí, después o
  nunca? Ningún caso de la fase los pide.
- [NECESITA ACLARACIÓN] **7. Axisimetría** (STR-10): una viga en axisimetría es una lámina de
  revolución, con esfuerzo circunferencial. ¿Entra aquí o en una spec propia?
- [NECESITA ACLARACIÓN] **8. Esfuerzos por metro o por anillo**: en deformación plana, por metro de
  túnel; en axisimetría, por el anillo entero, como las fuerzas (spec 002, D2).
- [NECESITA ACLARACIÓN] **9. El contorno de STR-07**: la reproducción P03 dice 17.5 m de radio
  exterior con elementos infinitos y la ficha lee ≈ 12.5 m en la figura 7.5. Con contorno lejano y
  fijo el dato no hace falta; con elementos infinitos sí.
- [NECESITA ACLARACIÓN] **10. «Retirada automática»** (el plan): no se dice qué es (¿cuando se
  excava el terreno de los dos lados?). Por comprobar en la referencia antes de proponerlo.
