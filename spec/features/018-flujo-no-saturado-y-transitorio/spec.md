# Spec 018 — No saturado y transitorio

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 4 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 018 — No saturado y transitorio»). Solo el
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
      - `ogr_core/fem/seepage.py`: `UnsaturatedSeepageSolver` (k(ψ) por Picard con subrelajación;
        si no converge, aceleración de Anderson y continuación con Newton); `TransientSeepageSolver`
        (ecuación de Richards en forma mixta, Euler implícito, Picard modificado de Celia, Bouloutas
        y Zarba 1990, almacenamiento concentrado, almacenamiento específico bajo el nivel freático;
        etapas `TransientStage` con su tiempo y sus condiciones; campo inicial dado,
        `initial_head`, o estacionario; número de pasos automático, `_auto_time_steps`; balance de
        masa por etapa, `stored_water`).
      - `ogr_core/hydraulic/permeability_models.py`: constante, *Simple* (convención de OGR sin
        fuente, D190), Brooks y Corey (1964), Fredlund y Xing (1994), Gardner en forma racional,
        van Genuchten (1980) y tabla; cada uno en su unidad de succión (altura o kPa, v0.1.200).
        **No tiene la forma exponencial** de la conductividad que usa la solución de GW-14.
      - `ogr_core/hydraulic/hydraulic_properties.py`: **una sola curva de retención, la de van
        Genuchten, para todos los modelos** (convención de OGR, D191); su α por defecto,
        0.036 1/m, se eligió porque reproducía mejor los transitorios publicados de los problemas
        17 y 18 del banco de filtración de Slip2D (`retention_alpha`); θs, θr y almacenamiento
        específico con defecto propio. `water_content`, `specific_moisture_capacity`,
        `storage_content`.
      - Resistencia no saturada **de equilibrio límite** (φb de Fredlund, con el tope de succión de
        la spec 005 de Slip2D) en `ogr_core/materials/` y `hydraulic/pore_pressure.py`. **No hay**
        tensión efectiva no saturada para elementos finitos (ningún método de χ).
      - **Lo que no tiene, visto**: axisimetría y T6 (como en la 017); funciones del tiempo
        continuas (solo etapas); condición inicial por material (la referencia ofrece seco,
        presión, Ru, rejilla o interpolada, M24 §9); el coeficiente mv de las fichas como dato (el
        núcleo pide almacenamiento específico).
      - Evidencia del solver: en OGR-Core, `tests/test_transient_celia_v1268.py` (Celia et al.
        1990: posición del frente y balance de masa), `test_transient_face_rule_v1274.py`,
        `test_transient_carried_state_v1282.py`, `test_picard_steep_curve_v1266.py`,
        `test_unsaturated_v127.py` (formas y límites de cada k(ψ)); en Slip2D,
        `tests/test_transient_v130.py`, `test_transient_coupling_v1125.py` y su spec
        `005-filtracion-transitoria-acoplada` (problema 102, aquí VER-SLP-120: cuatro factores
        permanentes publicados como criterio; los 22 intermedios, como medición, porque no se
        publican ks, θ(ψ) ni Ss).
      - Aquí: lo que deje la 017.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 017: flujo estacionario, condiciones de contorno, presiones en el análisis tensional y la
  malla del flujo (su duda 1). La frontera entre las dos se discute en su duda 4.
- Spec `004-modelo-y-proyecto`: el **tiempo** de cada fase (hoy una fase no tiene tiempo).
- Specs 008, 009 y `010-presiones-hidrostaticas`: tensión efectiva, SSR por instante, convenio.
- Spec `005-resultados`: magnitudes por instante (`POST-HIST`, `POST-LINEA`) y su `.h5`.

## Contexto y objetivo

Sobre el flujo estacionario saturado de la 017 faltan tres cosas. La **zona no saturada**: la
permeabilidad cae con la succión y el agua retenida depende de ella (`FLU-NOSAT`, 30 casos). El
**tiempo**: almacenamiento, condiciones que cambian por etapa, lluvia, un estado inicial impuesto
(`FLU-TRANS`, 20; `CC-Q`, 10; condición inicial impuesta, en `OTRO`: GW-17 y GW-18). Y la
**succión en la resistencia**: la tensión efectiva no saturada (`UNSAT-MEC`, 7). El núcleo tiene las
dos primeras, validadas en Slip2D; la tercera no existe en elementos finitos. El plan no da casos de
cierre propios para esta spec: los de la fase son de la 017 y de la 019.

