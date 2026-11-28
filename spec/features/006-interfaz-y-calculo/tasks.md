# Tareas — Spec 006, interfaz, operaciones y cálculo

Pequeñas y verificables, ordenadas por dependencia. Al terminar cada una:
- este archivo y el changelog de su parte, al día;
- la suite entera en verde (`.venv/Scripts/python tests/_runner.py`; desde la parte C, con
  `QT_QPA_PLATFORM=offscreen`);
- el commit directo en `main`, sin push hasta que la propietaria lo pida (la C y la D, en la rama
  corta que ella elija, por la CI).

Cada test lleva su cabecera y tiene dientes: mutaciones sistemáticas
(`{etiqueta: (archivo, texto, sustituto)}`), anotadas aquí. Cada tarea de interfaz cierra además
con la lista por componente de `spec/constitution/guia-de-interfaz.md`.

## Antes de programar

- [x] T0. **Spec, plan y tareas aprobados**, con D1–D18. Va en un commit propio.
  - `docs/decisiones/ADR-0005-interfaz-comun.md` (D1).
  - `plan_de_desarrollo.md`: P1 con los tamaños medidos; la «Spec 006» en cuatro partes (D2).
  - `tech-stack.md`: `ogr-gui` y las dependencias de D14.
  - `guia-de-interfaz.md` aprobada, y enlazada desde `AGENTS.md` (D16).

  *Hecho cuando:* la propietaria ha dado el OK, y las decisiones están anotadas como aprobadas en
  `spec.md` y `plan.md`. (Hecho el 2026-11-24: OK de la propietaria a D1–D18; ADR-0005 escrito;
  `plan_de_desarrollo.md`, `tech-stack.md` y `AGENTS.md` al día; la guía, aprobada y enlazada.)
- [x] T1. **Las dos peticiones de D1**, por escrito en `../Promts_desarrollo/`, con lo encontrado y
  la evidencia (archivos y tamaños de Slip2D, la copia de OGR Data, la regla de capas):
  - a la sesión de OGR-Core: el armazón sin Qt (registro, errores, conversión de argumentos,
    trabajos en subproceso, protocolo del puente), en una versión etiquetada;
  - a la suite: el repositorio `OGR-GUI` y su v0.1.0 con las piezas de D1 (ii), copiadas de Slip2D
    sin tocarlo, con sus tests y su CI.

  *Hecho cuando:* las dos están escritas y entregadas a la propietaria. No bloquea la parte A.
  (Hecho el 2026-11-24: `2026_11_24_peticion_ogr_core_armazon_de_operaciones.md` y
  `2026_11_24_peticion_suite_paquete_ogr_gui.md`, con los archivos, las líneas y lo que ata cada
  pieza a Slip2D, comprobados en su v0.1.486.)

## Parte A — v0.0.12: lo que falta sin Qt

- [x] T2. **v0.0.12**, `model/edit.py`: contornos y vértices (añadir, mover, borrar, cerrar, cambiar
  de tipo) — RF-1, RF-7. Empieza `CHANGELOG_v0.0.12.md`.

  *Hecho cuando:* cada edición da un modelo válido o un error que nombra el argumento; aplicada por
  `Document.edit`, deshacer la devuelve; en axisimetría, un vértice con x < 0 se rechaza al
  añadirlo.
  (Hecho el 2026-11-24: también renombrar, trasladar, insertar y borrar vértices y el arco y las
  divisiones de un segmento; la geometría compartida sigue compartida. 21 tests; 17 mutaciones, 17
  cazadas.)
- [x] T3. `model/cuts.py`: los cortes (RF-2).

  *Hecho cuando:*
  - recto con recto, recto con arco y arco con arco añaden el vértice en los dos contornos y sobre
    los dos segmentos;
  - un cruce por un vértice existente no añade nada;
  - dos segmentos solapados dan un error que nombra los dos contornos;
  - un arco partido conserva su centro en las dos mitades;
  - las regiones del resultado son las del dibujo, y la respuesta lista los vértices añadidos.

  (Hecho el 2026-11-24: 9 tests; 10 mutaciones, 10 cazadas. Un tramo en común se rechaza, como dice
  el plan; la alternativa, dejarlo como lado compartido, queda propuesta en el changelog.)
