# OGR FEM2D v0.0.14

**Fase 1, séptima parte: el modelador** (spec 006, parte C). La ventana, los menús, el lienzo, la
entrada de geometría y los diálogos de la fase 1, sobre las operaciones de la parte B y las piezas
comunes de `ogr-gui` (ADR-0005). En la rama corta `dev/modelador`, porque toca la CI. Este archivo
cuenta lo que fue entrando, tarea a tarea.

## T19 — las partes C y D, precisadas; `ogr-gui` fijado (2026-11-24)

- **`ogr-gui` v0.1.0 fijado** en `pyproject.toml`, y PySide6, qtawesome y matplotlib declarados con su
  licencia (D14), con el OK de la propietaria. Instalados en el `.venv` con la orden que dio OGR-GUI:
  `ogr-gui` no depende de `ogr-core`, así que no lo toca (lo comprueba un test, con la versión fijada).
- **El runner**, con la lista blanca de fugas de OGR-GUI para sus piezas (la caché de iconos, el
  recolector, la guarda de la rueda, el suelo de los botones, la paleta original, `backend_fallback` de
  matplotlib), sus ganchos del recolector y las carpetas propias de cada corrida para las preferencias y
  el puente.
- **La CI**, con las bibliotecas de Qt en Linux, `QT_QPA_PLATFORM=offscreen` y el extra `[mcp]`: los tests
  del servidor MCP, que hasta ahora se saltaban en GitHub, corren allí.
- **El plan de las partes C y D, con las piezas reales** de `ogr_ui`. Lo que no trae y escribe este
  programa: el lienzo, sus objetos y sus herramientas, la tabla de coordenadas y el valor bajo el cursor.
  **Dos piezas que no se usan tal cual**: el diálogo de enganche tiene un control que no hace nada
  (`ortho_snap_angle_deg`, pendiente en OGR-GUI), y no va en un menú hasta que se arregle (regla 7); y
  «Fit to results» del diálogo de contornos recorta al percentil 98, que escondería el pico de tensión
  (T8): se usa sin ese botón, y se pide a OGR-GUI que el percentil sea un argumento
  (`../Promts_desarrollo/2026_11_24_peticion_ogr_gui_rango_entero.md`).
- La versión pasa a 0.0.14.

## T20 — la ventana, sus menús, sus acciones y sus textos (2026-11-25)

`ogr_fem2d/gui/`: `main_window.py`, `menus.py`, `inventory.py`, `session.py`, `app.py` y el diccionario
por áreas (`i18n/es_menus.py`, `i18n/es_messages.py`); `python -m ogr_fem2d` abre la ventana (RF-13,
RF-21; D3, D4, D13).

- **La ventana no edita el modelo**: llama a las operaciones de la parte B por una sesión
  (`session.Session`), como la línea de órdenes y un agente, y vuelve a dibujar cuando la sesión dice que
  algo cambió. Así H5 se cumple por construcción, y cada edición es un paso de la misma historia.
- **Los menús, en el orden del trabajo** (RF-13); los de fases futuras (Soporte, Agua, Estadística y
  Herramientas), con una sola entrada deshabilitada que dice cuándo llegan (D4). Los de esta fase que aún
  no tienen entradas son los que dice `menus.PENDING`, con la tarea que los llena; un test lo vigila.
- **Las reglas 2 y 3, con las comprobaciones comunes de `ogr_ui.testing`**: todo texto por `tr()` (dos
  excepciones con su porqué: el título de la ventana y la línea de la versión), todo con su español
  (también cada acción, cada menú, cada motivo y cada mensaje de las operaciones, en sus dos formas
  cuando lleva una cuenta), ninguno del español de la suite cambiado; toda acción en un menú y toda
  entrada deshabilitada con su motivo. **Cada acción tiene su operación o su porqué** (D13).
- **Los mensajes de las operaciones salen en el idioma del lector**: van codificados, y la interfaz los
  vuelve a componer desde su código (`i18n.say`), también el nombre de cada paso de deshacer. **Los del
  núcleo (`API_MESSAGES`) aún salen en inglés**: su español es común a la suite, y se pide a OGR-GUI que
  lo lleve (añadido a `../Promts_desarrollo/2026_11_24_peticion_ogr_gui_rango_entero.md`).
