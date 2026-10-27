# Plan de desarrollo

> **Aprobado por el propietario (2026-10-27)**, con las cuatro propuestas P1–P4 tal como están.
> Desglosa la [hoja de ruta](roadmap.md) aprobada en *specs*
> SDD y tareas, desde la fase 1 hasta el final del FEM. Cada *spec* se escribe, se aprueba y se
> cierra como la 001 (`spec.md`, `plan.md`, `tasks.md`), así que aquí solo va lo que cada una debe
> resolver, de dónde sale y qué casos la cierran: el detalle se fija al abrirla. Fuentes de este plan:
> la hoja de ruta, el análisis inicial (`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/`:
> S01 especificación inicial, S02 reutilización de Slip2D, S06 pendientes y dudas, lo observado en
> 22 reproducciones, el árbol de menús y el catálogo teórico T00) y el índice de los 274 casos de
> verificación (`../Referencias/Ejemplos/Casos_por_problema/00_INDICE.md`).

## Dónde estamos

- **Fase 0 cerrada** (spec 001): elemento T6, elasticidad, Mohr-Coulomb con su tangente consistente,
  escalones con Newton y partición del incremento; referencia en Python validada contra Kirsch y
  Salençon; variantes NumPy y Rust detrás de una interfaz común; ruedas y congelado en tres
  plataformas. ADR-0001 aceptada: el motor va en Rust.
- **Fase 0b cerrada**: `ogr-core` v0.1.0 con geometría, malla (Delaunay de SciPy, triángulos de 3
  nudos), filtración, materiales, cargas, proyecto `.ogr`, DXF, estadística e informes.
- **Lo que no hay todavía**: modelo de proyecto FEM, mallado general, interfaz gráfica, `ogr_api`,
  línea de órdenes, servidor MCP, resultados en `.h5`, casos con `modelo.ogr`. El motor solo resuelve
  el cuarto de corona de la spec 001.

## Decisiones previas a la fase 1

**Tomadas por el propietario el 2026-10-27: las cuatro propuestas.** P1, opción (b): la parte
genérica de la interfaz se extrae, copiándola desde Slip2D sin tocarlo, a una versión nueva de
OGR-Core o a un paquete hermano `ogr-gui`; cuál de los dos se decide en el ADR que abra la *spec* de
la interfaz, y cada versión nueva de OGR-Core sigue necesitando su OK. P2: T6 y T3 en la fase 1. P3:
las presiones hidrostáticas pasan a la fase 2 (la hoja de ruta se actualizó). P4: el bucle global
pasa a Rust en la fase 2, tras medir.

| # | Decisión | Opciones | Propuesta | Por qué importa |
|---|---|---|---|---|
| P1 | **Cómo reutilizar la interfaz de Slip2D.** `ogr_gui` (42 000 líneas), `ogr_api` (9 700), `ogr_mcp` (2 900) y `ogr_cli` viven en el repositorio de Slip2D, que no se toca | (a) copiarlos a OGR-FEM2D y adaptarlos; (b) extraer lo genérico (lienzo, herramientas, diálogos de proyecto, vista y preferencias, contornos, i18n, trabajos en subproceso, deshacer) a una versión nueva de OGR-Core o a un paquete hermano `ogr-gui`, copiándolo desde Slip2D sin tocarlo, como se hizo con el núcleo; (c) escribirla de nuevo | **(b)**: es la vía del ADR-0002 y evita una tercera copia divergente; pide un ADR y una versión nueva de OGR-Core con tu OK | Es la tarea más grande de la fase 1 y decide si FEM2D y Slip2D comparten aspecto y comportamiento |
| P2 | **Elementos de la fase 1.** La hoja de ruta dice T3/T6/Q4/Q8 | T6 solo; T6 y T3; los cuatro | **T6 como elemento principal y T3 (que ya genera la malla de `ogr-core`)**; Q4 y Q8 cuando haya mallado mapeado (spec de malla) | La regla 9 deja que cada caso fije su elemento: no hace falta el Q8 de la ficha de STR-01 para validarlo |
| P3 | **Agua para el SSR antes de la fase 4.** Los casos de SSR (123 de 274) piden nivel freático, Hu/Ru y agua embalsada, que no son flujo FEM | dejarlo en la fase 4; adelantarlo a la fase 2 | **Adelantar a la fase 2 las presiones hidrostáticas** (nivel freático, Hu, Ru, rejilla, agua embalsada; ya están en `ogr-core`) y dejar en la 4 el flujo FEM, el no drenado y la consolidación | Con eso la fase 2 desbloquea unos 41 casos en lugar de 21 (recuento del índice de casos) |
| P4 | **Cuándo pasa el bucle global a Rust.** Hoy Python ensambla y factoriza: en la malla del caso 002 la factorización (75–94 ms) ya pesa más que la llamada de Rust (5–9 ms) | ahora; en la fase 2, con el SSR (cientos de análisis); más tarde | **En la fase 2**, con una medida A/B de SuperLU frente a `faer` como manda el ADR-0001 | El SSR multiplica el coste del bucle por el número de factores probados |

