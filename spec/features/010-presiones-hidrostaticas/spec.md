# Spec 010 — Presiones intersticiales hidrostáticas

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 2 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 010 — Presiones intersticiales
> hidrostáticas», adelantada de la fase 4 por la decisión P3). Solo el **qué** y el **porqué**, sin
> fórmulas ni decisiones tomadas. **Antes de abrirla hay que reevaluarla** (sección siguiente);
> después, plan y tareas con el OK de la propietaria.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador:
      `ogr_core/hydraulic/pore_pressure.py` (`pore_pressure_at`: sin agua, nivel freático, línea
      piezométrica, Ru, constante, y Hu con su modo automático; devuelve kPa);
      `ogr_core/hydraulic/water_surfaces.py` (qué superficie de agua vale en cada sitio: la del
      material para u, cualquier nivel freático para el peso saturado);
      `ogr_core/hydraulic/water_pressure_grid.py` (rejilla de altura total, de presión o de
      presión intersticial, con dos interpoladores, TPS e IDW); `ogr_core/interpolation.py`
      (IDW, TPS, TIN y lineal por cota, con el TPS local como método secundario);
      `ogr_core/hydraulic/ponded_water.py` (agua embalsada: solo la crean el nivel freático y la
      línea de desembalse); `ogr_core/materials/material.py` (`unit_weight`, `sat_unit_weight`,
      `use_sat_unit_weight`, `water_surface_id`, `hu`, `auto_hu`); `ogr_core/loads/overburden.py`.
      En Slip2D, `ogr_slip2d/slicer.py` (`_apply_ponded_water`, `_base_pore_pressure`) hace lo
      mismo en las rebanadas. Para el refuerzo, `ogr_core/support/support.py` (el geosintético de
      equilibrio límite: resistencia y arranque, no rigidez).
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 009: el SSR con presiones fijas, que es donde se usan casi todos estos casos.
- Spec 008: las leyes trabajan en tensiones efectivas.
- Spec `004-modelo-y-proyecto`: líneas de agua, asignación por material y por fase, rejillas,
  método y peso específico del agua en los ajustes del proyecto, con sus defectos a la vista.
- Spec `005-resultados`: tensiones efectivas y presión intersticial como magnitudes (P07).
- Spec `006-interfaz-y-calculo`: diálogos de propiedades hidráulicas y de agua, menú *Agua*.

## Contexto y objetivo

La decisión P3 adelantó a la fase 2 las presiones hidrostáticas porque muchos casos de SSR las piden
y no son flujo: nivel freático o línea piezométrica (`NF`, 42 casos), agua embalsada (`AGUA-EXT`,
19), Ru (`RU`, 9), rejilla (`PP-REJ`, 5) y peso distinto sobre y bajo el nivel (`PESO-SAT`, 4).
El núcleo ya calcula la presión intersticial en un punto con esos métodos, con el mismo significado
que en OGR Slip2D (P07). Lo nuevo en elementos finitos es dónde entra: la presión de cada punto de
integración da la tensión efectiva con la que trabaja la ley, el agua embalsada es una carga sobre
el contorno, y el peso bajo el nivel cambia la tensión inicial y la fuerza de masa.

El plan pone aquí también los **geosintéticos** (`GEOSINT`, 12 casos, duda 13 de S06). En elementos
finitos son un elemento de tracción con su interfaz con el suelo (P22), que es material de la fase 3.

## Usuarios / actores

- **Ingeniero de taludes y presas**, que define el agua como en equilibrio límite.
- **El SSR de la 009**, que recibe las presiones fijas.
- **OGR Slip2D**, a través del núcleo, que ya usa las mismas definiciones.

## Historias de usuario

- H1: Como ingeniero quiero dibujar un nivel freático o una línea piezométrica y asignarlos a cada
  material, para calcular en tensiones efectivas como lo haría en equilibrio límite.
- H2: Como ingeniero quiero definir el agua por Ru, por Hu o por una rejilla medida, para usar los
  datos que tengo.