- El título dice el modelo, si tiene cambios sin guardar y el tipo de análisis (la referencia dejaba
  olvidarlo, P17). Lo que pregunta (un archivo, descartar cambios) es un método propio, para que los
  tests manejen la ventana sin un diálogo modal.
- `AGENTS.md`: la suite se corre siempre con `QT_QPA_PLATFORM=offscreen`. Para la CI de OGR-Core, la
  nota `../Promts_desarrollo/2026_11_25_nota_ogr_core_fem2d_sin_pantalla.md`, para cuando esta rama se
  fusione.

9 tests (8 de la ventana y 1 de capas: fuera de `gui/` nada importa Qt); 12 mutaciones, 12 cazadas (el
orden de los menús se comparaba con la propia constante; ahora con la lista de RF-13).

Una fuga que vio el vigilante en la suite entera: el guardián del recolector de `ogr_ui` se instalaba solo
si Qt ya estaba cargado, y una corrida del runner dentro de un test (`test_project_setup_v001`) lo
instalaba después de que la corrida de fuera hubiera mirado. Ahora se instala al empezar cada corrida,
como en OGR-GUI: no importa Qt, e instalarlo dos veces no hace nada.

## T21 — el lienzo: el modelo dibujado y moverse por él (2026-11-25)

`ogr_fem2d/gui/canvas/view.py` y `paths.py`; en la ventana, el lienzo con las pestañas de las fases debajo,
y el menú Vista (ver todo, acercar, alejar, rejilla, malla) (RF-15; D15; guía §3, §4, §6).

- **y hacia arriba**, como el modelo: un punto de la escena es un punto del modelo.
- **Cada tipo de contorno, su trazo**: externo y de material con los colores de Slip2D, excavación en rojo
  oscuro y fase discontinua en azul; trazos cosméticos, igual de gruesos a cualquier ampliación. Los arcos,
  con 16 cuerdas por cuarto de vuelta, solo para el dibujo: el modelo, la malla y las consultas guardan el
  arco.
- **Las regiones, con el color de su material**; una excavada en la fase que se ve, o todavía sin material,
  vacía. La fase que se ve es la que se edita (RF-15), en las pestañas. Un modelo a medio dibujar (sin
  externo, con un cruce) dibuja sus contornos y ninguna región.
- **La malla, un solo objeto** que pinta todas sus aristas, cada una una vez (84 432 en el caso 005).
- **D15, medido con el caso 005** (28 066 T6), escrito antes de medir: el primer dibujo, 0,17 s (objetivo,
  1 s); ampliar, 16 ms, y mover, 6 ms (objetivo, 0,1 s); cambiar de fase, 0,14 s. El test lo exige en este
  equipo, y con un margen de 5 en la CI, que es más lenta y compartida.
- La rueda amplía alrededor del cursor, el botón central mueve, la rejilla sigue la ampliación a pasos
  1-2-5 con los colores del tema, y las coordenadas del cursor van a la barra de estado.

9 tests; 14 mutaciones, 14 cazadas (cuatro se escapaban al principio: los trazos se comparaban con la
propia tabla, una arista repetida no cambiaba la cuenta, un arco recto pasaba con pocos puntos y las
coordenadas se emitían a mano; ahora se comparan con los colores de la suite, se cuentan los trazos del
camino, se piden las cuerdas y se mueve el ratón de verdad).

## T22 — la entrada de geometría (2026-11-25)

`ogr_fem2d/gui/canvas/tools.py` (sin Qt), `controller.py` y `dialogs/coordinates.py`; el menú Contornos
(añadir excavación, externo, de material, de fase y excavación circular; arco, tabla de coordenadas y
terminar; mover, insertar y borrar vértices; borrar contornos) (D10, D12; guía §3, §8; P05, P13).

- **Un punto escrito quiere decir una cosa** (D12): `x, y`, `x y`, `x; y` con coma decimal, `x,y` con
  punto; relativo, `@dx, dy`; polar, `@d<ángulo` en grados, exacto en un cuarto de vuelta. Lo ambiguo
  (`1,5,2,5`) se rechaza diciendo cómo escribirlo. **El campo de X, Y de `ogr_ui` solo admite el punto
  absoluto con punto decimal**: se usa el mismo campo con el lector de este programa, y se pide a OGR-GUI
  que lo traiga (tercera cosa de `../Promts_desarrollo/2026_11_24_peticion_ogr_gui_rango_entero.md`).
