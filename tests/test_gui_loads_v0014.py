# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.14 (spec 006, T27) — the conditions and the loads: restrain in X, in
Y or in both, release, impose; distributed and point loads with their
orientation and their factor by stage; their drawing (RF-14, RF-15, RF-16;
spec 004, D6, D7, D10).

Invariants protected:

* **every option moves the model** (rule 7): each restraint, a release, ux
  and uy of an imposed displacement, the default of the external, the
  magnitude, its end, the orientation and the angle of a load, a factor
  and an activity by stage, deleting a condition and a load;
* **picking works in pixels and says so**: a click within ``PICK_PX``
  pixels of a vertex puts the thing on the vertex, else on the segment; a
  click that picks nothing says so; a point load on a segment, or a
  distributed one on a vertex, is said, not done;
* **the convention is written** next to each value of the dialogs (RF-16);
* **the external's default restraint is seen** on the canvas (the
  reference program fixed it without showing it), and leaves the segments
  a condition covers;
* **the arrows of a load**: their tip on the boundary, a NORMAL one into
  the ground (into the model, out of an excavation), as long as the total
  of the stage over the largest; a factor 0 takes them off.
"""
from __future__ import annotations

import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QFormLayout  # noqa: E402

from ogr_fem2d.gui.canvas import controller as tc  # noqa: E402
from ogr_fem2d.gui.canvas import marks  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402
from ogr_fem2d.model import model as md  # noqa: E402

APP = QApplication.instance() or QApplication([])
LEFT = Qt.MouseButton.LeftButton
_KEEP = []


def _window():
    w = MainWindow()
    w.resize(900, 700)
    w.show()
    _KEEP.append(w)
    w.act_new()
    w.do("boundary_add", type=md.EXTERNAL, closed=True,
         points_xy=[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]])
    w.do("boundary_add", type=md.EXCAVATION, closed=True,
         points_xy=[[4.0, 4.0], [6.0, 4.0], [6.0, 6.0], [4.0, 6.0]])
    w.view.zoom_all()
    return w


def _close(w):
    w.confirm_discard = lambda: True
    w.close()


class TestConditions:
    def test_each_restraint_and_release_by_clicks(self):
        w = _window()
        try:
            for key, kind in (("restrain_x", md.X), ("restrain_y", md.Y),
                              ("restrain_xy", md.XY), ("release", md.FREE)):
                n = len(w.session.model.conditions)
                w.actions_by_key[key].trigger()
                assert w.tools.mode == tc.PLACE
                assert "8 pixels" in w.statusBar().currentMessage()
                w.tools.clicked(5.0, 0.05, LEFT)                       # the bottom segment
                c = w.session.model.conditions[n]
                assert c.kind == kind and c.span == md.Span("ext1", (0.0, 0.0), (10.0, 0.0))
                w.tools.key(Qt.Key.Key_Escape)
            # a vertex, within the pixels
            w.actions_by_key["restrain_x"].trigger()
            off = 3.0 / w.view.pixels_per_unit()
            w.tools.clicked(10.0 - off, 10.0, LEFT)
            assert w.session.model.conditions[-1].vertex == (10.0, 10.0)
            # nothing there: said
            w.tools.clicked(20.0, 20.0, LEFT)
            assert "No boundary within 8 pixels" in w.statusBar().currentMessage()
            # delete: the last one on that segment
            n = len(w.session.model.conditions)
            w.actions_by_key["delete_condition"].trigger()
            w.tools.clicked(5.0, 0.05, LEFT)
            assert len(w.session.model.conditions) == n - 1
            assert w.session.model.conditions[-2].kind == md.XY      # free went
            w.tools.clicked(5.0, 9.95, LEFT)                         # none on the top
            assert "Nothing of that kind" in w.statusBar().currentMessage()
        finally:
            _close(w)

    def test_impose_and_the_default(self):
        w = _window()
        try:
            dlg = w.impose_dialog()
            form = dlg.form
            assert isinstance(form, QFormLayout)
            assert "+ towards +x" in form.labelForField(dlg.ux.box).text()
            assert "+ upward" in form.labelForField(dlg.uy.box).text()
            assert dlg.params() == {"kind": md.DISPLACEMENT}
            dlg.uy.box.setValue(-0.01)
            assert dlg.params() == {"kind": md.DISPLACEMENT, "uy": -0.01}
            dlg.ux.box.setValue(0.002)
            w.tools.start_place({"op": "condition_set", **dlg.params()})
            w.tools.clicked(5.0, 9.95, LEFT)
            c = w.session.model.conditions[-1]
            assert (c.kind, c.ux, c.uy) == (md.DISPLACEMENT, 0.002, -0.01)
            # the default of the external
            assert w.session.model.default_restraint == md.XY
            w.ask_choice = lambda *_a: list(md.RESTRAINTS).index(md.Y)
            w.act_default_restraint()
            assert w.session.model.default_restraint == md.Y
        finally:
            _close(w)

    def test_the_default_is_seen_and_leaves_what_a_condition_covers(self):
        w = _window()
        try:
            default = [i for i in w.view.condition_items if i.data(0)[2]]
            assert len(default) == 4 and all(i.data(0)[1] == md.XY for i in default)
            w.do("condition_set", kind=md.X, boundary="ext1", start=[0.0, 0.0], end=[10.0, 0.0])
            default = [i for i in w.view.condition_items if i.data(0)[2]]
            assert len(default) == 3
            mine = [i for i in w.view.condition_items if not i.data(0)[2]]
            assert {i.data(0)[1] for i in mine} == {md.X} and len(mine) == 3   # ends and middle
            # not active in a stage: not drawn there
            w.do("stage_add")
            w.do("condition_stage", condition=0, stage="2", active=False)
            w.stage_tabs.setCurrentIndex(1)
            assert not [i for i in w.view.condition_items if not i.data(0)[2]]
        finally:
            _close(w)


class TestLoads:
    def test_distributed_each_option(self):
        w = _window()
        try:
            dlg = w.load_dialog("distributed")
            form = dlg.form
            names = [dlg.orientation.itemText(k) for k in range(dlg.orientation.count())]
            assert "Normal to the boundary (+ into the ground)" in names
            assert not dlg.angle.box.isEnabled()
            dlg.magnitude.box.setValue(100.0)
            p = dlg.params()
            assert p == {"kind": "distributed", "magnitude": 100.0, "orientation": md.NORMAL}
            dlg.magnitude_end.box.setValue(50.0)
            dlg.orientation.setCurrentIndex(dlg.orientation.findData(md.ANGLE_FROM_HORIZONTAL))
            assert dlg.angle.box.isEnabled()
            dlg.angle.box.setValue(30.0)
            p = dlg.params()
            assert (p["magnitude_end"], p["orientation"], p["angle"]) == (
                50.0, md.ANGLE_FROM_HORIZONTAL, 30.0)
            assert form.labelForField(dlg.magnitude.box).text() == "Magnitude at the start"
            w.tools.start_place({"op": "load_set", **p})
            w.tools.clicked(5.0, 9.95, LEFT)
            ld = w.session.model.loads[-1]
            assert (ld.start_value, ld.end_value, ld.orientation, ld.angle) == (
                100.0, 50.0, md.ANGLE_FROM_HORIZONTAL, 30.0)
            assert ld.span == md.Span("ext1", (10.0, 10.0), (0.0, 10.0))
            # on a vertex: said, not done
            n = len(w.session.model.loads)
            w.tools.clicked(10.0, 10.0, LEFT)
            assert "goes on a segment" in w.statusBar().currentMessage()
            assert len(w.session.model.loads) == n
        finally:
            _close(w)

    def test_point_load_and_delete(self):
        w = _window()
        try:
            dlg = w.load_dialog("point")
            form = dlg.form
            assert "per metre out of the plane" in form.labelForField(dlg.magnitude.box).text()
            assert dlg.magnitude.box.suffix() == " kN"
            dlg.magnitude.box.setValue(10.0)
            dlg.orientation.setCurrentIndex(dlg.orientation.findData(md.HORIZONTAL))
            w.tools.start_place({"op": "load_set", **dlg.params()})
            w.tools.clicked(5.0, 9.95, LEFT)                          # a segment: said
            assert "goes on a vertex" in w.statusBar().currentMessage()
            w.tools.clicked(10.0, 10.0, LEFT)
            ld = w.session.model.loads[-1]
            assert (ld.vertex, ld.magnitude, ld.orientation) == ((10.0, 10.0), 10.0, md.HORIZONTAL)
            w.actions_by_key["delete_load"].trigger()
            w.tools.clicked(10.0, 10.0, LEFT)
            assert w.session.model.loads == ()
        finally:
            _close(w)

    def test_the_arrows(self):
        w = _window()
        try:
            w.do("load_set", kind="distributed", magnitude=100.0, boundary="ext1",
                 start=[10.0, 10.0], end=[0.0, 10.0])                  # the top, normal
            w.do("load_set", kind="distributed", magnitude=50.0, boundary="exc1",
                 start=[4.0, 4.0], end=[6.0, 4.0])                     # the hole's bottom
            arrows = marks.load_arrows(w.session.model)
            top = [a for a in arrows if a.load == 0]
            assert all(a.tip[1] == 10.0 and a.tail[1] > 10.0 for a in top)    # pushes down
            hole = [a for a in arrows if a.load == 1]
            assert all(a.tip[1] == 4.0 and a.tail[1] > 4.0 for a in hole)      # into the rock
            length = lambda a: math.dist(a.tail, a.tip)  # noqa: E731
            assert abs(length(top[0]) - 2 * length(hole[0])) < 1e-9
            assert {i.data(0) for i in w.view.load_items} == {("load", 0), ("load", 1)}
            # the factors by stage
            w.do("stage_add")
            dlg = w.stage_factors_dialog()
            dlg.table.item(0, 1).setText("0")
            dlg.table.item(1, 1).setText("2")
            dlg._accept()
            assert w.session.model.loads[0].factors == (1.0, 0.0)
            assert w.session.model.loads[1].factors == (1.0, 2.0)
            w.stage_tabs.setCurrentIndex(1)
            assert {i.data(0) for i in w.view.load_items} == {("load", 1)}
        finally:
            _close(w)

    def test_condition_factors_by_stage(self):
        w = _window()
        try:
            w.do("condition_set", kind=md.X, boundary="ext1", start=[0.0, 0.0], end=[10.0, 0.0])
            w.do("condition_set", kind=md.DISPLACEMENT, vertex=[10.0, 10.0], uy=-0.01)
            w.do("stage_add")
            dlg = w.stage_factors_dialog()
            r_restraint, r_imposed = dlg.rows.index(("condition", 0)), dlg.rows.index(
                ("condition", 1))
            dlg.table.item(r_restraint, 1).setCheckState(Qt.CheckState.Unchecked)
            dlg.table.item(r_imposed, 1).setText("")
            dlg._accept()
            c0, c1 = w.session.model.conditions
            assert c0.active == (True, False) and c1.factors == (1.0, None)
            dlg = w.stage_factors_dialog()
            dlg.table.item(r_imposed, 0).setText("x")
            dlg._accept()
            assert "write a number" in dlg.error.text()
        finally:
            _close(w)
