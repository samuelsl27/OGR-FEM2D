# Spec 006 — Interfaz, operaciones y cálculo

> **Revisada (2026-11-24), para aprobar.** Fase 1 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 006 — Interfaz, operaciones y cálculo (depende
> de P1)»). Solo el **qué** y el **porqué**; el cómo, en `plan.md`. Las dudas del borrador son ahora
> las decisiones propuestas D1–D18 (abajo), para el OK de la propietaria. Versiones: **v0.0.12 a
> v0.0.15**, una por parte (D2).

## La revisión (2026-11-24)

- [x] Contrastada con el código y con las specs cerradas desde el borrador (004 el 2026-11-23, 005
  el 2026-11-24). **Ya está hecho, sin Qt**:
  - el modelo como valor inmutable, su validación con el objeto culpable (`model/model.py`,
    `problems`), el deshacer (`model/history.py`, sobre `ogr_core.project.commands`), el archivo
    `.ogrfem2d`, las huellas, abrir un `.ogr` de Slip2D y un DXF (spec 004);
  - las ediciones de fases, asignaciones, excavación y factores por fase (`model/stages.py`). **No
    hay todavía funciones de edición de la geometría** (añadir, mover o borrar contornos y vértices),
    ni de materiales, campo, condiciones y cargas: hoy se construye el modelo entero;
  - los cortes entre contornos los dejó la 004 para aquí (su D15: «los cortes los pondrá la 006»);
    las condiciones por nudo, «cuando lo pida la 006» (su D7);
  - el cálculo fase a fase con `should_stop` entre fases, el `.h5` con sus estados, el catálogo de
    magnitudes con claves para traducir, la recuperación por parches, las consultas por línea, por
    contorno, en todos los nudos y frente a la fase, el resumen y la tabla CSV con sus ajustes
    (spec 005). **Lo que la 005 deja a la 006**: el selector con el catálogo, los estados al abrir,
    `calculate` para el subproceso, el dibujo de las consultas y de los contornos, y el valor
    absoluto como opción de dibujo;
  - los valores por defecto ya decididos (borrador, duda 5): sistema `metric_kpa`, deformación
    plana, malla graduada de **T6** (spec 003; el T3 no cumple STR-04 ni STR-09), tensión de campo
    nula, el externo fijo en X e Y escrito explícito (004, D16), E y ν sin valor hasta que se dan
    (004, D16);
  - el `Project` del núcleo (borrador, duda 2) ya no es el modelo de este programa (004, D1): el
    lienzo y la ventana de Slip2D, que lo usan, no se pueden reutilizar tal cual.
  - Del `.ogr` del borrador (RF-16) se pasa al `.ogrfem2d` (ADR-0004).