- **Un contorno se dibuja** por clics, puntos escritos, la tabla o arcos por tres puntos (medio círculo o
  más, dos segmentos); un punto sobre el primer vértice lo cierra; Retroceso deshace el último paso, Esc
  cancela, Intro o el botón derecho terminan. Terminar es una sola operación (`boundary_add`, con sus
  cortes) y un solo paso de deshacer, y la barra de estado dice cuántos cortes puso.
- **Cada clic se engancha** (`ogr_ui`, `SnapEngine`): a un vértice, a un segmento (un arco por sus
  cuerdas, que no son vértices), a la rejilla; las palancas, las de la barra de estado. **Escoger** un
  vértice o un segmento funciona a 8 píxeles de la pantalla, y un clic que no escoge nada lo dice (P13).
- **El lienzo vacío muestra una vista de partida** de 70 × 50 m: a un píxel por metro la rejilla era de
  50 m, y cada clic se iba a su nudo. Lo encontraron los tests.
- La tabla de coordenadas, con la coma o el punto decimal; una celda que no es un número se dice con su
  fila (P05: escribir deprisa en la referencia no era fiable; la tabla sí).

11 tests; 14 mutaciones, 13 cazadas y 1 equivalente (la cuenta de marcas decimales sobraba, porque la
expresión regular ya admite una por número: quitada del código).

## T23 — los ajustes del proyecto y las fases (2026-11-25)

`ogr_fem2d/gui/dialogs/project_settings.py`, `gui/units.py`; el menú Análisis (ajustes del proyecto;
añadir, renombrar y borrar fase), y el mismo menú en las pestañas de las fases (RF-14, RF-15; P17).

- **El diálogo, como el de Slip2D**: la lista de páginas a la izquierda (General, Resumen del proyecto).
  Lo que muestra sale del modelo y lo que da es solo lo que cambió: **una** `project_settings` y un paso
  de deshacer; sin cambios, ninguna operación. Cada opción dice lo que hace: la axisimetría toma x como
  el radio y el eje en x = 0, y la carga puntual es la del anillo entero; el sistema de unidades cambia
  lo que se muestra y cómo se lee lo escrito, nunca los valores (004, D5). Un rechazo (axisimetría con un
  vértice a la izquierda del eje) se dice en el diálogo, que se queda abierto.
- **El tipo de análisis, a la vista** (P17): en el título (T20) y ahora en la barra de estado, con las
  unidades de longitud y de tensión; en axisimetría **el eje se dibuja** (x = 0, trazo y punto). Un
  vértice dibujado a la izquierda del eje se rechaza diciendo por qué.
- **Las unidades cambian lo mostrado, no los valores**: `gui/units.py` es el único sitio de la ventana
  por el que una longitud pasa de metros a lo mostrado y vuelve. En pies, el cursor da pies, un punto
  escrito o una fila de la tabla en pies cae donde dice (en metros en el modelo), la cabecera de la tabla
  dice ft, y la rejilla es un número redondo de pies (en metros sería 3,28 ft y el enganche daría cotas
  raras). Las demás magnitudes llegan con sus diálogos (T24-T27).
- **Las fases son las pestañas** (RF-15): añadir va detrás de la que se ve y pasa a verse; renombrar
  (también con doble clic en la pestaña); borrar la que se ve, sin preguntar porque se deshace (guía §9).
  La única fase no se puede borrar, y la acción lo dice. Una fase sin nombre se ve como «Fase N».
- **Probado en pantalla** (sin pantalla, a imagen): las notas del diálogo se cortaban y el nombre de la
  página no cabía en la lista; se abre con `ogr_ui.dialog_size` (`open_at_content_size`, `list_width`).
  La etiqueta del análisis, a la derecha del todo, estrechaba el campo de X, Y: va delante de las palancas.

8 tests; 18 mutaciones, 17 cazadas y 1 equivalente (renombrar con el mismo nombre ya no deja paso: lo
filtra el espacio de trabajo; la comprobación de la ventana, quitada).

## T24 — la tensión de campo y su bloque (2026-11-25)

`ogr_fem2d/gui/dialogs/field_stress.py` y `canvas/paths.field_marks`; en el menú Cargas, «Tensión de
campo...» (RF-14, RF-15, RF-16; 004, D5, D6 y D14).