## Cómo se trabaja (sin cambios)

Una *spec* a la vez, con plan y OK antes de programar; fórmula sin fuente no entra; la referencia en
Python va antes que Rust y es su oráculo; cada fase se cierra con sus casos de validación
(`validacion/casos/`, con `modelo.ogr` desde la fase 1), su estudio de convergencia y su changelog;
cada tarea terminada se sube con la suite en verde. Las fichas de trabajo de los casos
(`Referencias/Ejemplos/Casos_por_problema/`) se van marcando en su «Seguimiento».

---

## Fase 1 — Primer análisis elástico de principio a fin

**Objetivo:** dibujar un modelo, mallarlo, calcularlo y ver los resultados, todo desde la interfaz,
en elástico. **Casos que la cierran:** STR-01 (Kirsch, ya validado en el motor), STR-04 (carga en
faja sobre semiespacio), STR-09 (cavidad esférica, axisimétrico). **Dudas de S06 que resuelve:** 7
(STR-04: efecto del dominio finito y anomalía del manual), 14 (convenio de signos: ya fijado, falta
aplicarlo en la interfaz).

### Spec 002 — Motor elástico general
- Entrada discreta del motor (regla 11): nudos, elementos, materiales por elemento, tensiones
  iniciales, restricciones, cargas y fases, con un esquema documentado y validado al recibirlo.
- Elementos T6 y T3 en **deformación plana y axisimetría** (fuente: Zienkiewicz y Taylor 2000;
  axisimetría, por localizar el capítulo y comprobarla antes de programarla).
- Restricciones X, Y, XY y desplazamiento impuesto (en totales, D2); cargas nodales, distribuidas
  (uniformes y triangulares, fuerzas nodales consistentes) y puntuales.
- Tensión inicial **constante** (σ1, σ3, σz, ángulo) y **gravitatoria** con K0 constante o variable
  con la profundidad (T06; por material); peso propio.
- Excavación: elementos desactivados en la fase (lo que la spec 001 hacía con la malla sin hueco),
  con la carga de la (2.13b).
- Referencia en Python, variante Rust y su identidad; la variante NumPy no se mantiene más allá de
  la spec 001 (D4).
- Casos: STR-01 con malla general (no el cuarto de corona), STR-04, STR-09. Identidades: sólido
  rígido, prueba de la parcela en axisimetría, equilibrio global de reacciones.

### Spec 003 — Malla
- Discretización de contornos y mallado en dos pasos, como el programa de referencia (*Discretize*
  y *Mesh*), partiendo del generador de `ogr-core`.
- T3 y T6 con los nudos intermedios sobre los arcos (lección de la spec 001); malla graduada,
  uniforme y radial; densificación por ventana o polígono; regiones de material.
- Calidad de malla (criterio por definir con fuente) y comprobación de elementos degenerados.
- Mallado mapeado y cuadriláteros (Q4, Q8) quedan para cuando una spec los pida (P2).
- Rendimiento: el Delaunay de SciPy en Python; en Rust (`spade`, licencia por comprobar) solo si
  se mide que hace falta.

### Spec 004 — Modelo FEM y proyecto `.ogr`
- Tipos de contorno nuevos: excavación, fase, junta, interfaz estructural (los de equilibrio límite
  no aplican).
- La **fase** como dimensión de todo el modelo (materiales, contornos, cargas, condiciones, más
  adelante soporte y agua); insertar, borrar y renombrar fases.
- *Project Settings*: unidades, deformación plana o axisimetría, fases, solver (tolerancia, número
  máximo de iteraciones, escalones), con los valores por defecto a la vista (regla 12).
- Materiales elásticos (isótropo) con peso y modo de tensión inicial; asignación por región y fase.
- Condiciones de contorno por segmento, vértice o nudo; condición por defecto del contorno externo.
- Compatibilidad geométrica con `.ogr` de Slip2D (importar su geometría) y DXF; deshacer y rehacer.
- Huella del modelo (ADR-0003) calculada aquí.

### Spec 005 — Resultados (`.h5`) y su interpretación sin interfaz
- Archivo `modelo.h5` con la huella (ADR-0003) y resultados obsoletos marcados como tales; partir de
  `ogr_core/project/results_io.py`.
- Magnitudes de campo: tensiones cartesianas y principales, σz, media, von Mises, diferencial,
  desplazamientos, deformaciones volumétrica y de corte máximo, factor de resistencia (T05). Cada
  una con su definición y su fuente.