- [x] Mirados OGR Slip2D (v0.1.486, solo lectura), OGR Data y el núcleo (v0.2.7; su `main`, 0.2.8.dev0):
  - Las cifras del borrador siguen exactas: `ogr_gui` 77 archivos y 48 721 líneas, de ellas 23 308 en
    los 13 que importan el motor de equilibrio límite; `ogr_api` 31 y 10 158 (6 087 en los 14 que lo
    importan); `ogr_mcp` 8 y 2 952, sin el motor; `ogr_cli` 2 y 395. El plan de desarrollo todavía
    dice 42 000 y 9 700.
  - **Nadie más ha planeado extraer la interfaz**: ni Slip2D, ni OGR-Core (`docs/consumidores.md`),
    ni los prompts de la suite. La regla de capas del núcleo (`AGENTS.md`, «Capas») prohíbe PySide6,
    `ogr_api` y `mcp`, y un test lo vigila.
  - **OGR Data ya copia el aspecto de Slip2D** (`ogr_data/gui/themes.py`: «the OGR-Slip2D design
    language»), su `tr()` y su patrón de operaciones y de servidor MCP. La «copia que diverge» que
    P1 quería evitar ya existe una vez.
  - Lo genérico de verdad (sin el motor ni el `Project`), con su tamaño: temas y colores por papel
    (`themes/`, 454), iconos semánticos sobre qtawesome (`resources/icons.py`, 217), leyenda (289),
    paletas y niveles (`contours.py`, 296, salvo su lista de campos), enganche (`snap_engine.py`,
    344), barra de estado con las palancas y la entrada de X, Y (277), los motivos de lo deshabilitado
    (`disabled_reasons.py`, 66), tareas en hilo (`background.py`, 264), preferencias (164), tamaños
    de diálogo y botones (`dialog_size.py`, `button_floor.py`, `wheel_guard.py`), gráfico XY
    (`xy_chart.py`), el mecanismo de `tr()`. En las operaciones: el registro (`ops/__init__.py`,
    68), los errores (130), la conversión de argumentos (`coerce.py`, 285), los trabajos en
    subproceso (`jobs/__init__.py`, 271), el puente con la ventana (`bridge.py`, 442, solo
    biblioteca estándar).
  - **No es genérico**: la ventana principal (7 500), la de interpretación (4 821) y el lienzo
    (4 378) mezclan lo común con el equilibrio límite y con el `Project`. El diccionario de
    traducciones (8 462) mezcla los dos dominios, ordenado por versión.
  - Slip2D **no tiene entrada de arcos** para los contornos (solo círculos de anotación), y aquí el
    modelo los tiene (004, D2).
- [x] Fuentes: **ninguna fórmula nueva**. Lo numérico de esta spec es la vía completa (las
  operaciones, la interfaz) dando **los mismos números** que la 005, que ya están validados. El
  dibujo de contornos interpola con las funciones de forma del motor (Z&T ec. 14.27, ya leída en la
  005). El contorno externo automático no tiene fuente (abajo, D18).
- [x] Fichas STR-01, STR-04 y STR-09 releídas con su «Seguimiento»: las tres tienen la línea de
  resultados hecha por la 005 y dicen «Falta: el dibujo de la línea y de los contornos (spec 006)».
- [x] Análisis de la interfaz de referencia releído (`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/`,
  árbol de menús, D01–D04, D08, interpretación, cálculo, reproducciones). Lo que confundía a los
  usuarios está en «Lo que se evita» (abajo).
- [x] Dudas convertidas en decisiones propuestas (D1–D18), para el OK de la propietaria.

## Depende de

- **Decisión P1** del plan (tomada: opción (b)); D1 la concreta, con su ADR (ADR-0005).
- Specs 002 a 005: motor, malla, modelo y resultados. ADR-0002, ADR-0003 y ADR-0004.
- **Fuera de este repositorio** (D1): una versión de OGR-Core con el armazón de las operaciones y de
  los trabajos, y la primera versión del paquete `ogr-gui`. Se piden por escrito; esta spec no los
  rodea.
- `spec/constitution/guia-de-interfaz.md` (D16).

## Contexto y objetivo

Es la spec que cierra la fase 1: dibujar un modelo, mallarlo, calcularlo y ver los resultados, todo
desde la interfaz, en elástico. Tiene tres capas, como Slip2D: las **operaciones** sin Qt, con la
línea de órdenes y el servidor MCP encima; el **modelador**, con los menús en el orden del flujo de
trabajo; y el **cálculo** y la **interpretación**. La interfaz sigue la estética de Slip2D y la
mejora donde la guía de interfaz lo justifica; cada opción mueve el número (regla 7) y cada valor por
defecto que lo cambia se ve con el resultado (regla 12).

## Usuarios / actores

- **El ingeniero**; **el docente y el estudiante**; **un agente** a través del servidor MCP; **un
  script** o la línea de órdenes; **el investigador** que lee los resultados.

## Historias de usuario

- H1: Como ingeniero quiero dibujar un túnel y su contorno exterior, mallarlo, darle la tensión de
  campo, calcular y ver σ1 alrededor del hueco sin salir del programa.
- H2: Como ingeniero que conoce Slip2D quiero los menús en el orden del flujo de trabajo, los mismos
  atajos, y entrar vértices por clic, por teclado (absolutos, relativos o polares), por tabla, y
  círculos y arcos.
