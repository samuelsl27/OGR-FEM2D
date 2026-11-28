# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.14 (spec 006, T24) — the field stress: its dialog and its block drawn
(RF-14, RF-15, RF-16; spec 004, D5, D6 and D14).

Invariants protected:

* **every field of the dialog moves the model** (rule 7): sigma_1,
  sigma_3, sigma_z, the angle; the kind; the surface, and each column of a
  stratum; adding and removing a stratum. Each change is ONE ``field_set``;
  nothing changed is no operation;
* **the convention is written next to every stress** (RF-16): compression
  positive, in the label of each of the three; the units, in each box;
* **what is shown is in the model's units, what is kept is in kPa**: in
  ksf a sigma_1 written as 1 is 47.88 kPa; a value not touched goes back
  exactly as it was (no rounding through what is shown);
* **a refusal is said in the dialog**, which stays open: sigma_1 < sigma_3;
  a cell that is not a number names its stratum;
* **the block draws what is kept**: a constant field is a square turned by
  the angle with arrows as long as each stress over the largest, in for
  compression and out for tension; a gravitational field is the surface
  and each stratum's bottom.
"""
from __future__ import annotations

import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from ogr_fem2d.gui.canvas import paths  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402
from ogr_fem2d.model import model as md  # noqa: E402

APP = QApplication.instance() or QApplication([])
KSF = 47.880258980335840       # kPa in one ksf (1 kip = 4.4482216 kN, 1 ft = 0.3048 m)
_KEEP = []


def _window(with_model=True):
    w = MainWindow()
    _KEEP.append(w)
    w.act_new()
    if with_model:
        w.do("boundary_add", type=md.EXTERNAL, closed=True,
             points_xy=[[0.0, -20.0], [40.0, -20.0], [40.0, 0.0], [0.0, 0.0]])
    return w


def _close(w):
    w.confirm_discard = lambda: True
    w.close()


def _set_cell(dlg, r, c, text):
    dlg.strata.item(r, c).setText(text)


class TestTheDialog:
    def test_each_field_of_the_constant_one(self):
        w = _window()
        try:
            w.do("field_set", kind="constant", sigma_1=10.0, sigma_3=5.0, sigma_z=6.0, angle=0.0)
            cases = [("sigma_1", 12.0), ("sigma_3", 4.0), ("sigma_z", 7.0), ("angle", 30.0)]
            for name, value in cases:
                before = w.session.model.field
                dlg = w.field_stress_dialog()
                getattr(dlg, name).box.setValue(value)
                dlg._accept()
                after = w.session.model.field
                assert getattr(after, name) == value and getattr(before, name) != value, name
                others = [n for n, _v in cases if n != name]
                assert all(getattr(after, n) == getattr(before, n) for n in others), name
                w.act_undo()
            steps = len(w.session.history()[0])
            dlg = w.field_stress_dialog()
            assert dlg.changes() == {}
            dlg._accept()
            assert len(w.session.history()[0]) == steps
        finally:
            _close(w)

    def test_the_convention_and_the_units_are_written(self):
        w = _window()
        try:
            dlg = w.field_stress_dialog()
            from PySide6.QtWidgets import QFormLayout
            form = dlg.sigma_1.box.parent().layout()
            assert isinstance(form, QFormLayout)
            for n in ("sigma_1", "sigma_3", "sigma_z"):
                label = form.labelForField(getattr(dlg, n).box).text()
                assert "compression +" in label, label
                assert getattr(dlg, n).box.suffix() == " kPa"
            assert dlg.angle.box.suffix() == " °"
            assert dlg.strata.horizontalHeaderItem(0).text() == "Bottom (m)"
        finally:
            _close(w)

    def test_gravity_each_column_and_the_rows(self):
        w = _window()
        try:
            dlg = w.field_stress_dialog()
            dlg.gravity.setChecked(True)
            assert dlg.strata.rowCount() == 1
            assert dlg.strata.item(0, 0).text() == "-20"          # the bottom of the model
            assert dlg.surface.box.value() == 0.0                 # its top
            _set_cell(dlg, 0, 2, "0,5")              # a decimal comma is refused (D12, 2026-11-28)
            dlg._accept()
            assert "Stratum 1" in dlg.error.text(), dlg.error.text()
            assert not isinstance(w.session.model.field, md.GravityField)
            for c, text in ((1, "20"), (2, "0.5"), (3, "0.6")):
                _set_cell(dlg, 0, c, text)
            dlg._accept()
            f = w.session.model.field
            assert f == md.GravityField(0.0, (md.Stratum(-20.0, 20.0, 0.5, 0.6),))
            # each column, the surface, a row added and one removed: each moves the model
            for change, read in (
                    (lambda d: _set_cell(d, 0, 0, "-15"), lambda f: f.strata[0].bottom),
                    (lambda d: _set_cell(d, 0, 1, "21"), lambda f: f.strata[0].unit_weight),
                    (lambda d: _set_cell(d, 0, 2, "0.7"), lambda f: f.strata[0].k),
                    (lambda d: _set_cell(d, 0, 3, "0.8"), lambda f: f.strata[0].kz),
                    (lambda d: d.surface.box.setValue(2.0), lambda f: f.surface),
                    (lambda d: (d.strata_add.click(),
                                [_set_cell(d, 1, c, t)
                                 for c, t in enumerate("-40 22 1 1".split())]),
                     lambda f: len(f.strata))):
                before = w.session.model.field
                dlg = w.field_stress_dialog()
                change(dlg)
                dlg._accept()
                assert read(w.session.model.field) != read(before)
            assert len(w.session.model.field.strata) == 2
            dlg = w.field_stress_dialog()
            dlg.strata.setCurrentCell(1, 0)                     # the one chosen goes
            dlg.strata_remove.click()
            dlg._accept()
            assert [s.bottom for s in w.session.model.field.strata] == [-15.0]
            # a value not touched goes back exactly, not as shown (6 figures)
            w.do("field_set", kind="gravity", surface=0.0,
                 strata=[{"bottom": -20.0, "unit_weight": 20.123456789, "k": 0.5, "kz": 0.5}])
            dlg = w.field_stress_dialog()
            assert dlg.strata.item(0, 1).text() == "20.1235"
            _set_cell(dlg, 0, 2, "0.7")
            dlg._accept()
            assert w.session.model.field.strata[0] == md.Stratum(-20.0, 20.123456789, 0.7, 0.5)
            # back to constant
            dlg = w.field_stress_dialog()
            dlg.constant.setChecked(True)
            dlg._accept()
            assert isinstance(w.session.model.field, md.ConstantField)
        finally:
            _close(w)

    def test_refusals_are_said_in_the_dialog(self):
        w = _window()
        try:
            dlg = w.field_stress_dialog()
            dlg.sigma_1.box.setValue(1.0)
            dlg.sigma_3.box.setValue(2.0)
            dlg._accept()
            assert "sigma_1" in dlg.error.text() and dlg.result() == 0
            assert w.session.model.field == md.ConstantField()
            dlg = w.field_stress_dialog()
            dlg.gravity.setChecked(True)
            dlg._accept()                                   # the unit weight still empty
            assert "Stratum 1" in dlg.error.text() and "Unit weight" in dlg.error.text()
        finally:
            _close(w)

    def test_in_other_units(self):
        w = _window()
        try:
            w.do("field_set", kind="constant", sigma_1=100.0, sigma_3=50.0, sigma_z=50.0)
            w.do("project_settings", units="imperial_ksf")
            dlg = w.field_stress_dialog()
            assert dlg.sigma_1.box.suffix() == " ksf"
            assert abs(dlg.sigma_1.box.value() - round(100.0 / KSF, 3)) < 1e-12
            dlg.sigma_3.box.setValue(1.0)                   # 1 ksf
            dlg._accept()
            f = w.session.model.field
            assert abs(f.sigma_3 - KSF) < 1e-9
            assert f.sigma_1 == 100.0 and f.sigma_z == 50.0  # not touched: exactly as they were
            # a stratum written in feet and kips/ft³
            dlg = w.field_stress_dialog()
            dlg.gravity.setChecked(True)
            assert dlg.strata.horizontalHeaderItem(0).text() == "Bottom (ft)"
            for c, text in enumerate(("-10", "0.1", "1", "1")):
                _set_cell(dlg, 0, c, text)
            dlg._accept()
            s = w.session.model.field.strata[0]
            assert abs(s.bottom + 3.048) < 1e-12
            assert abs(s.unit_weight - 0.1 / 0.006365880354264175) < 1e-9     # 15.71 kN/m³
        finally:
            _close(w)


class TestTheBlock:
    def test_constant(self):
        m = md.Model(boundaries=(md.Boundary("e", md.EXTERNAL, ((0.0, 0.0), (10.0, 0.0),
                                                               (10.0, 10.0), (0.0, 10.0)), True),),
                     field=md.ConstantField(10.0, 5.0, 5.0, 0.0))
        marks = paths.field_marks(m)
        square, *arrows = marks.lines
        cx, cy = marks.centre
        assert cx > 10.0                                     # beside the model
        # sigma_1 horizontal: its shafts along x, twice as long as sigma_3's
        shafts = [a for a in arrows if len(a) == 2]
        horizontal = [a for a in shafts if abs(a[0][1] - a[1][1]) < 1e-12]
        vertical = [a for a in shafts if abs(a[0][0] - a[1][0]) < 1e-12]
        length = lambda a: math.dist(*a)  # noqa: E731
        assert len(horizontal) == len(vertical) == 2
        assert abs(length(horizontal[0]) - 2 * length(vertical[0])) < 1e-12
        # compression: the tip (second point) is nearer the centre than the tail
        for a in shafts:
            assert math.dist(a[1], (cx, cy)) < math.dist(a[0], (cx, cy))
        # turned by the angle
        turned = paths.field_marks(md.Model(boundaries=m.boundaries,
                                            field=md.ConstantField(10.0, 5.0, 5.0, 30.0)))
        e = turned.lines[0]
        d = (e[1][0] - e[0][0], e[1][1] - e[0][1])
        assert abs(math.degrees(math.atan2(d[1], d[0])) - 30.0) < 1e-9
        # tension: out
        pulled = paths.field_marks(md.Model(boundaries=m.boundaries,
                                            field=md.ConstantField(-1.0, -2.0, 0.0, 0.0)))
        for a in [a for a in pulled.lines[1:] if len(a) == 2]:
            assert math.dist(a[1], pulled.centre) > math.dist(a[0], pulled.centre)

    def test_gravity_and_in_the_window(self):
        w = _window()
        try:
            w.do("field_set", kind="gravity", surface=0.0,
                 strata=[{"bottom": -8.0, "unit_weight": 20.0, "k": 0.5, "kz": 0.5},
                         {"bottom": -20.0, "unit_weight": 21.0, "k": 0.6, "kz": 0.6}])
            marks = paths.field_marks(w.session.model)
            assert [line[0][1] for line in marks.lines] == [0.0, -8.0, -20.0]
            assert w.view.field_item is not None
            assert w.view.field_item.data(0) == ("field", "gravity")
            w.do("field_set", kind="constant", sigma_1=1.0, sigma_3=1.0, sigma_z=1.0)
            assert w.view.field_item.data(0) == ("field", "constant")
            # zoom all shows the block beside the model
            w.view.resize(600, 400)
            w.view.zoom_all()
            seen = w.view.mapToScene(w.view.viewport().rect()).boundingRect()
            assert seen.contains(w.view.field_item.sceneBoundingRect())
        finally:
            _close(w)