- Paso de puntos de integración a nudos para dibujar contornos (fuente: Zienkiewicz y Taylor 2000,
  §14.2, recuperación de tensiones), sin perder los valores en los puntos, que son los que se
  validan.
- Consultas por línea, por contorno de excavación y en todos los nudos, con exportación a tabla;
  evolución por fase.

### Spec 006 — Interfaz, operaciones y cálculo (depende de P1)
- `ogr_api`: operaciones sin Qt para todo lo anterior (y la línea de órdenes y el servidor MCP
  encima, como en Slip2D).
- **Modelador**: los menús en el orden del flujo de trabajo (Archivo, Edición, Vista, Análisis,
  Contornos, Malla, Cargas, Desplazamientos, Soporte, Agua, Estadística, Propiedades, Herramientas,
  Ventana, Ayuda); diálogos de la fase 1 (proyecto, tensión de campo, malla, materiales, asignación,
  desplazamientos, cargas); dibujo del bloque de tensiones de campo.
- **Cálculo** en subproceso cancelable, con cola y progreso por fase, escalón e iteración; registro
  de convergencia.
- **Interpretación**: selector de magnitud, contornos con leyenda, pestañas de fase, consultas y
  gráficos, *Info Viewer*, exportación de valores en nudos.
- Traducción ES/EN de todo texto visible, todo alcanzable desde un menú, ayuda adaptada.
- Los tres casos de la fase con su `modelo.ogr` y un test que los abre, calcula y compara.

---

## Fase 2 — No linealidad, plasticidad y reducción de resistencia

**Objetivo:** cálculo elastoplástico robusto con criterio de colapso fiable y SSR. **Casos:** STR-05
(Prandtl), STR-02 (ya validado en el motor), STR-03 (Hoek-Brown), SLP-01 (ACADS 1a) y SLP-12 (Arai
y Tagyo), y con P3 los SSR con nivel freático y agua embalsada. **Dudas de S06:** 3 (convergencia de
malla, ya resuelta en la spec 001), 5 (sensibilidad del SRF a la malla), 8 (tolerancia por defecto y
colapso).

### Spec 007 — Tolerancia, colapso y escalones (empieza la fase, enmienda 3 de la constitución)
- Fijar con STR-05 la **tolerancia por defecto** y el **criterio de colapso**: en la reproducción
  P13, con la tolerancia por defecto del programa de referencia, una carga por encima del colapso
  «convergía».
- Escalones automáticos (número de escalones del factor de resistencia, T05) y su reparto, mostrados
  con el resultado (regla 12).
- **Robustez de Newton**: la spec 001 dejó anotado que diverge con ψ = 0° en mallas finas y que la
  partición del incremento no basta; buscar la fuente (longitud de arco: de Souza Neto et al. 2008,
  cap. 4, Box 4.4; búsqueda lineal: la remiten a Crisfield 1991, que hay que conseguir) y validarla
  con el caso que fallaba.
- Fases de carga (STR-05 tiene ocho) y el gráfico de la historia por fase.

### Spec 008 — Leyes de la fase 2
- Mohr-Coulomb completo: tracción límite, residual y frágil-plástico (MC-RES), dilatancia.
- Drucker-Prager y Hoek-Brown generalizado (con la conversión a GHB como preproceso), cada uno con
  oráculo en Python, tangente consistente, prueba en punto material contra su fuente, identidad con
  Rust y su caso.
- Contrato común de ley constitutiva, pensado ya para los modelos de la fase 5 (T00 §4 propone el del
  modelo de usuario).

### Spec 009 — Reducción de resistencia al corte (SSR)
- Algoritmo (sin manual de teoría: fuente por conseguir; el análisis cita Dawson et al. 1999), con
  búsqueda del factor crítico, área de búsqueda y de exclusión (15 casos la piden) y aplicación por
  material.
- Resultados: deformación de corte máxima, vectores de desplazamiento, gráfico del SRF.
- Casos SLP-01 y SLP-12: los mismos que valida Slip2D, que da una comparación independiente (no una
  validación) en el mismo modelo.

### Spec 010 — Presiones intersticiales hidrostáticas (si se aprueba P3)
- Nivel freático y líneas piezométricas, Hu, Ru, rejilla de presiones (los siete interpoladores de
  `ogr-core`), agua embalsada como carga, tensiones efectivas, peso por encima y por debajo del nivel.
- Geosintéticos para los terraplenes reforzados (GEOSINT, 12 casos; duda 13: falta la rigidez del
  caso SLP-24).

### Spec 011 — Rendimiento del bucle global (P4)
- Ensamblaje y factorización: SuperLU frente a `faer` con A/B en el mismo proceso (método de la
  T13), paralelismo de la integración (`rayon`) si se mide que compensa.
- Bucle de escalones e iteraciones en Rust si la medida lo pide; la referencia en Python sigue siendo
  el oráculo.

---

## Fase 3 — Estructuras, discontinuidades y fases de construcción