- H3: Como ingeniero quiero cancelar un cálculo largo y ver su progreso por fase, escalón e
  iteración, y su registro.
- H4: Como ingeniero quiero una consulta por línea con su gráfico y exportarla a una tabla.
- H5: Como agente quiero construir y calcular el mismo modelo con las mismas operaciones que la
  interfaz.
- H6: Como usuario quiero toda la interfaz en español o en inglés.
- H7: Como ingeniero quiero ver, junto al resultado, lo que lo decidió: la malla, los defectos, el
  estado de los resultados.

## Requisitos funcionales (EARS)

**Lo que falta en el modelo, sin Qt (parte A)**

- RF-1: EL SISTEMA ofrece cada edición del modelo como una función pura (modelo → modelo): contornos
  y vértices (añadir, mover, borrar), materiales, asignaciones, campo, condiciones, cargas, malla y
  ajustes del proyecto.
- RF-2: CUANDO un contorno nuevo o movido cruza otro, EL SISTEMA añade el vértice de la intersección
  en los dos (004, D15), y lo dice.
- RF-3: EL SISTEMA construye círculos y arcos como segmentos con su centro (004, D2): un arco por tres
  puntos o por inicio, centro y fin, partido en dos si pasa de 180°; un círculo, cuatro arcos (D10).
- RF-4: EL SISTEMA da un informe textual del modelo y de sus resultados (D17), sin Qt.
- RF-5: EL SISTEMA da, para dibujar un campo sobre la malla, los triángulos y sus valores, material a
  material y con las funciones de forma del elemento (D11), y los niveles de la leyenda.

**Operaciones y transporte (parte B)**

- RF-6: EL SISTEMA ofrece cada acción de las specs 004 y 005 y de RF-1 a RF-5 como una operación con
  nombre, argumentos tipados y respuesta serializable, sin Qt; la interfaz, la línea de órdenes y el
  servidor MCP la llaman, y ninguna sabe quién la llama.
- RF-7: SI una operación recibe un argumento desconocido o inválido, ENTONCES lo rechaza con un error
  que lo nombra; nunca lo acepta en silencio.
- RF-8: EL SISTEMA hace de cada edición un paso de deshacer, venga de donde venga.
- RF-9: CUANDO se pide calcular, EL SISTEMA lo hace en un subproceso cancelable y con cola, informa
  del progreso por fase, escalón e iteración (D9) y al terminar escribe el `.h5` (spec 005).
- RF-10: CUANDO se cancela, EL SISTEMA termina el proceso de verdad y no deja resultados que parezcan
  completos.
- RF-11: SI el cálculo falla (entrada rechazada, sistema singular, no convergencia), ENTONCES EL
  SISTEMA dice qué objeto del modelo lo causa y conserva el registro.
- RF-12: SI no hay malla, o la malla o los resultados son de otro modelo, ENTONCES calcular o
  interpretar no se ofrece como válido, y el motivo se dice.

**Modelador (parte C)**

- RF-13: EL SISTEMA ordena los menús como el flujo de trabajo: Archivo, Edición, Vista, Análisis,
  Contornos, Malla, Cargas, Desplazamientos, Soporte, Agua, Estadística, Propiedades, Herramientas,
  Ventana, Ayuda; toda acción es alcanzable desde un menú (regla 3). Los menús de fases futuras se
  ven, con su motivo (D4).
- RF-14: EL SISTEMA ofrece los diálogos de la fase 1: ajustes del proyecto, fases, tensión de campo,
  malla en dos pasos (discretizar y mallar), materiales, asignación por región y fase (con excavar),
  desplazamientos (restringir en X, en Y o en las dos, imponer, liberar) y cargas.
- RF-15: EL SISTEMA dibuja las fases como pestañas, el bloque de tensiones de campo, las condiciones y
  las cargas; la fase visible es la que se edita.
