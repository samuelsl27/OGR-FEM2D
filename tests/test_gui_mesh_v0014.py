# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.14 (spec 006, T25) — the mesh in two steps: its settings, discretize,
mesh, reset; its drawing and its notes (RF-14, RF-20; spec 003; P10).

Invariants protected:

* **every setting moves the mesh** (rule 7): the kind, the element, B, the
  nodes on the excavations, the longest edge, the uniform size, the number
  of elements, a window; each a ``mesh_settings`` of only what changed;
* **two steps**: Discretize draws the nodes the boundaries will have and
  counts them, without changing the model; Mesh is enabled only after it;
* **no default that moves the number** (guide §10): the nodes on the
  excavations start empty, and meshing without them is refused, saying
  why, in the dialog;
* **B and the notes of the mesher are in view** (rule 12): the dialog says
  the smallest angle B guarantees (arcsin(1/2B), Shewchuk 2002a); the
  status bar says the mesh's size, and its tooltip B, the smallest angle
  and the warnings;
* **a mesh of another geometry is kept and marked** (P10; 004, RF-11): an
  edit leaves it, drawn dashed in another colour, and the status bar says
  so; reset takes it away (one step to undo).
"""
from __future__ import annotations

import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from ogr_fem2d.gui.dialogs.mesh_setup import guaranteed_angle  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402
from ogr_fem2d.mesh import geometry as g  # noqa: E402
from ogr_fem2d.model import model as md  # noqa: E402

APP = QApplication.instance() or QApplication([])
_KEEP = []


def _window():
    """A square with a square hole: small, meshed in a moment."""
    w = MainWindow()
    _KEEP.append(w)
    w.act_new()
    w.do("boundary_add", type=md.EXTERNAL, closed=True,
         points_xy=[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]])
    w.do("boundary_add", type=md.EXCAVATION, closed=True,
         points_xy=[[4.0, 4.0], [6.0, 4.0], [6.0, 6.0], [4.0, 6.0]])
    mat = w.do("material_set", name="rock", E=1e6, nu=0.25)["material"]
    w.do("material_assign", material=mat, x=1.0, y=1.0)
    w.do("material_assign", material=mat, x=5.0, y=5.0)
    return w


def _close(w):
    w.confirm_discard = lambda: True
    w.close()


def _mesh(w, change=None):
    dlg = w.mesh_setup_dialog()
    if change:
        change(dlg)
    dlg.do_discretize()
    assert dlg.mesh_button.isEnabled(), dlg.error.text()
    dlg.do_mesh()
    assert dlg.result() == 1, dlg.error.text()
    return w.session.model.mesh


class TestTheDialog:
    def test_no_default_for_the_nodes(self):
        w = _window()
        try:
            dlg = w.mesh_setup_dialog()
            assert not dlg.mesh_button.isEnabled()          # discretize first
            assert dlg.nodes.value() == 0 and dlg.nodes.text() == "(to be given)"
            dlg.do_discretize()
            assert "boundary_nodes" in dlg.error.text() and not dlg.mesh_button.isEnabled()
            assert w.session.model.mesh is None
        finally:
            _close(w)

    def test_each_setting_moves_the_mesh(self):
        w = _window()
        try:
            base = _mesh(w, lambda d: d.nodes.setValue(16))
            assert w.session.model.mesh_settings.boundary_nodes == 16
            sig = lambda mesh: (len(mesh.nodes), len(mesh.elements), len(mesh.elements[0]))  # noqa
            settings = [
                ("nodes", lambda d: d.nodes.setValue(32)),
                ("element", lambda d: d.element.setCurrentIndex(d.element.findData(3))),
                ("bound", lambda d: d.bound.setValue(3.0)),
                ("max_size", lambda d: d.max_size.setValue(0.5)),
                ("window", lambda d: (d.window_add.click(),
                                      [d.windows.item(0, c).setText(t) for c, t in
                                       enumerate(("0", "0", "3", "3", "0,2"))])),
                ("uniform size", lambda d: (d.kind.setCurrentIndex(d.kind.findData(g.UNIFORM)),
                                            d.by_size.setChecked(True), d.size.setValue(1.0))),
                ("uniform count", lambda d: (d.kind.setCurrentIndex(d.kind.findData(g.UNIFORM)),
                                             d.by_count.setChecked(True),
                                             d.count.setValue(400))),
            ]
            kept = {"nodes": ("boundary_nodes", 32), "element": ("nodes_per_element", 3),
                    "bound": ("quality_bound", 3.0), "max_size": ("max_size", 0.5),
                    "uniform size": ("size", 1.0), "uniform count": ("elements", 400)}
            for name, change in settings:
                steps = len(w.session.history()[0])
                mesh = _mesh(w, change)
                if name in kept:
                    setting, want = kept[name]
                    assert getattr(w.session.model.mesh_settings, setting) == want, name
                assert sig(mesh) != sig(base) or mesh.nodes != base.nodes, name
                assert len(w.session.history()[0]) == steps + 2, name   # settings, mesh
                w.act_undo()
                w.act_undo()
                assert w.session.model.mesh == base, name
            # in feet: the longest edge written in feet, kept in metres
            w.do("project_settings", units="imperial_ksf")
            dlg = w.mesh_setup_dialog()
            assert dlg.max_size.suffix() == " ft"
            dlg.max_size.setValue(2.0)
            dlg._accept()
            assert abs(w.session.model.mesh_settings.max_size - 2 * 0.3048) < 1e-12
            # the window, kept as it was when not touched; a polygon kept as it is
            w.do("mesh_settings", windows=[{"polygon": [[0, 0], [3, 0], [0, 3]], "size": 0.2}])
            dlg = w.mesh_setup_dialog()
            assert "polygon of 3" in dlg.windows.item(0, 0).text()
            assert "windows" not in dlg.changes()
        finally:
            _close(w)

    def test_b_says_its_angle(self):
        assert abs(guaranteed_angle(math.sqrt(2.0)) - 20.7048) < 1e-4
        w = _window()
        try:
            dlg = w.mesh_setup_dialog()
            assert "20.7°" in dlg.bound_note.text()
            dlg.bound.setValue(2.0)
            assert "14.5°" in dlg.bound_note.text()
        finally:
            _close(w)


class TestStepsAndState:
    def test_discretize_draws_and_counts(self):
        w = _window()
        try:
            w.do("mesh_settings", boundary_nodes=16)
            steps = len(w.session.history()[0])
            w.act_discretize()
            item = w.view.discretization_item
            assert item is not None and item.data(0)[0] == "discretization"
            n = item.data(0)[1]
            assert n >= 16 + 4 and f"{n} nodes" in w.statusBar().currentMessage()
            assert len(w.session.history()[0]) == steps and w.session.model.mesh is None
        finally:
            _close(w)

    def test_the_status_bar_and_a_stale_mesh(self):
        w = _window()
        try:
            assert w.mesh_label.text().startswith("No mesh")
            assert not w.actions_by_key["mesh_reset"].isEnabled()
            w.do("mesh_settings", boundary_nodes=16)
            w.act_mesh()
            m = w.session.model
            assert w.mesh_label.text() == "Mesh: %d nodes, %d elements T6" % (
                len(m.mesh.nodes), len(m.mesh.elements))
            tip = w.mesh_label.toolTip()
            assert "B = 1.414" in tip and "20.7°" in tip and "Smallest angle of the mesh" in tip
            assert "Meshed:" in w.statusBar().currentMessage()
            assert not w.view.mesh_item.stale
            # an edit: the mesh is kept, marked
            w.do("project_settings", title="x")
            w.do("boundary_edit", boundary="exc1", op="move_vertex", point_xy=[4.0, 4.0],
                 to_xy=[3.5, 4.0])
            assert w.session.model.mesh is not None
            assert w.mesh_label.text().startswith("Mesh of another geometry")
            assert w.view.mesh_item.stale
            # reset: one step
            assert w.actions_by_key["mesh_reset"].isEnabled()
            w.actions_by_key["mesh_reset"].trigger()
            assert w.session.model.mesh is None and w.mesh_label.text().startswith("No mesh")
            w.act_undo()
            assert w.session.model.mesh is not None
        finally:
            _close(w)