- H3: Como ingeniero quiero que el agua por encima del terreno actúe como carga, para estudiar un
  talud sumergido o un embalse.
- H4: Como ingeniero quiero ver con el resultado qué método, qué peso del agua y qué interpolador se
  usaron, porque cambian el factor (regla 12).

## Requisitos funcionales (EARS)

**Presión intersticial**

- RF-1: EL SISTEMA calcula la presión intersticial en cada punto de integración con el método del
  material: ninguno, nivel freático, línea piezométrica (con Hu constante o automático), Ru, rejilla
  (altura total, altura de presión o presión) o constante, reutilizando el núcleo.
- RF-2: EL SISTEMA calcula la tensión efectiva de cada punto y la ley la usa; guarda las dos, total y
  efectiva, y la presión, con la conversión de signo en un único sitio (regla 10).
- RF-3: MIENTRAS dura un SSR, EL SISTEMA mantiene fijas las presiones (009, RF-7).
- RF-4: EL SISTEMA admite líneas de agua distintas por fase (P07).

**Agua embalsada y peso**

- RF-5: CUANDO hay agua por encima del contorno, EL SISTEMA aplica su presión hidrostática como
  carga sobre ese contorno, con la regla del núcleo sobre qué superficies la crean.
- RF-6: EL SISTEMA usa el peso saturado bajo el nivel freático y el natural por encima, en la fuerza
  de masa y en la tensión inicial gravitatoria, que se calcula en tensiones efectivas.

**Geosintéticos (si se quedan aquí)**

- RF-7: EL SISTEMA modela un refuerzo que solo trabaja a tracción, con su rigidez axial, su
  resistencia y su contacto con el suelo, sin ningún valor por defecto oculto (P22: la rigidez por
  defecto del programa de referencia casi anula el refuerzo).

**Reglas transversales**

- RF-8: Cada método y cada opción (peso del agua, Hu automático, interpolador, presión negativa,
  peso saturado) tiene su test que mueve el número (regla 7) y su valor a la vista con el resultado.
- RF-9: El motor recibe presiones por punto, no líneas de agua (regla 11): las calcula el preproceso.

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| Columna con nivel freático horizontal | Identidad hidrostática | Presión en cada punto; total menos presión igual a efectiva; reacciones |
| Talud totalmente sumergido | Identidad: con agua embalsada y peso saturado, el mismo factor que el talud seco con peso sumergido | Factor crítico de las dos formulaciones |
| Rejilla plana frente a nivel freático horizontal | Identidad: el TPS reproduce un campo plano exactamente (núcleo) | Presión en los puntos |
| `VER-SLP-12`, Arai y Tagyo (1985), ej. 3 | Arai y Tagyo (1985), Bishop | Factor crítico frente a un FS de equilibrio límite publicado |
| `VER-SLP-14`, Ru = 0.5 | Spencer (1969) y Baker (1980) | Ídem |
| `VER-SLP-07`, rejilla de alturas, ACADS 5 | Giam y Donald (1989) | Ídem, con agua embalsada |
| `VER-SLP-35`, talud sumergido | Duncan y Wright (2005), FS publicado | Factor crítico |
| `VER-SLP-104`, peso saturado y agua embalsada | US Army Corps of Engineers (2003) | Factor crítico |
| `VER-SLP-48`, muro de tres niveles con geosintético | Leshchinsky y Han (2004), valor de árbitro | Factor crítico (si RF-7 se queda) |

Se proponen como los que la cierran **SLP-12** (el del plan) y **SLP-35**, más las identidades.
Como en la 009, las referencias publicadas son factores de equilibrio límite; el de OGR Slip2D en el
mismo modelo es una comparación independiente. Cálculo propio sobre la tabla maestra: esta spec
añade unos 29 casos a los de la 009 sin geosintéticos, y unos 10 más con ellos.

## Fuentes por conseguir

