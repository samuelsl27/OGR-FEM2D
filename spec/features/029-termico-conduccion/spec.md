# Spec 029 — Conducción de calor

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 7 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Fase 7 — Campos especiales»: térmico, «conducción y
> después acoplamientos»). Solo el **qué** y el **porqué**, sin fórmulas ni decisiones tomadas.
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
      - `ogr_core/fem/seepage.py`, `SeepageSolver`: difusión escalar estacionaria sobre T3, tensor
        anisótropo por material, matriz elemental en forma cerrada, Dirichlet por eliminación,
        caudal nodal y reparto de un caudal por segmento a sus dos nudos, solver disperso con
        reutilización de la factorización, aviso de problema singular y de elementos planos.
      - `TransientSeepageSolver` (mismo módulo): Euler implícito, almacenamiento concentrado (un
        tercio del área de cada T3 a cada nudo), etapas `TransientStage` con su tiempo y sus
        condiciones, campo inicial dado (`initial_head`) o estacionario, número de pasos automático
        (`_auto_time_steps`) y balance por etapa (`stored_water`).
      - **Lo que le faltaría para el calor, visto y sin decidir**: la condición de convección
        (mixta: un término en la matriz y otro en el segundo miembro; `BCType` no la tiene); la
        fuente interna; una capacidad propia por material en lugar de la del agua (pendiente de la
        retención y almacenamiento específico, `hydraulic/hydraulic_properties.py`); una incógnita
        sin la cota (el solver trabaja en altura total y sus condiciones de presión, presión nula y
        rezume no tienen sentido térmico); conductividad que dependa de la temperatura (hoy solo
        `kr` por succión, con su Picard); T6 y axisimetría, que tampoco tiene (017, duda 2).
      - `ogr_core/fem/mesh.py` (malla propia, solo T3), `fem/streamlines.py` (líneas de flujo en
        T3) y `flux_through_segment` (sección **recta**): el equivalente de una sección de
        transferencia de calor. El mallador de aquí (`ogr_fem2d/mesh/`) no da un `ogr_core.fem.Mesh`
        (017, duda 1).
      - Aquí: `ogr_fem2d/engine/` (motor tensional sin tiempo, `docs/motor/entrada.md`), y lo que
        dejen las specs 017, 018 y 028 sobre etapas, pasos de tiempo, funciones del tiempo e
        historias.
      - Lo observado: nada; la versión observada no tenía térmico (carpeta B,
        `modelo/M25_termico.md`, todas sus secciones de la versión actual; `M04b`, página térmica;
        `M13`; `compute_interpret/I05`). Teoría: `C_teoria/T12` (bloques A, F, H, K); erratas en
        `T00` §3.3.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Specs 002 y 003 (motor, malla T3 y T6, refinamiento local) y `004-modelo-y-proyecto`
  (propiedades por material, condiciones por segmento, vértice o nudo y por fase, **tiempo de
  fase**, valores por defecto a la vista; su duda 5, malla dada).
- Specs `005-resultados` (magnitudes por instante, `POST-LINEA`, `POST-HIST`, `.h5`) y
  `006-interfaz-y-calculo` (menú, cálculo en subproceso cancelable).
- Specs 017 y 018: el solver de difusión del núcleo, la malla del flujo frente a la tensional, las
  etapas, el esquema y los pasos de tiempo (018, dudas 5, 7 y 9). Lo que decidan para el agua
  decide aquí lo mismo o lo contrario a propósito.
- Spec 028 (funciones del tiempo, `C-TIEMPO`, e historias en puntos), si llega antes.

## Contexto y objetivo

La temperatura es un campo nuevo: escalar, sin desplazamientos, con conducción estacionaria
(`TER-COND`, 6 casos) y transitoria (`TER-TRANS`, 18). Matemáticamente es un problema de difusión,
el mismo que el flujo de agua transitorio que ya resuelve el núcleo, con otra capacidad y otras
condiciones: temperatura, flujo, convección hacia un medio (`TER-CONV`, 3) y fuentes internas
(`TER-FUENTE`, 1). Faltan también la condición inicial de temperatura (`OTRO`: VER-THM-02 y -10) y
la conductividad que depende del estado (`TER-K`, 6), aquí solo en lo que no exige acoplamiento.
T12 §1.7 propone escalonar el térmico y da a este primer escalón dificultad media. Esta spec es ese
escalón; el cambio de fase, el agua, la mecánica y los contornos especiales son la 030.

## Usuarios / actores

- **Ingeniero de cimentaciones, conducciones y obras en terreno helado**, que necesita el campo de
  temperaturas antes de cualquier acoplamiento.
