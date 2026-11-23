# Spec 022 — Elasticidad anisótropa y no lineal (Duncan-Chang) y ensayos de laboratorio

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
      - Aquí: `ogr_fem2d/engine/reference/elastic.py` (solo isótropa, en deformación plana y en
        axisimetría), `engine/model.py` (`Material`: elástico o Mohr-Coulomb) y
        `engine/interface.py` (`material_row`, la fila de parámetros que cruza a Rust).
      - Núcleo: no hay elasticidad anisótropa ni no lineal. `hydraulic/permeability_models.py`
        guarda una permeabilidad anisótropa con razón y ángulo (`k2_k1`, `k1_angle_deg`): el
        convenio del ángulo de los ejes del material debería ser uno solo en todo el programa.
        `geometry/anisotropic_surface.py` (polilínea que orienta la estratificación, punto a punto)
        sirve hoy a criterios de equilibrio límite; si orienta también la rigidez, es genérico.
      - Lo observado: la reproducción P16 y su ensayo uniaxial P16b (carpeta A del análisis de
        interfaz, `reproducciones/`); teoría en `C_teoria/T07a` §3 y `T07c` §2; signos en `T00`
        §3.2 y erratas en §3.3. La spec 021 (duda 1) pregunta si los ensayos de un solo Q8
        (`VER-STR-13`, `-29`) dan lo mismo con triángulos.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 002 (motor elástico, deformación plana y axisimetría, desplazamientos impuestos) y su D6, que
  rechaza las leyes plásticas con T3 y en axisimetría; spec 007 (escalones y Newton).
- Spec 008: el contrato común de ley (RF-8, RF-9) y el Mohr-Coulomb que pone la rotura de
  Duncan-Chang; su RF-10 para `VER-STR-15` y `-29`, axisimétricos.
- Specs `004-modelo-y-proyecto` (parámetros y orientación por material), `005-resultados`
  (magnitudes por punto y por fase) y `006-interfaz-y-calculo` (diálogos, menús, gráficos).
- Spec 021 solo si un caso exige cuadriláteros (su duda 1).

## Contexto y objetivo

El motor solo tiene elasticidad isótropa. Dos familias de la fase 5 cambian la rigidez sin
plasticidad propia: la **anisótropa** (`ELAS-ANISO`: transversalmente isótropa, cinco constantes, y
ortótropa, nueve, en ejes del material), que pide `VER-STR-08`, y la **no lineal hiperbólica de
Duncan y Chang (1970)** (`DC`), con rigidez que depende del confinamiento y del nivel de tensión, una
rama de descarga-recarga y rotura de Mohr-Coulomb, que piden `VER-STR-14`, `-15` y `-29`. La
anisotropía es además la rigidez de modelos posteriores (hinchamiento, T07b §8; T07c §4).

Esta spec trae también lo que validan todas las leyes de la fase: la **simulación de ensayos de
laboratorio** (`ENSAYO-LAB`) y las **trayectorias de tensión y curvas en un punto** (`POST-TRAY`).
Se piden aquí porque es la primera spec de la fase que los necesita (`VER-STR-29`) y porque la
elasticidad anisótropa da la forma más barata de validarlos; las specs 023, 024 y 026 los usan. La
regla 8 exige probar cada ley en un punto de Gauss contra su fuente: este es ese banco de pruebas,
en la referencia en Python (ADR-0001) y en el modelo de un elemento.

## Usuarios / actores

- **El ingeniero de rocas**, con macizos estratificados o esquistosos; **el ingeniero de suelos**, con
  arenas y arcillas de rigidez dependiente de la tensión.
- **El investigador y el docente**, que simulan un ensayo y comparan con el laboratorio.
- **Las specs 023 a 026**, que validan sus leyes con el mismo banco; **los casos de validación**.

## Historias de usuario

- H1: Como ingeniero quiero dar las constantes de un material transversalmente isótropo u ortótropo
  y el ángulo de sus ejes, y saber sin ambigüedad qué significa cada coeficiente de Poisson.
- H2: Como ingeniero quiero un Duncan-Chang con descarga-recarga y rotura de Mohr-Coulomb, y ver con
  el resultado la presión de referencia y el esquema de integración que se usaron.
- H3: Como investigador quiero simular un ensayo triaxial, edométrico o uniaxial (carga, descarga y
  recarga; con control de tensión o de deformación) y obtener sus curvas y su trayectoria p–q.