- **El diálogo**: constante (σ1, σ3, σz y el ángulo de σ1 con la horizontal, antihorario) o
  gravitatorio (la cota de la superficie y los estratos de arriba abajo: base, peso específico, K y Kz).
  **El convenio está escrito junto a cada tensión** («compresión +», RF-16) y la unidad, en cada campo.
  En axisimetría, una nota dice lo que pide el equilibrio radial (σr = σθ, τrz = 0), que el motor ya
  exige (spec 002, enmienda de D3).
- **Las unidades del modelo, en los dos sentidos**: en ksf, un σ3 escrito como 1 se guarda como
  47,88 kPa; un valor que el usuario no tocó vuelve **exactamente** como estaba, no a través del redondeo
  de lo que se muestra (un γ de 20,123456789 se ve 20,1235 y sigue siendo 20,123456789).
- **Sin defectos que muevan el número** (guía §10): sin estratos, el primero llega hasta la base del
  modelo y la superficie es su techo (geometría del modelo); el peso específico, K y Kz los escribe el
  usuario, y una celda vacía se dice con su estrato. Un rechazo (σ1 < σ3, una base que no queda por
  debajo de su techo) se dice en el diálogo.
- **El bloque dibuja lo guardado**: un campo constante es un cuadrado girado el ángulo de σ1, junto al
  modelo, con una flecha por cara tan larga como su tensión sobre la mayor, hacia dentro en compresión y
  hacia fuera en tracción; uno gravitatorio, la superficie y la base de cada estrato. «Ver todo» incluye
  el bloque, que si no quedaba fuera de la vista (se vio al dibujarlo a imagen).

7 tests; 19 mutaciones, todas cazadas (cuatro, después de reforzar los tests: quitar el estrato
escogido, la celda no tocada, la celda en otras unidades y el bloque en «ver todo»).

Encontrado de paso: unos borradores escritos con el Python del sistema salieron con CRLF; normalizados a
LF antes del commit (el `.gitattributes` ya fija `eol=lf`, así que nada llegó al repositorio).

## T25 — la malla en dos pasos (2026-11-25)

`ogr_fem2d/gui/dialogs/mesh_setup.py`; el menú Malla (ajustes, discretizar, discretizar y mallar, quitar
la malla); la malla en el lienzo y en la barra de estado (RF-14, RF-20; spec 003; P10).

- **Dos pasos, como la referencia**: «Discretizar» dibuja una cruz en cada nudo que tendrán los
  contornos y los cuenta, sin tocar el modelo; «Mallar» se habilita después (y vuelve a deshabilitarse
  al cambiar el tipo de malla). Cada ajuste cambiado es una `mesh_settings` con solo lo cambiado; mallar,
  otro paso.
- **Cada ajuste mueve la malla** (regla 7): tipo, elemento, B, nudos en las excavaciones (o en el
  externo si no hay), lado máximo, tamaño o número de elementos de la uniforme, y las ventanas de
  refinamiento como rectángulos (una ventana que no lo es, dada por la operación, se muestra y se
  guarda tal cual). Las longitudes, en las unidades del modelo.
- **Los nudos de la graduada no tienen defecto** (guía §10; spec 003, D5): el campo empieza «(por dar)»
  y discretizar sin ellos se rechaza en el diálogo diciendo por qué (la referencia ponía 75 o 60).
- **B y lo que decidió la malla, a la vista** (regla 12): junto a B, el ángulo mínimo que garantiza,
  arcsin(1/2B) (Shewchuk 2002a); en la barra de estado, el tamaño de la malla, y en su ayuda emergente B,
  el ángulo mínimo obtenido y los avisos del mallador; al mallar, el resumen.
- **La malla de otra geometría se queda y se marca** (P10; 004, RF-11): se dibuja a trazos en otro color
  y la barra de estado lo dice. «Quitar la malla» es un paso de deshacer, deshabilitado sin malla.

**Hallazgo (regla 6), para decidir**: mallar es síncrono. El caso 006 tarda 2,1 s en la ventana y el 005,
3,6 s (medido fuera): la ventana se queda quieta con el cursor de espera y «Mallando...». La guía (§4)
pide progreso y cancelar para un proceso largo. Propuesta: mallar como trabajo en subproceso, con el
mismo armazón que calcular (parte D, T30), o aceptarlo así para la fase 1. No se ha cambiado nada.