- **La spec 030**, que pone encima el cambio de fase, la advección y la deformación térmica.
- **Investigadora y docente**, que contrastan con las soluciones clásicas de conducción.

## Historias de usuario

- H1: Como ingeniero quiero imponer temperaturas, flujos y convección sobre los contornos dibujados,
  por fase, y que sobrevivan a un nuevo mallado.
- H2: Como ingeniero quiero dar a cada material su conductividad (también anisótropa o en tabla con
  la temperatura) y su capacidad calorífica, y ver con el resultado cuáles tomé por defecto.
- H3: Como ingeniero quiero un transitorio por etapas desde una temperatura inicial dada (uniforme,
  por material, con gradiente o por rejilla) y ver las isotermas, perfiles e historias.
- H4: Como investigadora quiero comprobar la placa, la barra semiinfinita y la superficie convectiva
  contra su solución cerrada, con la malla y el paso de tiempo fijados.

## Requisitos funcionales (EARS)

**Conducción**

- RF-1: EL SISTEMA resuelve la conducción estacionaria y la transitoria en deformación plana y en
  axisimetría, con conductividad isótropa o anisótropa por material, según la duda 1.
- RF-2: EL SISTEMA admite conductividad constante o dada por tabla frente a la temperatura; SI la
  iteración que eso exige no converge, ENTONCES lo dice con su historia y su tolerancia, y no da el
  campo como válido.
- RF-3: EL SISTEMA admite fuentes internas de calor por región, constantes o función del tiempo,
  según la duda 7.

**Contornos y condición inicial**

- RF-4: EL SISTEMA admite temperatura impuesta, flujo por segmento, flujo nodal y convección (un
  coeficiente y la temperatura del medio), constantes o función del tiempo, por segmento, vértice o
  nudo y por fase; un contorno sin condición es adiabático, y eso se dice con el resultado (regla
  12).
- RF-5: EL SISTEMA admite una temperatura impuesta que varía a lo largo de un contorno (VER-THM-02),
  según la duda 5.
- RF-6: SI en un estacionario ninguna condición fija el nivel de temperatura (ni temperatura ni
  convección), ENTONCES EL SISTEMA no calcula y lo dice.
- RF-7: EL SISTEMA parte de la condición inicial que se decida (duda 4) y la muestra con el
  resultado; la primera etapa de un transitorio no se calcula sin ella.

**Tiempo**

- RF-8: EL SISTEMA integra el transitorio por etapas con su tiempo y da con el resultado el esquema,
  los pasos usados en cada etapa y el balance de energía por etapa; el paso, como la malla, lo fija
  cada caso (reglas 9 y 12; duda 9).
- RF-9: CUANDO el paso es menor que la cota que da la fuente para evitar oscilaciones (Bergheau y
  Fortunier 2008, en T12, por comprobar), EL SISTEMA lo avisa; no lo cambia sin decirlo.

**Resultados**

- RF-10: EL SISTEMA da temperatura en nudos y puntos de integración, gradiente y flujo de calor por
  elemento, isotermas, perfiles por línea, historias en puntos declarados y el flujo integrado a
  través de una sección (duda 15).

**Motor y reglas transversales**

- RF-11: El solver térmico recibe nudos, elementos, conductividades, capacidades, fuentes y
  condiciones discretas por nudo y lado; no sabe de contornos, menús ni unidades de usuario (regla
  11). Si va en el motor de este programa, con su referencia en Python como oráculo de Rust
  (ADR-0001).
- RF-12: Un único convenio de signo del flujo de calor, documentado y convertido en un único sitio
  (regla 10; duda 11).