- H4: Como desarrollador quiero que el ensayo en un punto y el ensayo con un elemento den lo mismo.

## Requisitos funcionales (EARS)

**Elasticidad anisótropa (`ELAS-ANISO`)**

- RF-1: EL SISTEMA admite elasticidad transversalmente isótropa y ortótropa, con sus constantes en
  ejes del material y un ángulo de esos ejes respecto a los globales, en deformación plana (y en
  axisimetría solo con las orientaciones que la fuente admita: duda 3).
- RF-2: EL SISTEMA define cada coeficiente de Poisson por el ensayo que lo mide (qué deformación
  dividida por cuál, bajo qué tensión) y lo dice en el diálogo y en la documentación (S06, duda 10);
  un ensayo uniaxial de un elemento lo comprueba (regla 7).
- RF-3: SI las constantes no dan una rigidez simétrica y definida positiva, o violan las relaciones de
  reciprocidad de la fuente, ENTONCES EL SISTEMA lo rechaza con el material y la constante, sin
  corregirlo.
- RF-4: EL SISTEMA da las tensiones y deformaciones en ejes globales y, si se pide, en ejes del
  material, con el giro hecho en un único sitio.

**Duncan-Chang (`DC`)**

- RF-5: EL SISTEMA integra la ley hiperbólica de Duncan y Chang (1970) con su módulo tangente de
  carga, su módulo de descarga-recarga, el coeficiente de Poisson constante o la alternativa de la
  fuente que se adopte (duda 6), y rotura de Mohr-Coulomb (008).
- RF-6: EL SISTEMA decide carga o descarga-recarga con un criterio que tenga fuente, guarda en cada
  punto la variable de historia que lo decide y la da con el resultado (duda 5).
- RF-7: EL SISTEMA muestra con el resultado la presión de referencia, el esquema de integración del
  módulo dentro del escalón y el número de escalones, porque los tres mueven el número (regla 12;
  `VER-STR-29`: el manual atribuye su diferencia con la fuente a ese esquema).
- RF-8: SI la tensión que gobierna el módulo deja de ser de compresión, o el módulo se anula, ENTONCES
  EL SISTEMA hace lo que se decida con fuente y lo dice; no devuelve un módulo nulo ni negativo.

**Ensayos de laboratorio (`ENSAYO-LAB`) y trayectorias (`POST-TRAY`)**

- RF-9: EL SISTEMA simula ensayos de estado homogéneo (triaxial drenado en compresión y en extensión,
  a volumen constante, edométrico, uniaxial; carga, descarga y recarga) con control de tensión, de
  deformación o de una trayectoria dada en p–q, en dos niveles: un punto de Gauss sin malla y un
  modelo de uno o pocos elementos calculado por el motor normal.
- RF-10: CUANDO las dos simulaciones de RF-9 usan la misma ley y la misma trayectoria, EL SISTEMA da
  el mismo resultado a redondeo; si no, el banco de pruebas no vale y se dice.
- RF-11: EL SISTEMA da por fase y escalón, en un punto, p, q, εv, εq, εa, σ1/σ3 y, cuando exista, el
  exceso de presión, cada magnitud con su definición y su fuente, en compresión positiva para el
  usuario y con la conversión en el sitio único de la regla 10; y lo exporta a tabla.
- RF-12: Toda acción nueva (definir el ensayo, lanzarlo, ver sus curvas) está en un menú y todo texto
  pasa por `tr()` (reglas 2 y 3).

**Cada ley**