- [x] T4. `model/shapes.py`: arcos y círculos (RF-3, D10).

  *Hecho cuando:* tres puntos de una circunferencia conocida dan su centro; tres colineales, error;
  inicio, centro y fin en los dos sentidos; un arco de 270° sale en dos; el círculo son cuatro arcos
  que pasan por sus vértices.
  (Hecho el 2026-11-24: también por inicio, centro y ángulo, y `Drawn` para juntar rectas y arcos.
  11 tests; 12 mutaciones, 12 cazadas.)
- [x] T5. `model/edit.py`: materiales, asignaciones, campo, condiciones, cargas, ajustes de la malla
  y del proyecto (RF-1), sobre `stages.py` donde ya existe.

  *Hecho cuando:* lo mismo que la T2 para cada una; un material nuevo sin E ni ν es válido como
  documento y la traducción al motor lo dice (004, D16); cambiar de sistema de unidades no toca
  ningún valor (004, D5).
  (Hecho el 2026-11-24: 12 tests; 12 mutaciones, 12 cazadas. Las ediciones de fases de la 004 se
  juzgan ahora por lo que rompen, como estas. **Anomalía**: `assign_material` con la geometría a
  medias añadía una asignación duplicada; reportada y corregida con el OK de la propietaria
  (`regions.region_of`; Slip2D no la tiene, por otro diseño). 6 tests más; 7 mutaciones, 7
  cazadas.)
- [x] T6. `results/calculate.py`: el aviso de progreso (D9).

  *Hecho cuando:* los eventos salen en orden, uno al empezar y otro al terminar cada fase, también
  en un cálculo cancelado o incompleto; los casos 003 a 007 dan la misma huella de todos sus campos
  con y sin `progress`.
  (Hecho el 2026-11-24: bit a bit en un túnel de tres fases y en el caso 007 desde su archivo; el
  005 y el 006 pasan por el mismo bucle en sus tests de la 005; el 003 y el 004 no pasan por
  `calculate`. El aviso dice si la fase se resolvió. 6 tests; 8 mutaciones, 8 cazadas.)
- [x] T7. `report/info.py`: el informe (RF-4, D17).

  *Hecho cuando:* cada sección aparece; están todos los `deciding_values`; sin resultados, con
  resultados obsoletos o incompletos, lo dice; el texto y el HTML dicen lo mismo.
  (Hecho el 2026-11-24: con la columna de dos estratos como comprobación externa, 316 kPa y las
  reacciones. 7 tests; 9 mutaciones, 9 cazadas.)
- [x] T8. `results/drawing.py`: los triángulos y los niveles de un campo (RF-5, D11).

  *Hecho cuando:*
  - en los nudos, el valor dibujado es el recuperado;
  - un campo lineal con T3 y uno cuadrático con T6 salen exactos en todos los subvértices;
  - dos materiales no se mezclan en su contacto;
  - los lados curvos se dibujan sobre el arco;
  - los niveles automáticos de una fase cubren su rango, los de todas las fases el de todas, y los
    manuales son los pedidos;
  - el tiempo con el caso 005 está medido y anotado.

  (Hecho el 2026-11-24: 10 tests; 11 mutaciones, 11 cazadas. **Cambia lo previsto**: los intervalos y
  los colores son de `ogr-gui`; aquí, el rango entero, sin percentil. Caso 005: 1,12 s la primera
  tensión de una fase, 0,06 s las siguientes.)
- [x] T9. **Cierre de la parte A**: `docs/interfaz/edicion.md`; los casos 001 a 007, bit a bit;
  `CHANGELOG_v0.0.12.md` con lo encontrado.

  *Hecho cuando:* todo lo de la parte A está en verde, y la propietaria sabe en qué estado están las
  peticiones de la T1.
  (Hecho el 2026-11-24: la página va en `docs/modelo/edicion.md`, con su ejemplo ejecutado por un
  test; el motor y `rust/` sin cambios desde `9c366ff`; las peticiones, entregadas.)

## Parte B — v0.0.13: operaciones y transporte

Empieza cuando la versión de OGR-Core de D1 (i) está etiquetada.