## Usuarios / actores

- **Ingeniero de taludes con lluvia, presas con llenado o desembalse y columnas de laboratorio.**
- **El SSR de la 009**, que se calcula en instantes elegidos de un transitorio.
- **OGR Slip2D**, que comparte el solver y sus convenciones a través del núcleo.

## Historias de usuario

- H1: Como ingeniero quiero elegir la función de permeabilidad y la curva de retención de cada
  material, con su gráfica, para representar un suelo no saturado.
- H2: Como ingeniero quiero definir etapas con su tiempo y sus condiciones (lluvia, subida o bajada
  del embalse) y ver cómo evolucionan las presiones.
- H3: Como ingeniero quiero imponer un campo de presiones inicial, para estudiar su disipación.
- H4: Como ingeniero quiero que la succión aumente la resistencia solo con el método que elija, y
  ver ese método con el resultado.

## Requisitos funcionales (EARS)

**No saturado**

- RF-1: EL SISTEMA ofrece las funciones de permeabilidad del núcleo, cada una con su fuente, y la
  curva de retención que se decida (duda 2), con sus parámetros, unidades y gráfica.
- RF-2: EL SISTEMA muestra con el resultado el modelo, la curva de retención y cada parámetro
  tomado por defecto (regla 12), y el defecto ajustado del núcleo se dice como tal (duda 2).
- RF-3: SI la iteración no lineal no converge, ENTONCES EL SISTEMA lo dice con su historia, como en
  la 017, RF-6.

**Transitorio**

- RF-4: EL SISTEMA resuelve el flujo transitorio con el solver del núcleo, por etapas con su tiempo
  y sus condiciones, desde un campo inicial estacionario, dado o impuesto por material (duda 5).
- RF-5: EL SISTEMA da los pasos de tiempo usados en cada etapa y el error del balance de masa con el
  resultado; el paso, como la malla, lo fija cada caso (reglas 9 y 12).
- RF-6: EL SISTEMA admite caudal e infiltración por etapa (`CC-Q`) y las condiciones de la 017 en
  cada etapa; SI una condición cambia dentro de una etapa, ENTONCES según la duda 7.
- RF-7: CUANDO se pide, EL SISTEMA calcula el análisis tensional o el SSR en los instantes elegidos,
  con las presiones de ese instante fijas durante el SSR (009, RF-7).

**Tensión efectiva no saturada**

- RF-8: EL SISTEMA calcula la tensión efectiva con succión por el método que elija el usuario (los
  que pida un caso, cada uno con su fuente original) o, aparte, la resistencia no saturada de
  Mohr-Coulomb; nunca los dos sumados sin que el usuario lo vea (duda 8).
- RF-9: El convenio de la succión y de la presión negativa es el de la 010 y la 017, en un único
  sitio (regla 10).

**Reglas transversales**

- RF-10: Cada parámetro y opción nuevos (α, n y m de la retención, θs, θr, almacenamiento, esquema y
  número de pasos, método de χ, tope de succión) llevan su test que mueve el número (regla 7); los
  textos pasan por `tr()` y las acciones están en el menú *Agua* (reglas 2 y 3).