- RF-13: Cada opción nueva (esquema, pasos, masa concentrada o consistente, tolerancia de k(T),
  condición por defecto del contorno, temperatura inicial por defecto) lleva su test que mueve el
  número (regla 7) y su valor a la vista con el resultado (regla 12); los textos pasan por `tr()` y
  las acciones están en un menú (reglas 2 y 3; duda 14).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-THM-01`, placa cuadrada estacionaria | Nithiarasu y Lewis (2012), ej. 5.2.1: ensamblaje a mano de 8 T3 y serie de Fourier | T en el centro: con la malla de 8 T3, el valor del ensamblaje a mano a redondeo (identidad); con malla fina, la serie; isotermas (duda 3) |
| `VER-THM-03`, barra semiinfinita con flujo en el extremo | Nithiarasu y Lewis (2012), ej. 6.4.2 | Perfil de temperatura en t = 1 (la ficha da el flujo en W/m: unidad por comprobar) |
| `VER-THM-04`, superficie convectiva en un medio semiinfinito | Carslaw y Jaeger (la ficha cita 1986; la expresión la aporta la ficha, no el manual) | Temperatura de la superficie frente al tiempo durante un día |
| `VER-THM-02`, franja calentada sobre permafrost | Solo otro programa | **Comparación**, no validación; contornos lateral e inferior sin documentar o ilegibles en la ficha |
| Conducción 1D estacionaria | — (identidad) | Perfil lineal exacto a redondeo, también con tensor anisótropo y girado, en T3 y T6 |
| Analogía con el agua | — (identidad) | El mismo problema escrito como flujo de agua (conductividad como permeabilidad, capacidad como almacenamiento) da el mismo campo que el solver del núcleo |
| Convección extrema | — (identidad) | Coeficiente nulo: adiabático; coeficiente muy grande: tiende a la temperatura impuesta |
| Transitorio largo | — (identidad) | Con condiciones fijas, tiende al estacionario |
| Balance de energía | — (identidad) | Calor almacenado en cada etapa igual al flujo neto por el contorno más las fuentes |
| Axisimetría | — (identidad) | Un cilindro hueco con temperaturas fijas da el perfil que la fuente dé por exacto |
| Conductividad en tabla | — (identidad) | Una tabla constante da lo mismo que la constante; una variable mueve el número (regla 7) |
| Convergencia en malla y en tiempo | — | Tres mallas y tres pasos: el error baja; la tolerancia, con los elegidos (regla 9) |
| Referencia y Rust | — (identidad) | Mismos campos hasta el redondeo, si va al motor (ADR-0001) |

Se proponen como los que la cierran **THM-01, THM-03 y THM-04** (analíticos, solo conducción).
Ningún `EJ-THM` cabe aquí: todos piden cambio de fase o acoplamiento (030).

## Fuentes por conseguir

- `Referencias/Bibliografia` no tiene ninguna fuente térmica (`00_LEEME.md`, 2026-11-22). Sí está
  Zienkiewicz y Taylor (2000), vol. 1: su buscador encuentra la conducción de calor en el cap. 3 y
  en el cap. 17 (PDF, págs. ≈57–89 y ≈500–521); por leer si basta para la formulación de Galerkin y
  la semidiscretización en el tiempo.
- La formulación que cita T12: Lewis, Nithiarasu y Seetharamu (2004). Las fichas THM-01 y -03
  citan Nithiarasu y Lewis (2012): por comprobar si es otra edición de la misma obra.
- Carslaw y Jaeger, *Conduction of Heat in Solids*: la ficha de THM-04 cita 1986; la edición que
  suele citarse es la 2.ª, de 1959 (por comprobar cuál es la reimpresión).
- Bergheau y Fortunier (2008), la cota del paso de tiempo (nombre del primer autor incompleto en
  T12).
- Si entran: la regla de la convección en un nudo con perímetro (T12 no explica cómo se usa) y el
  convenio del flujo de contorno (T12: «hacia fuera del modelo», sin convenio general).

## Requisitos no funcionales

- Unidades térmicas convertidas en un único sitio: las fichas mezclan W, kW, kJ/s, J/m³/°C,
  kJ/m³/°C y kJ/t/°C; temperatura en °C (la 030 necesitará kelvin en un sitio).
- Un transitorio largo se puede cancelar (006) y no recalcula lo que no cambia.
- Si se pide algo al núcleo, Slip2D sigue bit a bit.

## Casos límite

- Estacionario solo con flujos y convección nula (singular); todo adiabático en transitorio.
- Paso de tiempo muy pequeño frente a la cota de RF-9; una etapa de duración nula.
- Contraste fuerte de conductividades entre materiales; anisotropía extrema; capacidad nula.
- Nudo en el eje en axisimetría; un contorno de temperatura y otro de convección en el mismo nudo.
- Región excavada en una fase (spec 012): qué contorno queda y con qué condición.

## Fuera de alcance

- Todo lo de la spec 030: calor latente y agua no congelada, conductividades que dependen de la
  saturación o del estado helado (salvo lo que decida la duda 8), advección, convección natural,
  bloqueo de poros por hielo, deformación térmica, balance energético superficial, termosifones,
  aislamiento de juntas, propiedades térmicas de revestimientos.
- Radiación como contorno propio; dispersividad térmica (necesita las velocidades del agua).
- Térmico con dinámico, XFEM o consolidación.

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Todos los RF con su test en verde, y la regla 7 en cada opción nueva
- [ ] Los casos que la cierran dentro de tolerancia, con su malla, su elemento y su paso fijados
- [ ] Las identidades de la tabla, en verde y con dientes
- [ ] Referencia en Python y Rust con su identidad, si va al motor; lo pedido a OGR-Core, en una
      versión etiquetada y fijada aquí
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. Dónde vive el solver.** (a) Generalizar en OGR-Core el solver de
  difusión escalar, del que agua y calor serían dos casos (petición, con Slip2D bit a bit); (b) un
  adaptador aquí que escribe el calor como agua, sin convección ni fuente, que es rodear el núcleo;
  (c) un solver térmico en el motor de este programa (Rust y su referencia), que daría T6 y
  axisimetría; (d) otra.
- [NECESITA ACLARACIÓN] **2. Malla térmica y tensional**: la misma pregunta que la duda 1 de la 017.
  THM-01 usa T3 y THM-02 T6; la 030 necesita la temperatura en los puntos de integración del motor.
- [NECESITA ACLARACIÓN] **3. La malla de 8 T3 de THM-01** (diagonales orientadas): el mallador no
  la hace; es la duda 5 de la 004 (malla dada en el `.ogr`). Sin ella, THM-01 solo vale con malla
  fina frente a la serie.
- [NECESITA ACLARACIÓN] **4. Condición inicial** (`OTRO`): uniforme, por material, con gradiente con
  la profundidad (THM-02), por rejilla con los interpoladores del núcleo (THM-10), o el estacionario
  previo; ¿y cuál por defecto? La referencia tiene además un modo sin transferencia de calor que
  conserva la temperatura inicial, útil para la 030 (deformación térmica con temperatura dada).
- [NECESITA ACLARACIÓN] **5. Temperatura que varía a lo largo de un contorno** (THM-02): lineal
  entre dos valores, por cota o por tabla. El núcleo tampoco la tiene para la altura (017).
- [NECESITA ACLARACIÓN] **6. Funciones del tiempo**: tabla, sinusoidal (la referencia no da su
  forma), escalón. Las piden también la 018, la 019 y la 028: ¿quién las define primero?
- [NECESITA ACLARACIÓN] **7. Fuentes internas** (`TER-FUENTE`): su único caso, EJ-THM-06, mete el
  calor como flujo variable sobre el contorno de la excavación, no como fuente interna. ¿Entra la
  fuente interna sin caso, con una identidad, o queda fuera?
- [NECESITA ACLARACIÓN] **8. La frontera de `TER-K` con la 030.** Aquí: constante, anisótropa y en
  tabla con la temperatura. Las leyes de Johansen, Côté y Konrad y las demás dependen de la
  saturación y del estado helado. Opciones: (a) todas en la 030; (b) aquí como funciones puras,
  probadas en un punto (regla 8) con la saturación como dato, y su uso acoplado en la 030 (THM-11 y
  -12 comparan justo conductividad frente a saturación). Y la conductividad «constante» con valor
  helado y no helado que conmuta en la temperatura de congelación: ¿aquí o en la 030?
- [NECESITA ACLARACIÓN] **9. Esquema y pasos**: Euler implícito como el núcleo y como describe T12;
  masa concentrada (el núcleo) o consistente (la forma que escribe T12), que cambia el número cerca
  de los frentes; pasos fijos o automáticos; ¿se avisa o se impide bajo la cota de RF-9?
- [NECESITA ACLARACIÓN] **10. Unidades térmicas**: ¿las añade el núcleo (`units/unit_system.py`,
  petición) o se convierten aquí? ¿En qué unidades recibe el solver?
- [NECESITA ACLARACIÓN] **11. Convenio del flujo** (regla 10): entrante o saliente positivo. T12
  describe el flujo de contorno como saliente; THM-03 aplica un flujo que entra. Hay que mirar
  también el convenio del caudal en el núcleo, para que agua y calor no tengan dos.
- [NECESITA ACLARACIÓN] **12. Convección en un nudo** (EJ-THM-01: tubos de congelación como nudos
  con perímetro): ¿se admite, con qué fuente, o solo por segmento?
- [NECESITA ACLARACIÓN] **13. Casos de cierre.** El plan solo dice «THM» para la fase. ¿Se aprueban
  THM-01, -03 y -04?
- [NECESITA ACLARACIÓN] **14. Menú**: la 006 no tiene menú térmico; la versión actual de la
  referencia tiene uno propio (carpeta B, M25 §7). ¿Uno propio o repartido entre Análisis,
  Propiedades y Contornos?
- [NECESITA ACLARACIÓN] **15. Sección de transferencia de calor**: la del núcleo es recta; ¿basta, o
  poligonal como pide la 017 para el agua (P17)?

Las referencias T00 y T12 son de la carpeta C del análisis de interfaz
(`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/C_teoria/`); M04b, M13, M25 e I05, de la
carpeta B (`modelo/` y `compute_interpret/`); P17, de la carpeta A (`reproducciones/`).