- [x] T10. **v0.0.13**: la fijación del núcleo nuevo, en su propio commit (`pyproject.toml`, el
  `.venv` con `--no-deps --force-reinstall`, lo que pida su changelog). Se avisa a la propietaria de
  la fila de `docs/consumidores.md`.

  *Hecho cuando:* la cabecera del runner nombra la versión nueva y la suite entera está en verde.
  (Hecho el 2026-11-24: OGR-Core v0.2.9, `23bc41a`, con `ogr_core.api`; 660 de 660 con
  `shared: ogr_core 0.2.9`.)
- [x] T11. `api/workspace.py`, `api/ops/project.py` y `api/ops/history.py`: abrir, nuevo, guardar,
  cerrar, abrir un `.ogr` de Slip2D o un DXF, deshacer y rehacer (RF-6–8).

  *Hecho cuando:* cada operación rechaza un argumento desconocido o inválido con su nombre; cada
  edición es un paso de deshacer; abrir una importación devuelve su informe.
  (Hecho el 2026-11-24: también `project_summary`, `project_validate` y `project_settings`; los
  textos, codificados. 7 tests; 14 mutaciones, 14 cazadas. **Anomalía**: un modelo a medio
  dibujar no se podía guardar; corregida en la spec 004 con el OK de la propietaria: el archivo
  guarda un modelo válido como documento. 3 tests más; 5 mutaciones, 5 cazadas.)
- [x] T12. `api/ops/model.py` y `api/ops/mesh.py`: las ediciones de la parte A, discretizar y mallar
  (RF-6, RF-12).

  *Hecho cuando:* cada edición de `model/edit.py` tiene su operación (un test lo cuenta); mallar
  marca la malla vieja cuando cambia la geometría; los nombres coinciden con los de Slip2D donde
  hacen lo mismo.

  (Hecho el 2026-11-24: el caso 006, construido desde cero por las operaciones, tiene la huella de
  su archivo. 6 tests; 14 mutaciones, 14 cazadas.)
- [x] T13. `api/worker.py` y `api/ops/analysis.py`: calcular como trabajo en subproceso (RF-9–12).

  *Hecho cuando:*
  - tienen su test los estados `queued`, `running`, `done`, `failed` y `cancelled`;
  - el progreso llega por fase;
  - cancelar entre fases deja el `.h5` `cancelled`; matar el árbol deja el anterior y ningún
    temporal;
  - un fallo nombra el objeto del modelo y conserva el registro;
  - sin malla, con la malla de otra geometría o con resultados obsoletos, se niega y dice por qué;
  - cancelar y volver a calcular da lo mismo que calcular una vez.

  (Hecho el 2026-11-24: el gestor del núcleo no encola, rechaza (`Busy`): eso es lo que se prueba en
  lugar de `queued`. 8 tests; 11 mutaciones, 11 cazadas.)
- [x] T14. `api/ops/results.py`: abrir con su estado, las consultas, el resumen, la tabla, el informe
  y los triángulos de un campo (RF-6).

  *Hecho cuando:* cada consulta de la 005 tiene su operación y da sus mismos números bit a bit;
  unos resultados no válidos solo se leen pidiéndolo, y cada respuesta lleva el estado.
  (Hecho el 2026-11-24: también el campo listo para dibujar. 4 tests; 11 mutaciones, 11 cazadas.)
- [x] T15. `cli/__main__.py`: la línea de órdenes.

  *Hecho cuando:* abrir, mallar, calcular, consultar, exportar y el informe funcionan sobre un caso;
  un error sale con su código y la salida distinta de cero.
  (Hecho el 2026-11-24: también `run` con una lista de pasos. 3 tests; 6 mutaciones, 6 cazadas.)
- [x] T16. `mcp/`: el servidor MCP, con el SDK (`mcp>=2.1,<3`, MIT) en el extra `[mcp]`, con el OK de
  la propietaria y `--no-deps` (D14).

  *Hecho cuando:* las herramientas son exactamente el catálogo (un test lo comprueba); un argumento
  inválido devuelve el error de la operación.
  (Hecho el 2026-11-24: `mcp` 2.3.0 instalado con el OK de la propietaria. El SDK descartaba en
  silencio un argumento desconocido; ahora se rechaza por su nombre. Test de capas nuevo. La CI no
  instala el extra todavía: sus tests se saltan allí. 4 tests; 8 mutaciones, 8 cazadas.)