- RF-16: EL SISTEMA muestra en cada campo de tensión o de carga el convenio en que se escribe; la
  conversión sigue en su único sitio (`model/conventions.py`, regla 10).
- RF-17: EL SISTEMA abre un `.ogr` de Slip2D y un DXF desde el menú, con su informe a la vista.

**Cálculo e interpretación (parte D)**

- RF-18: EL SISTEMA ofrece una ventana de cálculo con la cola, el progreso, Cancelar, el registro y un
  resumen al terminar.
- RF-19: EL SISTEMA ofrece un selector de magnitud (el catálogo de la 005, con sus nombres en
  axisimetría), contornos con leyenda (magnitud, unidad, convenio, fase y si los valores son
  recuperados), pestañas de fase, consultas por línea, por contorno y en todos los nudos, con sus
  gráficos, y su exportación.
- RF-20: EL SISTEMA muestra con cada resultado los valores que lo decidieron (regla 12): la cota B y
  las notas del mallador, los nudos del eje que restringió el motor, el estado y las versiones del
  `.h5`, los ajustes de la consulta y del dibujo.

**Idioma, ayuda y casos**

- RF-21: EL SISTEMA pasa todo texto visible por `tr()`, con su traducción española (regla 2), y una
  ayuda adaptada que enlaza los casos de validación; sin telemetría ni llamadas de red no pedidas.
- RF-22: EL SISTEMA abre, calcula y consulta los casos de la fase con su `modelo.ogrfem2d` por las
  operaciones y por la interfaz, sin pantalla, y da los mismos números que la 005 (D13).

## Validación numérica

| Caso | Fuente científica | Qué se compara |
|---|---|---|
| `005-kirsch-malla-general`, `006-carga-en-faja-malla-general`, `007-cavidad-esferica-malla-general` | Las de la 005 (Kirsch en JCZ §8.4; Michell en Timoshenko y Goodier §34; Lamé, §121) | Por la vía completa (abrir, mallar, calcular en el subproceso, consultar), por las operaciones y por la interfaz: **los mismos números bit a bit** que la consulta de la 005, y dentro de la tolerancia de sus `esperado.json` |
| Identidad de transporte | — | La misma secuencia de operaciones por Python, la línea de órdenes, el servidor MCP y la interfaz da el mismo modelo (huella) y el mismo `.h5` (bit a bit en sus campos) |
| Identidad del dibujo | — | El modelo del caso 006 dibujado desde cero por las acciones de la interfaz tiene la huella del `modelo.ogrfem2d` guardado |
| Identidad de cancelación | — | Cancelar y volver a calcular da lo mismo que calcular una vez |
| Identidad del contorno dibujado | Z&T ec. (14.27), leída en la 005 | El valor dibujado en cada nudo es el recuperado; un campo lineal se dibuja exacto; la leyenda pinta con la misma función de color que el lienzo |
| Cortes | — (geometría) | El vértice añadido está en los dos contornos y sobre los dos segmentos; las regiones resultantes son las del dibujo |
| Regla 7 | — | Cada opción de cada diálogo y de cada operación, con el test que demuestra que mueve el número |

## Fuentes por conseguir

- Ninguna. Si algún día se ofrece el contorno externo automático (caja, círculo, envolvente), la
  relación entre su factor y el tamaño observada en la referencia es una hipótesis, no una fuente
  (D18).

## Requisitos no funcionales

- **Dependencias nuevas**, cada una con el OK de la propietaria y en la parte que la usa (D14):
  PySide6 (LGPL-3.0), qtawesome (MIT; los iconos de Font Awesome Free, CC BY 4.0 y OFL 1.1),
  matplotlib (licencia propia de tipo PSF) y el SDK de MCP (MIT, como extra opcional).
- Tests de la interfaz sin pantalla (`QT_QPA_PLATFORM=offscreen`) y sin estado filtrado (regla 5,
  el vigilante de fugas del núcleo), en Windows, macOS y Linux.
- El lienzo, fluido con la malla del caso 005 (28 066 T6), con los objetivos de D15 escritos antes de
  medir.