- RF-13: Cada ley tiene su referencia en Python, oráculo de Rust con identidad del orden de 1e-10
  (ADR-0001), su prueba en un punto de Gauss contra su fuente (regla 8) y un test de signo con las
  ecuaciones reescritas en tracción positiva (regla 10; T00 §3.2 da la elasticidad no lineal en
  compresión positiva).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-STR-08`, hueco circular transversalmente isótropo | Amadei (1983); Hooke anisótropo de Christensen (1979), según la ficha; Jaeger, Cook y Zimmerman (2007), cap. 5, lo resume citando a Amadei | σθ, ux y uy en la pared, 0–90°. La solución transcrita en la ficha no contiene νxz: hay que comprobar en Amadei cómo entra la deformación plana (en P16 la lectura llevó el error máximo en u del 2 % al 7 %) |
| Ensayo uniaxial de un elemento (como P16b) | La ley de Hooke de la fuente | Cociente de deformaciones: fija qué es ν12 (RF-2), en deformación plana y como identidad |
| Límite isótropo | Identidad | Anisótropa con constantes isótropas, igual a la elástica de la 002 a redondeo |
| Giro de los ejes | Identidad | Material y carga girados el mismo ángulo dan lo mismo en ejes del material; θ y θ + 180° iguales |
| `VER-STR-29`, triaxiales con descarga-recarga | Duncan y Chang (1970), experimental y numérica | q–εa de la arena suelta. La densa no se puede comparar con la ficha (escalas mezcladas); el confinamiento no está en la ficha, sí en la fuente (por comprobar) |
| Punto material Duncan-Chang | Duncan y Chang (1970) | Un triaxial a σ3 constante con escalones pequeños reproduce la hipérbola de la fuente; la descarga sigue su módulo |
| `VER-STR-14`, zapata corrida en arena | Tomlinson (2001), ensayo y elementos finitos; Duncan y Chang (1970) | Asiento frente a presión. Referencia **débil**: sin presión de referencia ni propiedades de la zapata; unidades mezcladas |
| `VER-STR-15`, zapata circular en arcilla no drenada | Tomlinson (2001), numérica publicada (la figura la rotula «analítica») | Asiento frente a presión, en axisimetría con φ = 0 |
| Ensayo en un punto frente a un elemento | Identidad (RF-10) | Las mismas curvas en los dos niveles, con elasticidad isótropa, anisótropa y Duncan-Chang |
| Regla 7 | — | Cada opción (tipo de Poisson, esquema, presión de referencia, ángulo) mueve el número |

Se proponen como los que la cierran `VER-STR-08` y `VER-STR-29`; `-14` y `-15` como numérica
publicada, con la tolerancia fijada antes de medir y la malla de su estudio (regla 9).

## Fuentes por conseguir

- Amadei (1983), *Rock Anisotropy and the Theory of Stress Measurements*; Christensen (1979),
  *Mechanics of Composite Materials*; la reproducción P16 nombra además a Lekhnitskii, sin cita.
- Duncan y Chang (1970), *J. Soil Mech. Found. Div.*, ASCE, 96(SM5), 1629–1653 (T00 §5.A). La
  opción de Poisson a partir de un módulo volumétrico (T07c §2) no tiene fuente en el catálogo.
- Tomlinson (2001), *Foundation Design and Construction*, 7.ª ed., para `VER-STR-14` y `-15`.
- Las condiciones de admisibilidad de las constantes anisótropas (RF-3): por localizar.
- Disponibles en `../Referencias/Bibliografia/`: Jaeger, Cook y Zimmerman (2007), que trata la
  elasticidad ortótropa y transversalmente isótropa en el cap. 5 (el texto cita a Amadei);
  Zienkiewicz y Taylor (2000), vol. 1, que menciona materiales anisótropos (alcance sin comprobar);
  de Souza Neto, Perić y Owen (2008) no trata la elasticidad anisótropa ni Duncan-Chang (su §10.3 es
  plasticidad anisótropa de metales). Las definiciones de p, q y εq de RF-11, de cualquiera de ellas.

## Requisitos no funcionales

- La elasticidad isótropa no se hace más lenta por existir la anisótropa: medida A/B antes de cerrar.
- El motor recibe las constantes y el ángulo ya en su sistema, sin unidades de usuario (regla 11);
  la presión de referencia de Duncan-Chang llega en las unidades del motor.

## Casos límite

- Constantes casi isótropas; un ν que lleva la rigidez al borde de lo admisible; E1 muy distinto de E3.
- Ángulo de 90° (ejes intercambiados) y ángulos negativos; orientación que deja el eje fuera del plano
  en una dirección que no es de simetría del material (duda 3).
- Duncan-Chang con confinamiento nulo o de tracción; con c = 0 en superficie; inversión de carga
  dentro de un escalón; rotura alcanzada a mitad de escalón.
- Ensayo a volumen constante con ν cercano a 0.5; edométrico con la rigidez lateral muy alta.

## Fuera de alcance

- Las otras elasticidades no lineales de T07a §3 (potencial en p, degradación del corte con la
  deformación) y las viscoelásticas (Maxwell, Standard, Burgers): ningún caso del índice las pide
  (duda 7).
- La resistencia anisótropa (025), el hinchamiento (026) y la permeabilidad anisótropa (017).
- El no drenado con generación de presión (019); `VER-STR-15` se calcula en totales, como su ficha.

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Todos los RF con su test en verde, y la regla 7 en cada opción nueva
- [ ] Cada ley probada en un punto de Gauss contra su fuente, con identidad Python–Rust
- [ ] `VER-STR-08` y `VER-STR-29` dentro de la tolerancia fijada antes de medir, con su malla
- [ ] El banco de ensayos con su identidad de RF-10 en verde y con dientes
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. Definición de ν12** (S06, duda 10): la ficha de `VER-STR-08` usa el
  acoplamiento con el módulo del eje 1; la reproducción P16b comprobó que el programa de referencia
  lo divide por el del eje 2 (su «ν12» es el ν21 de la otra notación). Opciones: (a) la notación de
  Amadei (1983) o la de Jaeger et al. (2007); (b) pedir ν12 y ν21 y comprobar la reciprocidad; (c)
  la del programa de referencia, para leer sus archivos. Cambia el número de `VER-STR-08`.
- [NECESITA ACLARACIÓN] **2. Erratas del catálogo** (T07a §3.8): «ν1» por ν12 en la transversalmente
  isótropa y G13 por G23 en la ortótropa. Se resuelven con la fuente, no con el manual.
- [NECESITA ACLARACIÓN] **3. Orientación en 2D**: un ángulo en el plano; qué eje queda fuera del
  plano; si se admite un plano de isotropía inclinado respecto a z; en axisimetría, solo ejes
  alineados con el de simetría. ¿Ángulo fijo por material o también la superficie anisótropa del
  núcleo, punto a punto?
- [NECESITA ACLARACIÓN] **4. Deformación plana en `VER-STR-08`**: la solución transcrita es la de las
  constantes en el plano. ¿Se reducen con la deformación fuera del plano nula (P16 lo apunta) o la
  fuente lo hace de otra forma? Sin leer Amadei (1983), el caso no tiene valor esperado.
- [NECESITA ACLARACIÓN] **5. Carga y descarga en Duncan-Chang**: el manual no dice qué variable de
  historia compara (T07c §2.4). Opciones: el nivel de tensión movilizado máximo, el desviador máximo,
  o lo que diga la fuente. Sin fuente, no entra.
- [NECESITA ACLARACIÓN] **6. Poisson en Duncan-Chang**: constante (la ficha de `VER-STR-29`) o a partir
  de un módulo volumétrico dependiente de la tensión (T07c §2, sin fuente en el catálogo; `VER-STR-15`
  habla de un Poisson tangente con ν = 0.48).
- [NECESITA ACLARACIÓN] **7. Otras elasticidades no lineales** de T07a §3: ningún caso las pide, pero
  el modelo de endurecimiento (024) dice admitir «cualquier opción elástica» y los de la 026 tienen
  rigidez dependiente de la tensión. ¿Se dejan para la spec que las necesite?
- [NECESITA ACLARACIÓN] **8. Esquema de integración de Duncan-Chang**: módulo al principio del
  escalón (lo que el manual dice del programa de referencia), medio en el escalón (lo que dice de la
  fuente) o implícito. Cambia `VER-STR-29`; la elección tiene que salir de la fuente.
- [NECESITA ACLARACIÓN] **9. Presión de referencia por defecto**: el diálogo observado trae 101.3 kPa.
  ¿Dato obligatorio, o defecto mostrado con el resultado (regla 12)? Depende de las unidades.
- [NECESITA ACLARACIÓN] **10. Dónde vive el banco de ensayos**: aquí (propuesta de este borrador),
  en una spec propia antes de la 022, o repartido entre la 005 (trayectorias) y la 006 (gráficos). El
  ensayo de corte de juntas de la 015 (su RF-7) es el mismo problema con otra ley.
- [NECESITA ACLARACIÓN] **11. Elemento de los ensayos** (spec 021, duda 1): un Q8 en las fichas; con
  T6 o T3 el estado homogéneo debería salir exacto. Comprobarlo aquí decide si la 021 hace falta
  para la fase 5.

Las referencias P16 y P16b son de la carpeta A del análisis de interfaz
(`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/`, `reproducciones/`); T00, T07a y T07c,
de la carpeta C (`C_teoria/`).