- [x] T17. **Las identidades de transporte y los casos por las operaciones** (RF-22).

  *Hecho cuando:*
  - la misma secuencia por Python, la línea de órdenes y el servidor MCP da la misma huella y los
    mismos campos del `.h5`;
  - los casos 005, 006 y 007, abiertos, mallados, calculados en el subproceso y consultados por las
    operaciones, dan bit a bit lo de la 005 y cumplen su tolerancia.

  (Hecho el 2026-11-24: la tolerancia, por los mismos números que la 005 ya compara con las
  soluciones cerradas. 4 tests; las mutaciones, en el changelog.)
- [x] T18. **Cierre de la parte B**: el barrido de las reglas 7 y 12 sobre las operaciones;
  `docs/operaciones/catalogo.md`; `CHANGELOG_v0.0.13.md`.

  *Hecho cuando:* la tabla de opciones con su test está en el changelog y no le falta ninguna.
  (Hecho el 2026-11-24: el catálogo, escrito desde el registro y vigilado por un test. 5 tests más.)

## Parte C — v0.0.14: el modelador

Empieza cuando `ogr-gui` v0.1.0 está etiquetado.

- [x] T19. **v0.0.14: precisar las partes C y D** sobre `ogr-gui` v0.1.0 (sus nombres, sus piezas, lo
  que no llegó), en `plan.md` y aquí. Con el OK: la fijación de `ogr-gui`, PySide6, qtawesome y
  matplotlib declarados con su licencia e instalados con `--no-deps`; la rama corta, si la elige la
  propietaria.

  *Hecho cuando:* el plan de C y D nombra archivos reales, la suite está en verde con las
  dependencias nuevas, y PySide6 funciona con el Python del `.venv`.
  (Hecho el 2026-11-24, en la rama `dev/modelador`: `ogr-gui` v0.1.0, PySide6 6.12.0, qtawesome 1.4.2,
  matplotlib 3.11.2; la CI con Qt sin pantalla y el extra `[mcp]`. El diálogo de enganche y «Fit to
  results», sin usar tal cual; la petición a OGR-GUI, escrita.)
- [x] T20. `gui/main_window.py`, `gui/actions.py`, `gui/menus.py`, `gui/i18n/` y `gui/inventory.py`:
  la ventana con los menús en su orden, los de fases futuras con su motivo (D4), el tema y los iconos
  de `ogr-gui` (RF-13, RF-21). La CI con Qt sin pantalla.

  *Hecho cuando:* pasan los censos (todo texto por `tr()` y traducido; toda acción en un menú; toda
  acción con su operación o su motivo; toda entrada deshabilitada con su motivo) y el test de capas.
  (Hecho el 2026-11-25: el registro de acciones va en `main_window.py` (`_mk`), sin `actions.py`
  aparte; y `session.py`, la ventana sobre las operaciones. Los mensajes del núcleo, sin español
  todavía: pedido a OGR-GUI. 9 tests; 12 mutaciones, 12 cazadas.)
- [x] T21. `gui/canvas/`: el dibujo del modelo (contornos por tipo, regiones con el color de su
  material, la fase visible) y la navegación (ampliar, mover, rejilla, regla, enganche) — RF-15.

  *Hecho cuando:* cada tipo de objeto tiene su color y su trazo de la suite; los tiempos de D15 con la
  malla del caso 005, medidos y anotados.
  (Hecho el 2026-11-25: 0,17 s el primer dibujo, 16 ms ampliar, 6 ms mover. La regla del lienzo, en
  la T22 con la entrada de geometría. 9 tests; 14 mutaciones, 14 cazadas.)
- [x] T22. La entrada de geometría (D10): clic, X, Y absolutos, relativos y polares, tabla, círculo,
  arco, editar vértices; los cortes y sus vértices, a la vista.

  *Hecho cuando:* cada forma de entrada da los vértices esperados; un clic de selección en vacío lo
  dice en la barra de estado; deshacer quita un vértice o un contorno.
  (Hecho el 2026-11-25: el campo de X, Y de `ogr_ui`, con el lector de este programa; pedido a
  OGR-GUI. 11 tests; 14 mutaciones, 13 cazadas y 1 equivalente.)