- La guía de interfaz (D16): cada componente nuevo pasa su lista.
- Instalador congelado con la interfaz, a partir del congelado de la spec 001.

## Casos límite

- Modelo sin malla; malla de otra geometría; resultados obsoletos, incompletos o cancelados.
- Cerrar la ventana o el programa con un cálculo en marcha.
- El servidor MCP editando un modelo que está abierto en la ventana (D8).
- Un texto sin traducción; una acción sin menú; una acción de la interfaz sin operación (los tres,
  fallo de un test).
- Axisimetría: el eje dibujado; la geometría con x < 0, rechazada al dibujarla.
- Cambio de unidades o de tipo de análisis con el modelo ya definido (las unidades no tocan los
  valores, 004 D5).
- Un contorno dibujado sobre otro, por un vértice suyo o a lo largo de un segmento suyo.
- Un clic de selección que no cae en nada.

## Lo que se evita (reproducciones de la referencia)

| Lo que pasaba | Aquí |
|---|---|
| Campo de 10 MPa por defecto, aplicado sin decirlo (P11) | Nulo por defecto, y dibujado con su bloque |
| Todo el externo restringido sin verse (P05) | Escrito explícito (004, D16) y dibujado en el lienzo |
| Añadir geometría borraba la malla (P10) | La malla queda, marcada como de otra geometría, y calcular dice por qué no se puede |
| Un clic a 2 px de un segmento no seleccionaba nada, en silencio (P13) | Tolerancia en píxeles de pantalla; el fallo se dice en la barra de estado |
| La axisimetría elegida no se aplicaba (P17) | El tipo de análisis, en el título y en la barra de estado; el eje, dibujado |
| Intro en un desplegable aceptaba el diálogo; Ctrl+A abría Asignar (P22) | Los atajos de Slip2D; Intro en un desplegable no acepta |
| Un aviso «Reset mesh» antes de cada edición (P21) | Se dice una vez, en la barra de estado |
| El botón Excavar no hacía nada (P03) | Excavar con su test (regla 7) y en el menú contextual de la región |

## Fuera de alcance

- El contenido de los menús de Soporte, Agua y Estadística (fases 2 a 6), SSR, juntas y soportes.
- Animación y grabación, datos de usuario, juntas ubicuas, isolíneas, líneas de flujo de tensiones,
  tensiones normal y tangencial sobre una consulta, pérdida de volumen de la excavación.
- Condiciones por nudo (004, D7), mallas por regiones avanzadas, contorno externo automático (D18).
- Importar o exportar modelos de otros programas que no sean de la suite; impresión e informes en
  PDF.

## Criterios de finalización

- [ ] D1–D18 aprobadas por la propietaria; ADR-0005 escrito
- [ ] Lo genérico, en las versiones etiquetadas que fija D1, fijadas aquí
- [ ] Todos los RF con su test en verde; todo texto nuevo traducido; toda acción en un menú y con su
      operación (o su motivo para no tenerla)
- [ ] Los casos de la fase, por las operaciones y por la interfaz, idénticos a la 005 y dentro de su
      tolerancia
- [ ] Las identidades de la tabla, en verde y con dientes
- [ ] Los objetivos de D15 medidos; la lista de la guía de interfaz pasada en cada componente
- [ ] La CI en verde en las tres plataformas, con la interfaz y el congelado
- [ ] Un changelog por parte con lo encontrado; fichas con su «Seguimiento»; la fase 1 cerrada en la
      hoja de ruta

## Decisiones propuestas (2026-11-24)

Para el OK de la propietaria. Las referencias D01–D08, M02, P03–P22 e I01–I03 son del análisis de
interfaz (`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/`). Los tamaños de Slip2D son de
su v0.1.486.