- RF-11: Cada ley nueva (retención, χ) se prueba en un punto contra su fuente antes de usarse en un
  modelo (regla 8), con su oráculo en Python si va al motor (ADR-0001).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-GW-14`, columna no saturada estacionaria | Gardner (1958; la ficha da 1958 y 1959) | Altura de presión en la columna, infiltración y exfiltración (duda 3) |
| `VER-GW-23`, acuífero confinado transitorio | Ferris, en Tao y Xi (2006) | Altura frente a x en los instantes de la ficha (unidades imperiales) |
| `VER-GW-17`, disipación de un exceso uniforme | Terzaghi, en Lambe y Whitman (1979) | Isócronas de presión; necesita la condición inicial impuesta |
| `VER-GW-18`, disipación en suelo estratificado | Pyrah (1996) | Isócronas con dos materiales del mismo cv |
| Infiltración en columna (test del núcleo) | Celia, Bouloutas y Zarba (1990) | Frente de humedad y balance de masa (evidencia del solver) |
| `VER-GW-10`, flujo libre con van Genuchten | Clement et al. (1996); Dupuit como aproximación | Caudal y freática para cuatro niveles aguas abajo |
| `VER-GW-06`, `-07`, `-20`, `-21`, `-22` | Lam y Fredlund (1984) y Fredlund y Rahardjo (1993), resultados numéricos | Alturas en líneas y caudales |
| `VER-GW-08`, zanja con lluvia | Gureghian (1981), numérica | Caudales |
| `VER-CON-09`, tensión efectiva no saturada | Bishop (1959) y el χ de cada método (Gudehus 1995, Khalili et al. 2004, Bolzon et al. 1996, Aitchison, Kohgo et al. 1993) | Perfil de tensión efectiva vertical |
| `VER-CON-11`, pesos según el estado | Bishop (1959) | Tensiones vertical total y efectiva |
| `VER-SLP-67`, presa en transitorio | Huang y Jia (2009), equilibrio límite y SSR publicados | Factor por instante |
| `VER-SLP-120`, desembalse rápido | Factores de equilibrio límite publicados en estado permanente (los que usó la spec 005 de Slip2D) | Factor en los estados permanentes, no en los intermedios |
| Transitorio largo frente a estacionario | Identidad | Con condiciones fijas, el transitorio tiende al estacionario de la 017 |
| Almacenamiento nulo en saturado | Identidad (por comprobar en la fuente) | Mismo campo que el estacionario en cada etapa |
| Regla 7 | — | Cada opción de RF-10 mueve el número |

Se proponen como los que la cierran **GW-14**, **GW-23** y **GW-17** (analíticas) y **CON-09** para
la tensión efectiva no saturada. GW-05, GW-09, GW-11 y GW-19 solo tienen otro programa como
referencia: serían comparaciones.

## Fuentes por conseguir

- Ninguna de agua en `Referencias/Bibliografia`.
- Funciones hidráulicas: van Genuchten (1980), Fredlund y Xing (1994), Brooks y Corey (1964),
  Gardner (1958), que cita el núcleo y no T11 (el manual de flujo no define las funciones, T11
  §1.3). El núcleo fecha a Gardner en 1958 y en 1956 en el mismo módulo; la ficha de GW-11, en
  1956. Mualem, si la permeabilidad de van Genuchten se deriva de él (por comprobar).
- Transitorio: Fredlund y Rahardjo (1993); Celia, Bouloutas y Zarba (1990); Lewis y Schrefler,
  citado incompleto en T11 §1.
- Tensión efectiva no saturada: Bishop (1959), Khalili et al. (2004), Gudehus (1995), Bolzon et
  al. (1996), Kohgo et al. (1993), Aitchison (T11 §3 lo fecha en 1961; la ficha de CON-09, en
  1960; T11 dice que su expresión impresa no se puede interpretar sin la fuente); resistencia:
  Fredlund, Morgenstern y Widger (1978) y Vanapalli et al. (1996).
- Las de los casos: Ferris (en Tao y Xi 2006), Lambe y Whitman (1979), Pyrah (1996), Clement et
  al. (1996), Gureghian (1981), Lam y Fredlund (1984), Huang y Jia (2009).
- La relación entre el mv de las fichas y el almacenamiento específico del núcleo, con su fuente.

## Requisitos no funcionales

- Un transitorio largo (EJ-UNS-01: cinco años y doce días de lluvia horaria) termina en un tiempo
  razonable y se puede cancelar (006).
- Unidades de tiempo del proyecto (s, h, días; GW-23 en pies y horas), convertidas en un sitio.
- Slip2D sigue bit a bit con lo que se pida al núcleo.

## Casos límite

- Succión enorme en una capa seca; k(ψ) muy pendiente (arenas); kr mínimo alcanzado.
- Etapa de duración nula; etapa con un solo paso; frente de humedad más fino que la malla.
- Toda la columna saturada (el almacenamiento solo es el específico); toda seca.
- Una presión inicial impuesta incompatible con las condiciones de la primera etapa.
- χ fuera de [0, 1] por datos de tabla; saturación residual igual a la saturada.

## Fuera de alcance

- Consolidación acoplada y no drenado (019); el almacenamiento derivado de la elasticidad, según
  la duda 6.
- Histéresis de la retención, aire como fase propia y modelos con succión (Barcelona, sin fuente en
  T11 §3); hielo y acoplamiento térmico (fase 7).
- Condición inicial impuesta de velocidad o de temperatura (`OTRO` en DYN-02, THM-02, THM-10).
- Lluvia con datos climáticos y balance superficial (`TER-SEB`).

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Todos los RF con su test en verde, y la regla 7 en cada opción nueva
- [ ] Cada función hidráulica y cada χ, probados en un punto contra su fuente (regla 8)
- [ ] Los casos que la cierran dentro de tolerancia, con su malla y su paso de tiempo fijados
- [ ] Lo pedido a OGR-Core, en una versión etiquetada y fijada aquí
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. Casos de cierre.** El plan no da ninguno a esta spec. Los propuestos
  arriba (GW-14, GW-23, GW-17, CON-09) son analíticos; ¿se aprueban, u otros?
- [NECESITA ACLARACIÓN] **2. La curva de retención y su defecto.** El núcleo usa la de van Genuchten
  para todos los modelos y un α elegido por ajuste a unos transitorios publicados. Un defecto
  ajustado a un caso no puede validar ese caso (regla 1) y cambia el resultado (regla 12). Opciones:
  (a) adoptar la convención del núcleo, a la vista; (b) una retención por modelo con su fuente,
  pedida a OGR-Core; (c) que el usuario dé siempre la curva. Antes, comprobar si los problemas 17 y
  18 de Slip2D son los VER-GW-17 y -18 de aquí (aquí son disipaciones saturadas).
- [NECESITA ACLARACIÓN] **3. La forma exponencial de Gardner** que pide GW-14: (a) pedirla a
  OGR-Core con su fuente; (b) aproximarla con una tabla, y el caso sería otro; (c) dejar GW-14.
- [NECESITA ACLARACIÓN] **4. Modelo de permeabilidad por defecto**: el núcleo, constante; la
  referencia, *Simple* (P08), que el núcleo imita con números propios sin fuente. ¿Cuál, o ninguno?
- [NECESITA ACLARACIÓN] **5. Condición inicial** (`OTRO`, GW-17 y GW-18): campo dado, estacionario
  de la 017 o por material como la referencia (seco, presión, Ru, rejilla, interpolada); ¿y cuál por
  defecto?
- [NECESITA ACLARACIÓN] **6. Almacenamiento derivado de la elasticidad** (consolidación desacoplada:
  CON-07, CON-08, el modelo desacoplado de CON-10 y los enfoques 2a y 3a de STR-32). T11 §1 da tres
  variantes, una con un factor sin derivar. ¿Aquí o en la 019?
- [NECESITA ACLARACIÓN] **7. Condiciones en el tiempo**: solo por etapas, como el núcleo y lo único
  que documenta la referencia para el agua (M24 §13), o funciones del tiempo dentro de una etapa.
- [NECESITA ACLARACIÓN] **8. Succión en la resistencia**: tensión efectiva única con χ (nueve
  métodos en T11 §3, ¿todos?) o resistencia no saturada (φb, Vanapalli), o las dos excluyentes; la
  referencia advierte de no contar dos veces la succión (T11 §3.3). ¿Y el tope de succión que Slip2D
  añadió en su spec 005?
- [NECESITA ACLARACIÓN] **9. Esquema y pasos de tiempo**: el núcleo usa Euler implícito y pasos
  automáticos; la referencia nombra diferencias centradas y regresivas sin decir su defecto (T11
  §1.4). ¿Se expone el esquema? ¿Pasos fijos por caso?
- [NECESITA ACLARACIÓN] **10. SSR en un transitorio** (SLP-67, SLP-120, EJ-SEE-03): ¿en qué
  instantes, y cómo se marcan en la interfaz?
- [NECESITA ACLARACIÓN] **11. Tolerancias del no lineal** (núcleo 1e-4, referencia 1e-6, P08), como
  la duda 9 de la 017.

La referencia P08 es de la carpeta A del análisis de interfaz
(`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/`, `reproducciones/`); M24, de la
carpeta B (`modelo/M24_agua_subterranea.md`).
