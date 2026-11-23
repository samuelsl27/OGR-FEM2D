# Spec 024 — Endurecimiento y ablandamiento

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
      - Aquí: `ogr_fem2d/engine/reference/mohr_coulomb.py` (Mohr-Coulomb perfecto, el límite de
        esta ley sin endurecimiento); lo que haya dejado la 008 (Mohr-Coulomb residual y
        frágil-plástico, `MC-RES`; contrato de ley) y la 022 (banco de ensayos).
      - Núcleo: ninguna ley con endurecimiento. Las funciones tabuladas de equilibrio límite
        (`materials/builtin_models.py`: `CPhiFunction`, `ShearNormalFunction`) interpolan c y φ en
        función de la tensión normal, no de la deformación plástica; su convenio fuera de la tabla
        (se mantiene la última fila) es una decisión suya, no de una fuente.
      - Lo observado: teoría en `C_teoria/T07c` §1 (este modelo) y `T07a` §5 (Mohr-Coulomb con
        casquete); signos en `T00` §3.2. El caso `VER-CNS-01` no tiene reproducción en la carpeta A.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 008 (contrato de ley, Mohr-Coulomb con tracción y dilatancia, su RF-10 para axisimetría) y
  007 (control por desplazamiento y robustez de Newton con ablandamiento).
- Spec 022: el banco de ensayos (`ENSAYO-LAB`) y las trayectorias (`POST-TRAY`).
- Spec 019, solo para los subcasos no drenados de `VER-CNS-01` si se calculan con material no
  drenado (duda 5); spec 023, si el casquete se comparte (duda 8).

## Contexto y objetivo

En arenas la plasticidad empieza con la carga: el rozamiento movilizado crece con la deformación
plástica de corte hasta el de rotura y, en las densas, cae después. El modelo de endurecimiento y
ablandamiento del catálogo (`SH`, T07c §1) lo representa con un mecanismo de corte de tipo
Mohr-Coulomb con rozamiento movilizado, una ley de endurecimiento de un parámetro o tabulada, dos
potenciales y, opcionalmente, un casquete y un corte a tracción; se apoya en Pietruszczak (2010).
`VER-CNS-01`, el caso que cierra la fase junto a `VER-STR-13`, es entero de este modelo: siete
series de triaxiales de laboratorio sobre cinco arenas.

**Qué ya cubre la 008 y no se repite aquí**: el Mohr-Coulomb con resistencia residual y el
frágil-plástico (`MC-RES`: caída a residual tras la primera plastificación; `VER-STR-30`,
`EJ-SEE-02`). Aquí el ablandamiento es **gradual**, gobernado por la deformación plástica, que es
otra cosa: la ley tabulada de esta spec no sustituye a la caída instantánea de la 008 (duda 7).

## Usuarios / actores

- **El ingeniero de suelos granulares**, que quiere rigidez y dilatancia realistas antes de la rotura.
- **El investigador**, que ajusta la ley a sus ensayos y la compara con el laboratorio.
- **Los casos de validación**; **la 026**, cuyos modelos de endurecimiento por corte son de la misma
  familia (duda 9).

## Historias de usuario

- H1: Como ingeniero quiero dar el rozamiento de rotura, la dilatancia, la cohesión y un parámetro de
  endurecimiento, y obtener la curva de un triaxial drenado.
- H2: Como investigador quiero dar el rozamiento (y la cohesión) como tabla frente a la deformación
  plástica de corte, con rama descendente, para reproducir el pico y el ablandamiento de una arena
  densa.
- H3: Como ingeniero quiero saber, con el resultado, qué mecanismos estaban activos y qué valores
  movilizados tenía cada punto.

## Requisitos funcionales (EARS)

**Mecanismo de corte**

- RF-1: EL SISTEMA integra un mecanismo de corte de tipo Mohr-Coulomb con rozamiento (y cohesión, si
  la fuente lo admite) movilizados que evolucionan con la deformación plástica de corte, con la ley
  de un parámetro de la fuente o con una tabla (duda 3).
- RF-2: EL SISTEMA ofrece los dos potenciales del catálogo (dilatancia en rotura; compactación y
  dilatancia) con la definición de la fuente, y el ángulo correspondiente.
- RF-3: CUANDO la ley no endurece (parámetro en su límite o tabla constante) y no hay casquete,
  EL SISTEMA da el Mohr-Coulomb perfecto de la 008 a redondeo (identidad con dientes).
- RF-4: EL SISTEMA guarda por punto la deformación plástica de corte, los valores movilizados y el
  mecanismo activo, y los da como resultado (005).

**Casquete y tracción (según la duda 2)**

- RF-5: SI se decide incluirlos, EL SISTEMA añade el casquete (vertical o elíptico) con su ley de
  endurecimiento por la deformación volumétrica plástica y el corte a tracción de la 008, con el
  estado inicial del casquete definido y escrito con el resultado (regla 12).

**Ablandamiento y reglas transversales**