5 tests; 23 mutaciones, todas cazadas (tres, después de reforzar los tests para que comprueben el ajuste
guardado y no solo que la malla cambie; una línea redundante que hacía equivalente la cuarta, quitada).

## T26 — los materiales y el panel de asignación (2026-11-25)

`ogr_fem2d/gui/dialogs/materials.py`, `gui/assign_panel.py`, `dialogs/fields.py`; el menú Propiedades
(definir materiales, asignar propiedades) y el menú de la región en el lienzo (RF-14; D7; 004, D9, D11,
D16; P03).

- **Los materiales**: la lista con su color a la izquierda y el escogido a la derecha (nombre, color,
  carga inicial, peso específico, E y ν), como la referencia. **Cada acción es una operación al
  momento**, un paso de deshacer: Añadir, Borrar (rechazado si una región lo tiene, y se dice), Aplicar
  (solo lo cambiado); escoger otro aplica antes lo cambiado en el que se ve.
- **E y ν sin defecto** (D16): uno nuevo los muestra «(por dar)» y la lista lo marca; `project_validate`
  y calcular lo nombran. Una vez dados no se pueden quitar (la operación no lo admite): el diálogo lo
  dice en vez de ignorarlo.
- **El peso específico solo con peso propio** (D11): habilitado con una carga inicial que lo tenga, y
  con su porqué cuando no.
- **El panel de asignación**, junto al lienzo y abierto mientras se hace clic: un material, Excavar o
  Rellenar, en la fase que se ve; «Solo esta fase» cambia solo esa. Lo que el motor no admite (un
  elemento que vuelve, otro material en una fase posterior) lo rechaza la operación y se dice.
- **El menú de la región** (D7): con el botón derecho y sin herramienta, asignar un material, excavar,
  rellenar y los materiales; fuera de una región, ninguno.
- `dialogs/fields.py`: el número de un diálogo en las unidades del modelo, que vuelve exacto si no se
  tocó, compartido ahora por la tensión de campo y los materiales.

**Encontrado por los tests**: escoger otro material con cambios sin aplicar los aplicaba, pero al
rellenar la lista de nuevo la fila volvía al material anterior, y el diálogo mostraba uno con la fila
de otro. Corregido (la fila se repone). Y «Solo esta fase» no se distinguía con dos fases: con tres,
rellenar solo la primera deja la excavación en las otras.

5 tests; 24 mutaciones, todas cazadas (cinco, después de reforzar los tests).

## T27 — las condiciones y las cargas (2026-11-25)

`ogr_fem2d/gui/canvas/marks.py` (sin Qt) y `dialogs/loads.py`; los menús Desplazamientos (restringir X,
Y o las dos, liberar, imponer, el defecto del externo, borrar condición) y Cargas (carga repartida,
puntual, borrar carga, factores por fase) (RF-14, RF-15, RF-16; 004, D6, D7, D10).

- **Se ponen con clics**, como la referencia: se escoge qué y se hace clic en los segmentos o vértices
  hasta Esc. Un clic a menos de 8 píxeles de un vértice lo escoge; si no, el segmento; si no hay nada,
  se dice, con los píxeles (P13). Una carga puntual en un segmento, o una repartida en un vértice, se
  dice y no se hace. Borrar quita la última condición (o carga) de ese sitio.
- **El convenio, junto a cada valor** (RF-16): la normal «+ hacia el terreno», la vertical «+ hacia
  abajo», la horizontal «+ hacia +x», los ángulos antihorarios, ux «+ hacia +x» y uy «+ hacia arriba»;
  la carga puntual, «por metro fuera del plano» (en axisimetría, «del anillo entero»).
- **El defecto del externo se ve** (la referencia lo fijaba sin mostrarlo): en gris, en cada segmento del
  externo que ninguna condición cubre; se cambia en Desplazamientos > Por defecto del externo.
- **Las flechas de una carga** tienen la punta en el contorno y son tan largas como su total en la fase
  sobre el mayor; la normal empuja hacia el terreno: hacia dentro del modelo, hacia fuera de una
  excavación. **Encontrado al probarlo**: en una esquina, la sonda que decide el lado caía sobre el otro
  contorno y una flecha salía al revés; el lado se decide ahora en el centro del segmento.
- **Los factores por fase** (D10), en una tabla: el factor de cada carga y desplazamiento impuesto (vacío:
  no actúa) y si cada restricción actúa; cada cambio es una operación en esa fase sola. La fase que se
  ve dibuja lo que actúa en ella.

