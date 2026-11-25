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