| # | Duda del borrador | Decisión propuesta | Por qué |
|---|---|---|---|
| D1 | 1: P1, OGR-Core o `ogr-gui`, y qué entra | **Las dos cosas, cada una con lo suyo, sin cambiar la regla de capas del núcleo.** (i) **Lo genérico sin Qt** (el registro de operaciones, los errores con código, la conversión de argumentos, los trabajos en subproceso y el protocolo del puente), a una versión nueva de **OGR-Core**: no importa PySide6 ni `mcp`, así que cabe. (ii) **Lo genérico con Qt** (temas y colores por papel, iconos, leyenda, paletas y niveles, enganche, barra de estado, motivos de lo deshabilitado, tareas en hilo, preferencias, ayudas de diálogo, gráfico XY, el mecanismo de `tr()` con sus textos y las comprobaciones de la regla 2 y la 3), a un **paquete hermano `ogr-gui`** (repositorio `samuelsl27/OGR-GUI`), que depende de `ogr-core` y se fija por etiqueta como él. Las dos cosas se copian de Slip2D **sin tocarlo**, como se hizo con el núcleo; Slip2D las adopta cuando su sesión lo decida. **No entra**: la ventana principal, la de interpretación, el lienzo completo ni los diálogos de contenido, que mezclan el equilibrio límite y el `Project`: este programa escribe los suyos sobre las piezas comunes. El servidor MCP de este programa es propio y fino (sin OAuth en la fase 1). ADR-0005 | La regla de capas del núcleo es la que deja probar el núcleo sin pantalla y usarlo desde la línea de órdenes; cambiarla por la interfaz es caro y no hace falta. Un paquete aparte para lo de Qt es lo que ya preveía P1. Lo que no es genérico no se extrae: copiarlo a medias sería la tercera copia que diverge (OGR Data ya es la segunda). Extraer solo lo limpio (del orden de 3 500 a 4 500 líneas con Qt, según cuántas ayudas de diálogo entren, y unas 1 200 sin él) es posible copiando, sin reescribir Slip2D |
| D2 | 9: cómo partirla | **Una sola spec, en cuatro partes**, cada una con su versión y su changelog: **A** (v0.0.12), lo que falta en el modelo y en la interpretación, sin Qt y sin esperar a nadie; **B** (v0.0.13), operaciones, línea de órdenes, servidor MCP y cálculo en subproceso, con la versión de OGR-Core de D1; **C** (v0.0.14), el modelador, con `ogr-gui`; **D** (v0.0.15), cálculo e interpretación en la interfaz y el cierre de la fase 1. Las peticiones de D1 salen en la T1, antes de programar, para que avancen en paralelo a la parte A | Partirla en specs nuevas correría la numeración del plan. Las partes dejan cada versión cerrada y en verde, y la A no depende de nadie. El orden (A → B → C → D) es el de las dependencias: cada parte usa la anterior |
| D3 | 3: traducciones | **Un diccionario común en `ogr-gui`**, con los textos de sus piezas, y **uno de este programa por áreas** (`ogr_fem2d/gui/i18n/`: menús, diálogos, interpretación, mensajes), como OGR Data. La clave es el texto inglés (el mecanismo de Slip2D). Las comprobaciones (todo texto por `tr()`, todo con traducción, ninguna traducción idéntica, censadas por AST) vienen de `ogr-gui`, para que la regla 2 diga lo mismo en todos los programas | Con un diccionario común, los textos comunes no divergen; con uno por áreas, este programa no hereda las 3 488 entradas de equilibrio límite. Una regla que necesitan dos programas vive en un sitio (`AGENTS.md` de OGR-Core, «Capas») |
| D4 | 4: menús de fases futuras | **Visibles, en su sitio, con una sola entrada deshabilitada que dice cuándo llegan** («Llega en la fase 2: spec 010»), con el mecanismo de `disabled_reasons` | El orden de los menús es lo que el ingeniero reconoce (guía, §1); ocultar impide descubrir (guía, §11). Una lista de entradas grises prometería lo que no hay |
| D5 | 5: valores por defecto | **Los del modelo, ya decididos** (la revisión, arriba). Un material nuevo pide E y ν, sin valor previo. **Ningún valor observado en la referencia** (10 MPa, E = 20 000 MPa, ν = 0.3, 0.027 MN/m³) entra como defecto. **Paleta de contornos por defecto: una de luminosidad monótona y apta para daltonismo** (Viridis, que Slip2D ya tiene), con las demás de Slip2D a mano | Un defecto inventado mueve el número sin decirlo (regla 12; 004, D16). La paleta: Slip2D pone el arco iris por defecto, que falsea el orden de los valores para quien no distingue los colores (guía, §12). Es una mejora que se propone también a Slip2D |
| D6 | 6: interpretación en otra ventana | **Como Slip2D**: una ventana de interpretación del mismo programa, por modelo, abierta desde Análisis → Interpretar; una ventana principal por modelo, varias a la vez | La coherencia con Slip2D (guía, §1). Ver el modelo y sus resultados a la vez sirve para comparar |
| D7 | 7: menús contextuales e impresión | **Contextuales, sí**: en la región (material, excavar, propiedades), el segmento (restricciones, cargas), el vértice y la consulta (gráfico, editar, borrar, copiar). **Exportar la vista a imagen, sí. Imprimir y configurar la página, no** | Los contextuales acercan la acción al objeto (Fitts; P03 solo funcionaba así). La imagen basta para un informe; imprimir es otra spec |
| D8 | 8: el puente entre el servidor MCP y la ventana | **En la parte D, si el protocolo está en el núcleo de D1** y la pieza de Qt en `ogr-gui`. Si no llegan a tiempo, se deja dicho y pasa a una spec posterior; la fase 1 se cierra con el servidor trabajando sobre archivos | En Slip2D es casi genérico (unas tres líneas nombran el programa). Hecho aquí aparte sería otra copia |
| D9 | Nueva: el progreso y la cancelación | **El progreso lleva fase, escalón e iteración**; en elástico, escalón e iteración valen 1, y la 007 los llena. Cancelar es en dos tiempos: **`should_stop` entre fases** (el `.h5` queda `cancelled`, spec 005) y, si el proceso no termina en un plazo, **se mata el árbol del proceso**, como en Slip2D; entonces queda el `.h5` anterior, que su huella juzga | El protocolo no cambia cuando lleguen los escalones. La parada entre fases conserva lo resuelto; matar el proceso es lo único que para de verdad una fase larga. El plazo no mueve ningún número |
| D10 | Nueva: la entrada de geometría | **Clic con enganche; X, Y por teclado** en la barra de estado, también **relativos (`@dx, dy`) y polares (`@d<ángulo`)**; **tabla**; **círculo** (centro y radio, o centro y punto: cuatro arcos); **arco** (tres puntos, o inicio, centro y fin; partido si pasa de 180°, porque el mallador toma el arco menor, spec 003). Los cortes añaden su vértice (RF-2). La selección de un tramo, por segmentos, con tolerancia en píxeles. Las condiciones, sobre la geometría (004, D7) | Es lo que da Slip2D más lo que el modelo necesita (los arcos) y lo que la referencia ofrecía (relativos y polares). Los relativos y polares son una mejora que se propone también a Slip2D |
| D11 | Nueva: el dibujo de los contornos | Cada elemento se **subdivide** (en T6, cuatro subtriángulos por nivel; dos niveles por defecto) y cada vértice nuevo toma el valor **interpolado con las funciones de forma del elemento** sobre los valores recuperados (Z&T ec. 14.27, como la consulta de la 005), **material a material**. Los niveles: automáticos por fase o de todas las fases, o a mano, con N intervalos. El valor bajo el cursor y las consultas usan la interpolación exacta, no el dibujo | Dibujar un T6 como cuatro T3 lineales sin más perdería la curvatura del campo que la 005 recupera. El dibujo es una imagen, no un número: lo que se compara sigue siendo la consulta. Material a material, porque la recuperación lo es (005, D5) |
| D12 | Nueva: los números en pantalla | Se muestran con el **separador decimal del idioma** (coma en español), como OGR Data; al escribir se aceptan la coma y el punto, y se muestra lo entendido con su unidad. **La tabla CSV, siempre con punto** (005, D15). Cambiar de idioma pide reiniciar, como Slip2D | Es la costumbre del lector y no es ambigua en un campo numérico (guía, §8). La tabla la lee un programa. El reinicio evita retraducir la ventana en caliente, que Slip2D tampoco hace |
| D13 | Nueva: cómo se valida la interfaz | Con **identidades** (la tabla de «Validación numérica»): mismo número por todos los caminos, mismo modelo dibujado que guardado, misma función de color en la leyenda y en el lienzo. Y un **inventario**: cada acción de la interfaz tiene su operación, o el motivo de no tenerla (como `inventory.py` de Slip2D) | Los números ya están validados contra soluciones cerradas en la 005; lo que esta spec puede romper es el camino, y eso lo prueba una identidad (regla 1). El inventario es lo que garantiza H5 |
| D14 | Nueva: dependencias | **PySide6**, **qtawesome** y **matplotlib** en la parte C; el **SDK de MCP** (`mcp>=2.1,<3`, como Slip2D) en la B, como extra opcional `[mcp]`. Cada una con su OK, su licencia en el comentario de `pyproject.toml` e instalada en el `.venv` con `--no-deps`. Los iconos de Font Awesome, con su atribución en «Acerca de» | Son las de Slip2D (PySide6 ≥ 6.6, sin la 6.12.0 por debajo de Python 3.12). Todas compatibles con AGPL-3.0; CC BY 4.0 pide atribución |
| D15 | Nueva: el objetivo de rendimiento | Con la malla del caso 005, en el equipo de desarrollo: **dibujar el modelo o un contorno por primera vez, ≤ 1 s; mover, ampliar o pasar el cursor, ≤ 0.1 s; cambiar de magnitud o de fase, ≤ 1 s**. Escritos antes de medir | Por debajo de 0.4 s la respuesta se siente inmediata (Doherty; guía, §4). Si no se cumple, es un hallazgo y se propone qué hacer, no se afloja solo |
| D16 | Nueva: la guía de interfaz | `spec/constitution/guia-de-interfaz.md` **pasa a la constitución**, enlazada desde `AGENTS.md`. Cada tarea de interfaz cierra con su lista por componente. Una mejora sobre Slip2D se propone también a su sesión | Las buenas prácticas, escritas una vez y consultables; la coherencia de la suite, protegida |
| D17 | Nueva: el informe | Sin Qt, en texto y HTML: el resumen del proyecto, el análisis y las unidades, las fases, el campo, la malla (tipo, elemento, nudos, elementos, cota B, notas y avisos del mallador), los materiales, las condiciones y las cargas, **los valores que deciden el resultado** (`deciding_values`) y, con resultados, su estado, sus versiones y por fase el resumen de la 005 (extremos y reacciones). Sin pérdida de volumen | Es lo que da la referencia (`01_info_viewer`) más lo que pide la regla 12. La pérdida de volumen pide definir el área deformada: no es de la fase 1 |
| D18 | Nueva: el contorno externo automático | **Fuera de esta spec** | La regla de su tamaño no tiene fuente; sería propia, y el usuario puede dibujar el externo (cuatro clics o un círculo) |

### Consecuencias en el resto del proyecto

- `plan_de_desarrollo.md`: P1 con los tamaños medidos (48 721 y 10 158), y la «Spec 006» con sus
  cuatro partes. En la T0, con el OK.
- ADR-0005 nuevo (D1); `tech-stack.md`, la fila del núcleo y una de `ogr-gui`; `AGENTS.md`,
  «Stack» y el enlace a la guía de interfaz (D16). En la T0.
- Peticiones escritas: a la sesión de OGR-Core (D1 i) y a la suite (D1 ii, el repositorio nuevo),
  en `../Promts_desarrollo/` (T1).
- Para Slip2D, solo propuestas: la paleta por defecto (D5), los relativos y polares (D10). No
  bloquean nada.