- [x] T23. Los ajustes del proyecto (análisis, unidades, resumen) y las fases (pestañas: insertar,
  borrar, renombrar) — RF-14, RF-15.

  *Hecho cuando:* el tipo de análisis está en el título y en la barra de estado; en axisimetría el eje
  se dibuja; cambiar de unidades cambia lo mostrado y no los valores; cada opción mueve el número.
  (Hecho el 2026-11-25: las unidades, en un único sitio de la ventana, `gui/units.py`; por ahora
  las longitudes, y cada diálogo siguiente las suyas. 8 tests; 18 mutaciones, 17 cazadas y 1
  equivalente.)
- [x] T24. La tensión de campo (constante o gravitatoria con estratos) y su bloque dibujado, con el
  convenio junto a cada campo — RF-14, RF-16.

  *Hecho cuando:* cada campo del diálogo mueve el número; el bloque dibuja lo guardado; el convenio
  está escrito en el diálogo.
  (Hecho el 2026-11-25: en Cargas; el bloque, junto al modelo y dentro de «ver todo». 7 tests;
  19 mutaciones, todas cazadas.)
- [x] T25. La malla en dos pasos (ajustes, discretizar, mallar, quitar), su dibujo y sus notas —
  RF-14, RF-20.

  *Hecho cuando:* cada ajuste mueve la malla; la malla de otra geometría se marca y calcular lo dice;
  la cota B y las notas del mallador están a la vista.
  (Hecho el 2026-11-25: mallar es síncrono, 2-4 s con las mallas de los casos; hallazgo
  reportado en el changelog, para decidir. 5 tests; 23 mutaciones, todas cazadas.)
- [x] T26. Los materiales y el panel de asignación (por clic en la región, excavar, «solo esta fase»),
  con su menú contextual — RF-14, D7.

  *Hecho cuando:* asignar y excavar mueven el número (P03); un material sin E ni ν se señala y
  calcular dice cuál falta.
  (Hecho el 2026-11-25: cada acción del diálogo es una operación al momento; el menú de la
  región. 5 tests; 24 mutaciones, todas cazadas.)
- [x] T27. Las condiciones y las cargas: restringir en X, en Y o en las dos, imponer, liberar; carga
  repartida y puntual con su orientación y su factor por fase; su dibujo — RF-14, RF-16.

  *Hecho cuando:* cada opción mueve el número; el externo fijo por defecto se ve en el lienzo; la
  selección por tramo tiene su tolerancia en píxeles y lo dice.
  (Hecho el 2026-11-25: el tramo es el segmento del clic, o el vértice a menos de 8 píxeles.
  7 tests; 23 mutaciones, todas cazadas.)
- [x] T28. Abrir un `.ogr` de Slip2D y un DXF desde el menú, con su informe; recientes; preferencias
  (idioma y tema) — RF-17.

  *Hecho cuando:* el informe de la importación se ve entero; cambiar de idioma lo guarda y pide
  reiniciar; los tests restauran idioma y tema.
  (Hecho el 2026-11-25: las líneas del informe salen en inglés; hallazgo reportado en el
  changelog. 3 tests; 14 mutaciones, todas cazadas.)
- [x] T29. **Cierre de la parte C**: el caso 006 dibujado desde cero por las acciones; la regla 7 de
  cada diálogo; la lista de la guía; `CHANGELOG_v0.0.14.md`.

  *Hecho cuando:* el modelo dibujado tiene la huella del `modelo.ogrfem2d` del caso (o el hallazgo
  está reportado, regla 6) y la tabla de opciones está completa.
  (Hecho el 2026-11-25: la malla, bit a bit; la huella, igual salvo el orden de los vértices
  de la ventana de refinamiento, hallazgo reportado. Tres decisiones pendientes antes de la
  parte D, en el changelog.)

## Parte D — v0.0.15: cálculo e interpretación en la interfaz

