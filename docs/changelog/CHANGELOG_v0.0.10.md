# OGR FEM2D v0.0.10

**Fija `ogr-core` v0.2.7** (2026-11-24): su lector DXF conserva los arcos si se le pide
(`read_dxf(..., keep_arcs=True)`), lo que la spec 004 pidió en su D13. Una subida de fijación va en un
commit suyo; el uso de los arcos en `ogr_fem2d/model/import_dxf.py`, en el siguiente.

## La fijación

- `pyproject.toml`, `README.md`, `AGENTS.md`, `tech-stack.md` y `roadmap.md`, a `v0.2.7`; el `.venv`,
  reinstalado desde la etiqueta con `--no-deps --force-reinstall`; las listas de versiones de
  `tests/test_project_setup_v001.py`, escritas para la fijación nueva.
- **Lo que trae y nos toca**: nada obligatorio. Con el modo por defecto el lector aplana como siempre,
  y en la salida aplanada solo cambian los dibujos con un *bulge* de más de media vuelta o con una
  `POLYLINE` 2-D con *bulge*, que antes se leían mal. Ningún test de FEM2D trae uno.
- Queda abierto en el núcleo: la extrusión negativa (OCS) de `ARC`, `CIRCLE` y `LWPOLYLINE`, que se
  lee reflejada en x (su changelog, §4). Lo decide la propietaria.
- La suite de FEM2D contra el núcleo de la PR la corrió la sesión de OGR-Core (493 de 493 contra
  `5ec7d97` y contra `5dd480d`). Aquí, la suite entera contra la etiqueta instalada: 493 de 493
  (`shared: ogr_core 0.2.7 … (installed, no git tree)`).
- La fila de FEM2D en `docs/consumidores.md` de OGR-Core se corrige allí (su sesión).
- **Hallazgo al subir la versión**: `test_read_and_written_again_the_same_bytes` comparaba los
  `modelo.ogrfem2d` de los casos byte a byte, `written_by` incluido, y la v0.0.10 escribe su nombre. El
  contenido es la identidad, no quién lo escribió (la huella del documento tampoco lo cuenta, D12): el
  test compara ahora todas las líneas menos esa. Los archivos no se reescriben con cada versión.
