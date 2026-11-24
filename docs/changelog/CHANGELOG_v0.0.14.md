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
