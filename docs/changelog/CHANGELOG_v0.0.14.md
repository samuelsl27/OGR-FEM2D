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