- [x] T30. **v0.0.15**, `gui/compute_window.py`: la cola, el progreso por fase, escalón e iteración,
  Cancelar, el registro y el resumen al terminar — RF-18.

  *Hecho cuando:* Cancelar para el proceso; cerrar con un cálculo en marcha pregunta una vez y lo
  para; un fallo nombra el objeto; la interfaz no se congela.
  (Hecho el 2026-11-27: la cola es `job_list`, sin encolar, porque el núcleo corre un trabajo
  cada vez; el plazo de Cancelar se espera fuera del hilo de la ventana. 9 tests; 17
  mutaciones, todas cazadas.)
- [x] T31. `gui/interpret/`: la ventana, el selector de magnitud, las pestañas de fase, el campo
  dibujado con su leyenda y sus opciones (rango, intervalos, paleta, modo, valor absoluto) y el valor
  bajo el cursor — RF-19, RF-20.

  *Hecho cuando:*
  - el selector es el catálogo, con los nombres de la axisimetría;
  - la leyenda dice magnitud, unidad, convenio, fase y procedencia, y pinta con la función del
    lienzo;
  - cada opción mueve el dibujo;
  - unos resultados obsoletos o incompletos no se confunden con válidos;
  - los tiempos de D15, medidos.
  (Hecho el 2026-11-27: todo, salvo el primer dibujo de una fase con el caso 005, 3,9 s frente
  a 1 s, por la recuperación: hallazgo con tres propuestas en el changelog. 15 tests; 20
  mutaciones, todas cazadas.)
- [x] T32. Las consultas en la interfaz (línea, polilínea, contorno con lado y distancia, todos los
  nudos), con su gráfico (frente a la distancia o a la fase) y su exportación — RF-19.

  *Hecho cuando:* cada consulta da los números de su operación; el gráfico y la tabla, también; cada
  opción mueve el número.
  (Hecho el 2026-11-27: 9 tests; 13 mutaciones, todas cazadas.)
- [x] T33. `gui/info_window.py`: el informe, guardable en HTML y en texto; lo que decidió el
  resultado, a la vista con él — RF-4, RF-20.

  *Hecho cuando:* el informe es el de la T7; los valores de RF-20 se ven en la interpretación.
  (Hecho el 2026-11-27: el informe, con cada línea codificada y en el idioma del lector; los
  nudos del eje, añadidos al informe. 8 tests; 11 mutaciones, todas cazadas.)
- [x] T34. El puente entre el servidor MCP y la ventana abierta (D8), si sus piezas están etiquetadas.

  *Hecho cuando:* una edición por el servidor se ve en la ventana y se deshace en ella; con un cálculo
  en marcha, responde `Busy`. O, si no están, está dicho en el changelog y anotado para otra spec.
  (Hecho el 2026-11-27: el protocolo del núcleo v0.2.9 bastó; la pieza de Qt es el `QTcpServer` de
  la ventana. 4 tests; 8 mutaciones, todas cazadas.)
- [x] T35. **Los casos por la interfaz** (RF-22): 005, 006 y 007, abiertos, calculados y consultados
  sin pantalla, y sus contornos dibujados. (Hecho el 2026-11-27.)

  *Hecho cuando:* dan los mismos números que por las operaciones; las fichas STR-01, STR-04 y STR-09
  tienen su «Seguimiento» (el dibujo de la línea y de los contornos).
- [x] T36. La ayuda adaptada, con los casos (RF-21); el congelado con la interfaz; la CI en las tres
  plataformas.

  *Hecho cuando:* la ayuda no hace llamadas de red; el congelado abre, malla, calcula y consulta un
  caso en Windows, macOS y Linux; su tamaño está anotado. (Hecho el 2026-11-27.)
- [x] T37. **El cierre de la spec y de la fase 1.**
  - El barrido de las reglas 7 y 12 sobre la interfaz.
  - Los casos 001 a 007, bit a bit.
  - `CHANGELOG_v0.0.15.md` completo.
  - La fase 1 cerrada en la hoja de ruta.
  - Las propuestas a Slip2D (D5, D10), entregadas a la propietaria.

  *Hecho cuando:* todos los criterios de finalización de `spec.md` están marcados.
  (Hecho el 2026-11-28: la CI de `3ec4fc8`, run 46127528558, en verde en las tres plataformas.)