- El principio de tensión efectiva de Terzaghi, citado sin datos en T11 §2; por comprobar.
- Bishop y Morgenstern (1960), por comprobar, como origen del coeficiente Ru.
- Hu automático: el núcleo lo toma de la documentación del programa de referencia, sin fuente
  científica. Hay que encontrarla o tratarlo como decisión propia.
- Interpoladores: el núcleo cita Shepard (1968), Harder y Desmarais (1972), Duchon (1976) y Franke
  (1985). El de Chugh y el de Chugh modificado (el defecto del programa de referencia, D01) no están
  en el núcleo ni tienen fuente localizada.
- Borges y Cardoso (2002) para SLP-24 (duda 13) y Leshchinsky y Han (2004) para SLP-48.

## Requisitos no funcionales

- Las presiones se calculan una vez por fase y punto, no en cada iteración.
- Unidades: el núcleo devuelve kPa; el modelo FEM puede ir en MPa (STR). La conversión, en un sitio.

## Casos límite

- Punto por encima del nivel freático (presión nula o negativa: corte de succión).
- Línea piezométrica por encima del terreno, que en el núcleo no crea agua embalsada.
- Línea de agua que no cubre todo el ancho del modelo; dos líneas para dos acuíferos.
- Rejilla con puntos fuera de su envolvente (método secundario del núcleo).
- Material sin línea asignada en un modelo que tiene una (regla del núcleo: no se usa).

## Fuera de alcance

- Flujo FEM estacionario o transitorio, cara de filtración y presiones del flujo en el SSR (fase 4,
  specs 017 y 018); no drenado y consolidación (spec 019).
- Desembalse rápido y exceso de presión por carga (están en el núcleo para equilibrio límite).
- Tensión efectiva no saturada (`UNSAT-MEC`, fase 4).

## Criterios de finalización

- [ ] Todos los RF con su test en verde
- [ ] Las identidades exactas y los casos que la cierran dentro de tolerancia, con su malla
- [ ] Los métodos que vienen del núcleo, usados desde el núcleo y no copiados
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog registrando qué se encontró

## Dudas abiertas

- [NECESITA ACLARACIÓN] **Duda 13 de S06 y sitio de los geosintéticos.** La rigidez axial del
  refuerzo cambia el factor (P22) y la ficha de SLP-24 no la da. Además el refuerzo necesita un
  elemento de tracción y su interfaz, que son de la fase 3 (specs 013, 015 y 016). Opciones: (a)
  dejarlos aquí con un elemento de tracción mínimo adherido sin interfaz; (b) moverlos a la fase 3;
  (c) una spec propia tras la 016. SLP-24 no vale como validación hasta tener los datos.
- [NECESITA ACLARACIÓN] **Interpolador por defecto de la rejilla**: el del programa de referencia
  (Chugh modificado) no está en el núcleo; el plan habla de «siete interpoladores de `ogr-core`» y el
  núcleo tiene dos en la rejilla y cuatro en `interpolation.py`. ¿Cuál por defecto y se piden más?
- [NECESITA ACLARACIÓN] **Agua embalsada con línea piezométrica**: el núcleo no la crea, por decisión
  documentada; ¿se mantiene en elementos finitos?
- [NECESITA ACLARACIÓN] **Tensión inicial con agua**: ¿el K se aplica a la tensión efectiva? ¿Qué
  pasa en una fase que cambia el nivel?
- [NECESITA ACLARACIÓN] **Presión negativa sobre el nivel**: ¿se anula o se mantiene? El núcleo lo
  deja elegir en la rejilla.
- [NECESITA ACLARACIÓN] **Peso saturado por defecto**: el núcleo no lo usa salvo que se pida
  (`use_sat_unit_weight`); ¿qué hace el FEM y cómo se muestra?
- [NECESITA ACLARACIÓN] **Duda 14 de S06**: el manual del no drenado escribe la tensión efectiva con
  la presión positiva en compresión sin declararlo (T11 §2.8); el convenio se fija aquí, no se copia.