7 tests; 23 mutaciones, todas cazadas.

## T28 — importar, recientes y preferencias (2026-11-25)

`ogr_fem2d/gui/dialogs/import_report.py`; en Archivo, «Abrir reciente», «Importar un modelo de OGR
Slip2D...» e «Importar DXF...» (RF-17; D12; ADR-0004).

- **El informe de la conversión se ve entero**, en una ventana junto al modelo: lo que vino, lo que no,
  los valores por defecto tomados (que cambian el resultado: revísalos), lo que se cambió y lo que falta
  en el modelo, cada parte con su cuenta aunque esté vacía.
- **Los recientes**: abrir o guardar un modelo lo pone el primero, sin repetirlo, hasta ocho; uno que ya
  no está se dice y se quita; la lista se vacía desde el mismo menú (deshabilitado si está vacía, con su
  porqué). Una conversión no entra (todavía no tiene archivo). Se guardan en los ajustes de la máquina,
  como el idioma.
- **Las preferencias** (ya conectadas en T20), ahora probadas: un idioma nuevo se guarda y la barra de
  estado dice que se aplica al volver a abrir; un tema se aplica al momento y se guarda.
- **Los tests no dejan estado** (regla 5): `tests/_settings.py` repone la lista de recientes y el estilo
  de la aplicación. El vigilante de fugas lo encontró: abrir un modelo desde la ventana escribía en los
  ajustes de la corrida, y elegir un tema cambiaba el estilo para los tests siguientes.

**Hallazgo (regla 2), para decidir**: las líneas del informe de una conversión las escriben
`import_slip2d` e `import_dxf` en inglés, como texto (no son mensajes con código como los de las
operaciones), así que en español el informe sale con los títulos traducidos y las líneas en inglés.
Propuesta: darles código en `api/messages.py`, como a los mensajes de las operaciones. No se ha cambiado.

3 tests; 14 mutaciones, todas cazadas (una, después de exigir cada parte del informe).

## T29 — cierre de la parte C (2026-11-25)

**El caso 006 dibujado desde cero por la ventana** (`tests/test_gui_case006_v0014.py`), como lo haría un
usuario: los ajustes (MPa), la fase renombrada, el externo escrito con puntos absolutos, relativos y
polares, las ocho divisiones de la faja, el material en MPa asignado con un clic, la superficie libre
(dos segmentos, un tramo), los laterales en x, la carga de la faja y la malla con su diálogo en dos
pasos. **Todo lo que decide el resultado es lo del `modelo.ogrfem2d` del caso**, y **la malla es la misma
bit a bit** (nudos, elementos y regiones).

Para llegar ahí entraron dos piezas que faltaban:

- **Un tramo de varios segmentos es una condición o una carga**: un clic en el segmento que continúa el
  tramo recién puesto (por cualquiera de sus dos extremos) lo alarga, y la barra de estado lo dice. El
  modelo guarda un tramo de vértice a vértice (004, D7); con un clic por segmento la superficie del caso
  habría sido dos condiciones, el mismo resultado con otra huella.
- **Malla > Divisiones del segmento...**: el número de divisiones de los segmentos en que se haga clic
  (0: decide el mallador), que el caso fija en la faja; existía en la operación y no en la ventana (D13).

**Hallazgo (regla 6), para decidir**: la ventana de refinamiento del diálogo se escribe desde su esquina
inferior izquierda, en sentido antihorario; el caso 006 escribió el mismo rectángulo desde la superior
izquierda (el 005 y el 007, cada uno desde otra). La malla es idéntica, pero `model_fingerprint` guarda el
polígono tal como se escribió, así que la huella del modelo dibujado no es la del caso hasta escribir la
ventana como el caso. El test lo comprueba así, y comprueba que con eso la huella es la misma. Propuesta:
o la huella toma el polígono de una ventana en una forma canónica (su vértice menor primero, antihorario),
o se acepta como está (no cambia ningún número). Cualquiera de las dos toca la 004 y sus casos: no se ha
hecho nada.

### La regla 7, diálogo a diálogo

Cada opción de la parte C con el test que demuestra que mueve el modelo (o lo dibujado):

