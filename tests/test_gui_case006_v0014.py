# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.14 (spec 006, T29) — the close of part C: case 006 (a strip load on a
half-space, general mesh) drawn from nothing by the window's actions, as a
user would: its settings, its boundary typed, the divisions of the strip,
its material, the assignment by a click, the conditions and the load by
clicks, the mesh by its dialog in two steps.

Invariants protected:

* **the model drawn is the case's**: its fingerprint
  (``fingerprint.model_fingerprint``: geometry, material, assignment,
  stages, field, conditions, loads, mesh settings and the mesh itself) is
  that of ``validacion/casos/006-carga-en-faja-malla-general/
  modelo.ogrfem2d``, and its mesh is the same bit for bit;
* **a refinement window is one however written**: the dialog writes the
  rectangle from its lower left corner and the case from its upper left
  one; the fingerprint and the mesher take one form of it (T29's finding,
  solved);
* **a stretch of several segments is one condition**: the free surface is
  two segments, clicked one after the other.
"""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import _cases_model  # noqa: E402
from ogr_fem2d.gui.canvas import controller as tc  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402
from ogr_fem2d.model import fingerprint, ogr_file  # noqa: E402
from ogr_fem2d.model import model as md  # noqa: E402

APP = QApplication.instance() or QApplication([])
LEFT = Qt.MouseButton.LeftButton
CASE = "006-carga-en-faja-malla-general"
_KEEP = []


def _typed(w, *texts):
    for text in texts:
        w.statusBar().coord_input.setText(text)
        w.statusBar().coord_input.returnPressed.emit()


def _draw_case_006(w):
    w.act_new()
    dlg = w.project_settings_dialog()
    dlg.units.setCurrentIndex(dlg.units.findData("metric_mpa"))
    dlg.title_edit.setText("Caso 006 dibujado")
    dlg._accept()
    w.ask_text = lambda *_a: "Carga"
    w.actions_by_key["stage_rename"].trigger()
    # the external, typed
    w.actions_by_key["add_external"].trigger()
    _typed(w, "0, -200", "@200, 0", "@200<90", "1, 0", "0, 0")
    w.tools.key(Qt.Key.Key_Return)
    w.view.resize(800, 600)
    w.view.show_extent(-3.0, -3.0, 4.0, 3.0)     # the strip, 1 m, many pixels long
    # the strip, in 8 divisions
    w.ask_int = lambda *_a: 8
    w.actions_by_key["segment_divisions"].trigger()
    w.tools.clicked(0.5, 0.0, LEFT)
    w.tools.key(Qt.Key.Key_Escape)
    # the material, in MPa, assigned by a click
    mats = w.materials_dialog()
    mats.add()
    mats.name.setText("Semiespacio")
    mats.E.box.setValue(20000.0)
    mats.nu.box.setValue(0.2)
    mats.apply_shown()
    mid = w.session.model.materials[0].id
    w.act_assign()
    w.assign_panel.choose(("material", mid))
    w.tools.clicked(100.0, -100.0, LEFT)
    w.tools.key(Qt.Key.Key_Escape)
    # the conditions: the surface free (two segments, one stretch), the sides in x
    w.actions_by_key["release"].trigger()
    w.tools.clicked(100.0, 0.0, LEFT)
    w.tools.clicked(0.5, 0.0, LEFT)
    w.tools.key(Qt.Key.Key_Escape)
    w.actions_by_key["restrain_x"].trigger()
    w.tools.clicked(200.0, -100.0, LEFT)
    w.tools.key(Qt.Key.Key_Escape)
    w.actions_by_key["restrain_x"].trigger()
    w.tools.clicked(0.0, -100.0, LEFT)
    w.tools.key(Qt.Key.Key_Escape)
    # the strip load, 1 MPa normal
    loads = w.load_dialog("distributed")
    loads.magnitude.box.setValue(1.0)
    w.tools.start_place({"op": "load_set", **loads.params()})
    w.tools.clicked(0.5, 0.0, LEFT)
    w.tools.key(Qt.Key.Key_Escape)
    # the mesh, by its dialog: graded, T6, 4 nodes, longest edge 6.25 m, a window
    mesh = w.mesh_setup_dialog()
    mesh.nodes.setValue(4)
    mesh.max_size.setValue(6.25)
    mesh.window_add.click()
    for c, text in enumerate(("0", "-6", "6", "0", "0.125")):
        mesh.windows.item(0, c).setText(text)
    mesh.do_discretize()
    mesh.do_mesh()
    return w.session.model


class TestCase006ByTheWindow:
    def test_the_model_is_the_cases(self):
        w = MainWindow()
        _KEEP.append(w)
        try:
            drawn = _draw_case_006(w)
            assert w.tools.mode == tc.NONE
            case = ogr_file.read(_cases_model.path(CASE))
            # each part, to say which one differs if one does
            assert drawn.analysis == case.analysis and drawn.field == case.field
            assert [b.vertices for b in drawn.boundaries] == [b.vertices for b in case.boundaries]
            assert [b.segments for b in drawn.boundaries] == [b.segments for b in case.boundaries]
            assert [(x.E, x.nu, x.unit_weight, x.initial_loading) for x in drawn.materials] == \
                [(x.E, x.nu, x.unit_weight, x.initial_loading) for x in case.materials]
            assert [(a.point, a.excavated) for a in drawn.assignments] == \
                [(a.point, a.excavated) for a in case.assignments]
            strip = lambda c: (c.kind, c.span.start, c.span.end, c.active)  # noqa: E731
            assert [strip(c) for c in drawn.conditions] == [strip(c) for c in case.conditions]
            assert drawn.default_restraint == case.default_restraint
            assert [(ld.span.start, ld.span.end, ld.start_value, ld.end_value, ld.orientation,
                     ld.factors) for ld in drawn.loads] == [
                (ld.span.start, ld.span.end, ld.start_value, ld.end_value, ld.orientation,
                 ld.factors) for ld in case.loads]
            # the window: the same rectangle, written from another corner
            (dw,), (cw,) = drawn.mesh_settings.windows, case.mesh_settings.windows
            assert dw.size == cw.size and set(dw.polygon) == set(cw.polygon)
            assert dw.polygon != cw.polygon
            # the mesh, bit for bit, and the fingerprint: the same model
            assert drawn.mesh.nodes == case.mesh.nodes
            assert drawn.mesh.elements == case.mesh.elements
            assert drawn.mesh.element_region == case.mesh.element_region
            assert fingerprint.model_fingerprint(drawn) == fingerprint.model_fingerprint(case)
        finally:
            w.confirm_discard = lambda: True
            w.close()