- RF-6: CUANDO un punto ablanda, EL SISTEMA lo marca; el resultado avisa de que en un problema de
  contorno la respuesta depende de la malla (el propio manual lo advierte, T07c §1.4), sin
  regularizarla en esta spec.
- RF-7: SI una tabla no está ordenada, tiene un solo punto o se sale de su dominio durante el
  cálculo, ENTONCES EL SISTEMA hace lo que se decida (duda 3) y lo dice; no extrapola en silencio.
- RF-8: La ley tiene su referencia en Python, su tangente comprobada contra la derivada numérica, su
  prueba en un punto de Gauss contra la fuente (regla 8), su identidad con Rust (ADR-0001) y un test
  de signo con las ecuaciones reescritas en tracción positiva (regla 10; T07c §1.8: el catálogo no
  declara su convenio y escribe el corte a tracción sobre σ3).
- RF-9: Cada opción (ley de un parámetro o tabla, potencial, casquete, tracción) lleva su test que
  mueve el número (regla 7); los textos pasan por `tr()` y las acciones están en un menú.

## Validación numérica

`VER-CNS-01` se reparte en sus siete series. Ninguna tiene solución cerrada: la referencia son
ensayos de laboratorio publicados, con parámetros que el manual **ajustó a las mismas curvas** y
sin módulo elástico ni Poisson en la ficha. Un ajuste no valida la integración (regla 1): eso lo
hacen la identidad de RF-3 y la prueba en un punto contra la fuente.

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-CNS-01` D1, Karlsruhe suelta, drenado, cinco confinamientos | Kolymbas y Wu (1990), experimental | σ1/σ3, q y εv frente a εa |
| `VER-CNS-01` D2, Karlsruhe densa, drenado, ocho confinamientos | Kolymbas y Wu (1990); la simulación por elementos discretos de Widulinski, Kozicki y Tejchman (2009) es otro modelo: **comparación** | q y εv frente a εa; a 200 kPa, σ1 y εv |
| `VER-CNS-01` D3, Ottawa C1 suelta, ley tabulada con ablandamiento | Alshibli y Sture (2000), experimental | Relación de tensiones, q y εv frente a εa; la tabla de la ficha está incompleta |
| `VER-CNS-01` D4, Hostun densa, ley tabulada y de un parámetro | Schanz y Vermeer (1996), experimental | q y εv frente a εa; las curvas del manual de otro programa no son referencia |
| `VER-CNS-01` D5, Hostun suelta | Schanz y Vermeer (1996), experimental | q y εv frente a εa |
| `VER-CNS-01` U1, Banding muy suelta, no drenado (licuefacción estática) | Castro (1969), recogido en Pietruszczak (2010) | q–εq, q–p′ y exceso de presión–εq; necesita la duda 5 |
| `VER-CNS-01` U2, Reid Bedford suelta, no drenado, dos confinamientos | Pietruszczak (2010) | q–p′, q–εq y exceso de presión–εq; necesita la duda 5 |
| Límite sin endurecimiento | Identidad (RF-3) | Igual al Mohr-Coulomb perfecto de la 008 y de la spec 001 |
| Punto material | La formulación de Pietruszczak (2010), si publica una trayectoria de referencia (por comprobar) | Superficie, flujo, endurecimiento y tangente frente a derivada numérica |
| Ensayo en un punto y con un elemento | Identidad (spec 022, RF-10) | Las mismas curvas |
| Regla 7 | — | Cada opción de RF-9 mueve el número |

Las series D4 y D5 (los ensayos de Schanz y Vermeer 1996) sirven también a la 026 como referencia
experimental de Hardening Soil. La tolerancia de cada serie se fija antes de medir, y la de una
curva experimental con parámetros ajustados no puede ser la de una solución cerrada.

## Fuentes por conseguir

- Pietruszczak (2010), *Fundamentals of Plasticity in Geomechanics*, CRC Press (T00 §5.A): la base
  de la formulación del modelo y del casquete de T07a §5. No está en la carpeta de bibliografía.
- Schanz y Vermeer (1996), *Géotechnique* 46(1), 145–151; Castro (1969), Harvard Soil Mechanics
  Series 81 (T00 §5.A). Kolymbas y Wu (1990), Alshibli y Sture (2000) y Widulinski, Kozicki y
  Tejchman (2009), solo con autor y año en la ficha: por completar.
- La definición de λ del casquete (con o sin el factor del volumen, T07c §1.8) y la interpolación de
  las tablas: de la fuente.
- Disponibles en `../Referencias/Bibliografia/`: de Souza Neto, Perić y Owen (2008), §8.2
  (Mohr-Coulomb, el retorno ya usado en la spec 001) y §10.2 (Drucker-Prager con casquete), para el
  retorno con varias superficies; no tratan este modelo.

## Requisitos no funcionales

- El motor recibe las tablas ya convertidas a sus unidades (regla 11); una tabla larga no debe hacer
  lenta la integración (A/B).

## Casos límite

- Parámetro de endurecimiento nulo o enorme; tabla con un tramo vertical (caída brusca) o con un
  rozamiento inicial nulo (la de Hostun densa empieza en 0°).
- Dilatancia igual al rozamiento; cohesión nula en un ensayo que pasa por tensión media cero (U1
  acaba en el origen de p′–q).
- Pico y ablandamiento dentro de un escalón; inversión de carga tras el pico.
- Esquina entre el corte y el casquete, y entre el corte y la tracción.

## Fuera de alcance

- El Mohr-Coulomb residual y frágil-plástico (008); las leyes de junta con ablandamiento (015).
- La regularización del ablandamiento y la localización en bandas de corte.
- Los modelos de endurecimiento de T07b §2 y §3 con fuente solo comercial (026, duda 9).
- La reducción de resistencia con esta ley (duda 10).

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Todos los RF con su test en verde, y la regla 7 en cada opción nueva
- [ ] La ley probada en un punto de Gauss contra su fuente, con identidad Python–Rust y la de RF-3
- [ ] Las series de `VER-CNS-01` que se decidan, dentro de la tolerancia fijada antes de medir
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. Fuente de la formulación**: el manual se apoya en Pietruszczak (2010)
  sin dar el algoritmo (T07c §1.4) y con ecuaciones de convenio dudoso (§1.8: el coeficiente del
  potencial escrito de dos formas; el vértice con la cohesión movilizada). Sin el libro, no entra.
- [NECESITA ACLARACIÓN] **2. Qué mecanismos**: `VER-CNS-01` solo usa el de corte (T07c §1.6). El
  casquete y la tracción no los pide ningún caso; con ellos hay opciones sin validar (regla 7).
  Opciones: (a) solo el de corte; (b) los tres, con un ensayo edométrico propio contra la fuente.
- [NECESITA ACLARACIÓN] **3. Ley tabulada**: interpolación entre puntos y fuera del rango (no
  documentado); si la cohesión también se tabula; cómo se mezcla con la ley de un parámetro.
- [NECESITA ACLARACIÓN] **4. Datos de `VER-CNS-01`**: faltan el módulo elástico y el Poisson de todas
  las series, el parámetro de la variante de un parámetro de D4 y las filas de las tablas que no se
  ven en el manual (D3: 14 visibles; D4: 12). T07c §1.3 da E y ν para los ensayos de Hostun de su
  propio ejemplo. Opciones: (a) completar con esas lecturas, declaradas; (b) calibrar nosotros y
  llamarlo ajuste; (c) dejar fuera las series sin datos.
- [NECESITA ACLARACIÓN] **5. Ensayos no drenados** (U1, U2): el manual impone volumen constante con
  desplazamientos y no explica cómo saca el exceso de presión. Opciones: (a) volumen constante en el
  banco de la 022 y el exceso a partir de la presión de célula constante, con tensión efectiva de
  Terzaghi (010); (b) material no drenado de la 019. Los incrementos de la ficha llegan al 1.8 % de
  deformación axial y las figuras al 20 % de corte: el escalado de cada ensayo no está documentado.
- [NECESITA ACLARACIÓN] **6. Ángulo de Lode**: la superficie de corte se escribe en p, q y θ; el
  catálogo no define θ (T07c, convenciones). Se fija con la fuente y con la 008.
- [NECESITA ACLARACIÓN] **7. Relación con `MC-RES` de la 008**: ¿una tabla con caída vertical puede
  representar el frágil-plástico? Se propone que no: cada ley con su caso (`VER-STR-30` en la 008).
- [NECESITA ACLARACIÓN] **8. Mohr-Coulomb con casquete** (T07a §5, Pietruszczak 2010): mismo
  casquete que esta ley y que Cam-Clay (023, duda 11), sin endurecimiento de corte y sin caso. ¿Entra
  aquí como variante, o se deja hasta que un caso lo pida?
- [NECESITA ACLARACIÓN] **9. Frontera con la 026**: los modelos de T07b §2 y §3 tienen el mismo
  mecanismo de rozamiento movilizado (el catálogo aconseja implementarlos juntos), pero solo citan un
  manual comercial. Se dejan en la 026 con su aviso; si aparece la fuente, ¿se traen aquí?
- [NECESITA ACLARACIÓN] **10. Reducción de resistencia**: ¿qué se reduce (rozamiento de rotura,
  tabla entera, cohesión)? Ningún caso del índice la pide con esta ley.
- [NECESITA ACLARACIÓN] **11. Ángulo de rotura de Hostun densa**: la tabla 1 de la ficha da 30°
  (menos que la suelta, 35°), la tabla del mismo ensayo sube a 40–45° y el ejemplo de T07c §1.3 da
  43.5°. Posible errata del manual; se usa lo que diga Schanz y Vermeer (1996).

La referencia T00 y las T07 son de la carpeta C del análisis de interfaz
(`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/C_teoria/`).