| Diálogo o herramienta | Opciones | Test |
|---|---|---|
| Ajustes del proyecto | análisis, unidades, título, autor, fecha, notas | `test_gui_settings_v0014`, `test_each_choice_moves_the_model` |
| Fases | añadir (detrás de la que se ve), renombrar, borrar | `test_gui_settings_v0014`, `test_add_rename_delete` |
| Unidades mostradas | cursor, punto escrito, tabla, rejilla | `test_gui_settings_v0014`, `test_feet_are_shown_and_read_and_the_values_kept` |
| Tensión de campo | tipo, σ1, σ3, σz, ángulo, superficie, base, γ, K, Kz, añadir y quitar estrato | `test_gui_field_v0014` (tres tests) |
| Malla | tipo, elemento, B, nudos, lado máximo, tamaño, número, ventana | `test_gui_mesh_v0014`, `test_each_setting_moves_the_mesh` |
| Divisiones del segmento | el número | `test_gui_loads_v0014`, `test_a_stretch_grows_both_ways_and_divisions` |
| Materiales | nombre, color, carga inicial, γ, E, ν; añadir, borrar | `test_gui_materials_v0014`, `test_add_each_field_and_delete` |
| Asignación | material, excavar, rellenar, solo esta fase | `test_gui_materials_v0014`, `test_assign_excavate_fill_by_clicks` |
| Condiciones | X, Y, XY, libre, ux, uy, defecto del externo, borrar | `test_gui_loads_v0014`, `TestConditions` |
| Cargas | magnitud, final, orientación, ángulo, puntual, borrar | `test_gui_loads_v0014`, `TestLoads` |
| Factores por fase | factor de carga, de desplazamiento (vacío: no actúa), restricción activa | `test_gui_loads_v0014`, `test_the_arrows`, `test_condition_factors_by_stage` |
| Entrada de geometría | absoluto, relativo, polar, coma decimal, tabla, círculo, arco, vértices | `test_gui_tools_v0014` |
| Recientes y preferencias | abrir, guardar, repetido, falta, vaciar; idioma, tema | `test_gui_files_v0014` |

En la parte C se corrieron **140 mutaciones** (T22 a T29), todas cazadas salvo tres equivalentes cuyo
código se quitó; las que escaparon al principio se cuentan en cada tarea, con el test que las caza ahora.

### La lista de la guía, componente a componente

- **Acciones**: todas en un menú (regla 3, `ogr_ui.testing.menus`), con `tr()` y su español (regla 2);
  las deshabilitadas, con su porqué en la barra de estado; los nombres e iconos de Slip2D donde hacen lo
  mismo (contornos, vértices, materiales, asignar, cargas). Atajos: los de la referencia (Ctrl+U
  ajustes de la malla, Ctrl+M mallar, Ctrl+A asignar).
- **Diálogos**: título con lo que se edita; campos en bloques con título; cada número con su unidad en
  el campo y, en tensiones, cargas y desplazamientos, el convenio junto al campo (RF-16); los valores
  salen del modelo, y los que no tienen fuente no tienen defecto (los nudos de la graduada; E, ν; γ, K y
  Kz de un estrato); botón principal con el verbo (Aplicar, Escoger dónde, Añadir los vértices); un
  rechazo se dice en el diálogo, que se queda abierto. Probados sin pantalla y sin `exec()`.
- **Lienzo**: respuesta con la malla del 005 (T21: cursor y zum por debajo de 0.1 s); colores y trazos
  por tipo, también de condiciones, cargas, bloque del campo y malla de otra geometría; marcas en
  píxeles. *Pendiente*: la selección resaltada no existe todavía (se escoge por clic y se actúa al
  momento); llegará con la consulta de la parte D.
- **Proceso largo**: mallar es síncrono (hallazgo de T25, para decidir); calcular es la parte D.
- **Mensajes**: dicen qué pasó, dónde y cómo seguir (los estados vacíos de la barra de estado: sin
  modelo, sin malla, malla de otra geometría); se dicen una vez, en la barra de estado.

### Lo que queda para decidir antes de la parte D

1. Mallar síncrono (T25): ¿trabajo en subproceso o se acepta en la fase 1?
2. Las líneas del informe de una conversión, en inglés (T28): ¿con código en `api/messages.py`?
3. La huella y el orden de los vértices de una ventana de refinamiento (T29).
4. Pedido a OGR-GUI (T22): el campo de X, Y con relativos, polares y coma decimal; y antes, el percentil
   de «Fit to results» y el español de `API_MESSAGES` (T19).