**Casos:** STR-07 (túnel revestido), STR-21 (bulones), STR-28 (junta que corta un túnel), STR-06
(roca diaclasada). **Dudas de S06:** 1 (fórmulas de bulones de la ficha, a revisar con
Carranza-Torres 2002), 4 (signo del momento de los revestimientos), 12 (dilatancia en juntas).

- **Spec 012 — Fases de construcción completas**: excavación y relleno por fases, cambio de
  material, *load split* (relajación de la tensión de campo), condiciones y cargas por fase en
  totales, fase de instalación de cada soporte.
- **Spec 013 — Revestimientos**: viga (Euler-Bernoulli o Timoshenko, por decidir con fuente),
  plastificación por capas (Owen y Hinton, T03), sección compuesta, rótulas y momentos, retirada
  automática; convenio de signos de los esfuerzos fijado antes de programar.
- **Spec 014 — Bulones**: los cinco tipos en orden de dificultad (anclado en los extremos y
  totalmente adherido; fricción; *tieback*; cable), patrones, pretensado, resultados (T02).
- **Spec 015 — Juntas**: elemento junta (Goodman et al. 1968), criterios Mohr-Coulomb,
  Barton-Bandis e hiperbólico, con dilatancia; redes de juntas (T04: Baecher, Veneziano, Voronoi…);
  interacción bulón-junta (Dight 1982).
- **Spec 016 — Interfaz estructural, elementos infinitos y resultados de soporte**: interfaz
  estructural, elementos infinitos en el contorno (5 casos; fuente por localizar), gráficos de
  bulones, revestimientos y juntas en la interpretación.

## Fase 4 — Agua

**Casos:** GW-03, GW-04, GW-15, CON-01. **Dudas de S06:** 11 (cara de filtración en una infiltración
negativa).

- **Spec 017 — Flujo FEM estacionario** reutilizando el de `ogr-core` (ya validado en Slip2D):
  condiciones de altura, presión nula, caudal, rezume; secciones de descarga; líneas de flujo;
  presiones del flujo en el análisis tensional y en el SSR.
- **Spec 018 — No saturado y transitorio**: funciones de permeabilidad y retención, almacenamiento,
  condiciones dependientes del tiempo.
- **Spec 019 — No drenado y consolidación acoplada** (Biot, T09).

## Fase 5 — Modelos constitutivos avanzados

**Casos:** STR-13, CNS-01. **Dudas de S06:** 9 (definición de N en Cam-Clay modificado), 10
(definición de ν12 en la anisotropía). Una *spec* por familia, cada una con su oráculo en Python:
elasticidad anisótropa; Cam-Clay y Cam-Clay modificado; Duncan-Chang; endurecimiento y
ablandamiento; roca diaclasada; Hardening Soil y los de suelo blando (antes, localizar las
publicaciones originales: el catálogo solo cita manuales comerciales para cuatro de ellos).

## Fase 6 — Probabilístico

Estimas puntuales (Rosenblueth; duda 2: la probabilidad de rotura observada no se reproduce con una
normal), Monte Carlo y LHS reutilizando `ogr_core.statistics`; variables de material, junta y
tensión de campo.

## Fase 7 — Campos especiales

Dinámico (Newmark, Rayleigh, contornos absorbentes y de campo libre), térmico (conducción y después
acoplamientos), XFEM (al final, con la ley de junta ya validada en el elemento convencional).

## Después del FEM

Diferencias finitas explícitas y elementos discretos de partículas y bloques, en la misma
aplicación (S01).

---

## Trabajo transversal (en todas las fases)

- **Validación**: cada fase cierra con sus casos; las fichas de los 274 casos se van marcando; los
  que solo tienen otro programa como referencia se apoyan en la fuente científica o en un cálculo
  independiente (por ejemplo, Slip2D en el SSR).
- **Distribución**: ruedas en la CI (ya está) e instalador congelado por versión, a partir del
  congelado de la spec 001.
- **Documentación**: ayuda de usuario, tutoriales y la página de cada caso de validación.
- **Pendientes del análisis de interfaz** (S06): menús contextuales, *Page Setup*, importación DXF
  real, varias fases en *Staged Material Properties*, juntas ubicuas y animación en la
  interpretación; completarlos al abrir la *spec* que los necesite.
- **Integración de los núcleos de Slip2D y FEM2D**: decisión futura (ADR-0002); no se toca Slip2D
  hasta entonces.

## Orden propuesto

1. Decisiones P1–P4.
2. Fase 1: specs 002 → 003 → 004 → 005 → 006 (la 006 puede empezar en paralelo a la 003 si se
   decide P1 pronto).
3. Fase 2: 007 → 008 → 009 → 010 → 011.
4. Fases 3 a 7 en el orden de la hoja de ruta, revisando este plan al cerrar cada fase.
