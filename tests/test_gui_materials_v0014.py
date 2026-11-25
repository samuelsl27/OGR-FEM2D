# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.14 (spec 006, T26) — the materials and the assignment panel, with the
region's menu (RF-14; D7; spec 004, D9, D11, D16; P03).

Invariants protected:

* **every field of a material moves the model** (rule 7): name, colour,
  initial loading, unit weight, E, nu; each Apply is one ``material_set``
  with only what changed; Add and Delete are one step each; a material a
  region has cannot be deleted, and the dialog says so;
* **E and nu have no default** (D16): a new material shows them «to be
  given», the list marks it, and the window's model refuses to calculate
  naming it (``translate``);
* **the unit weight only with self weight** (D11): enabled with an initial
  loading that has the body force, and says why when not;
* **the panel assigns by clicks** in the stage shown: a material, Excavate
  and Fill each move the model (P03); «This stage only» keeps an
  excavation to its stage; a click in no region is said;
* **the region's menu** (D7): a right click with no tool open offers its
  material, Excavate and Fill, and the materials; none outside a region.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from ogr_fem2d.gui.canvas import controller as tc  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402
from ogr_fem2d.model import model as md  # noqa: E402
from ogr_fem2d.model import translate  # noqa: E402

APP = QApplication.instance() or QApplication([])
LEFT, RIGHT = Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton
_KEEP = []


def _window():
    w = MainWindow()
    _KEEP.append(w)
    w.act_new()
    w.do("boundary_add", type=md.EXTERNAL, closed=True,
         points_xy=[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]])
    w.do("boundary_add", type=md.EXCAVATION, closed=True,
         points_xy=[[4.0, 4.0], [6.0, 4.0], [6.0, 6.0], [4.0, 6.0]])
    return w


def _close(w):
    w.confirm_discard = lambda: True
    w.close()


class TestTheDialog:
    def test_add_each_field_and_delete(self):
        w = _window()
        try:
            dlg = w.materials_dialog()
            assert dlg.list.count() == 0 and not dlg.apply_button.isEnabled()
            dlg.add()
            m = w.session.model
            assert len(m.materials) == 1 and m.materials[0].E is None
            assert dlg.E.box.text() == "(to be given)" and "(E and ν to be given)" in \
                dlg.list.item(0).text()
            cases = [
                (lambda d: d.name.setText("Rock"), "name", "Rock"),
                (lambda d: d._set_colour("#123456"), "color", "#123456"),
                (lambda d: d.loading.setCurrentIndex(d.loading.findData(md.FIELD_AND_BODY)),
                 "initial_loading", md.FIELD_AND_BODY),
                (lambda d: d.E.box.setValue(2e6), "E", 2e6),
                (lambda d: d.nu.box.setValue(0.3), "nu", 0.3),
            ]
            for change, name, want in cases:
                steps = len(w.session.history()[0])
                change(dlg)
                assert list(dlg.changes()) == [name], dlg.changes()
                dlg.apply_shown()
                assert getattr(w.session.model.materials[0], name) == want, name
                assert len(w.session.history()[0]) == steps + 1
            assert "to be given" not in dlg.list.item(0).text()
            # the unit weight, now that the loading has the body force
            assert dlg.unit_weight.box.isEnabled()
            dlg.unit_weight.box.setValue(21.0)
            dlg.apply_shown()
            assert w.session.model.materials[0].unit_weight == 21.0
            dlg.loading.setCurrentIndex(dlg.loading.findData(md.FIELD_STRESS))
            assert not dlg.unit_weight.box.isEnabled() and dlg.unit_weight.box.toolTip()
            # a second one; choosing it applies what was changed in the first
            dlg.add()
            assert w.session.model.materials[0].initial_loading == md.FIELD_STRESS
            assert dlg.list.currentRow() == 1 and dlg.name.text() == "Material 2"
            # choosing another applies what was changed in the one shown
            dlg.name.setText("Second")
            dlg.list.setCurrentRow(0)
            assert w.session.model.materials[1].name == "Second"
            assert dlg.name.text() == "Rock"
            dlg.list.setCurrentRow(1)
            assert dlg.name.text() == "Second"               # the one chosen, shown
            dlg.name.setText("Material 2")
            dlg.apply_shown()
            # E cannot be taken away once given: said, not done
            dlg.list.setCurrentRow(0)
            dlg.E.box.setValue(dlg.E.box.minimum())
            assert not dlg.apply_shown() and "E cannot be taken away" in dlg.error.text()
            assert w.session.model.materials[0].E == 2e6
            dlg.E.box.setValue(2e6 / 1.0)
            # delete: refused while a region has it
            w.do("material_assign", material=w.session.model.materials[1].id, x=1.0, y=1.0)
            dlg.fill(w.session.model.materials[1].id)
            dlg.delete()
            assert "material" in dlg.error.text().lower() and len(w.session.model.materials) == 2
            dlg.fill(w.session.model.materials[0].id)
            dlg.delete()
            assert [x.name for x in w.session.model.materials] == ["Material 2"]
        finally:
            _close(w)

    def test_in_other_units_and_untouched_exact(self):
        w = _window()
        try:
            mid = w.do("material_set", name="a", E=123456.789, nu=0.25)["material"]
            w.do("project_settings", units="metric_mpa")
            dlg = w.materials_dialog(mid)
            assert dlg.E.box.suffix() == " MPa" and abs(dlg.E.box.value() - 123.457) < 1e-9
            dlg.nu.box.setValue(0.3)
            dlg.apply_shown()
            assert w.session.model.material(mid).E == 123456.789     # not touched: exact
            dlg.E.box.setValue(200.0)
            dlg.apply_shown()
            assert w.session.model.material(mid).E == 200000.0
        finally:
            _close(w)

    def test_calculating_names_the_material_without_e(self):
        w = _window()
        try:
            mid = w.do("material_set", name="soft")["material"]
            w.do("material_assign", material=mid, x=1.0, y=1.0)
            w.do("material_assign", material=mid, x=5.0, y=5.0)
            got = w.session.call("project_validate")
            assert got["materials_incomplete"] == [mid] and not got["ready"]
            try:
                translate._materials(w.session.model)       # what calculating calls
            except md.ModelError as err:
                assert mid in str(err) and "no E or no nu" in str(err), str(err)
            else:
                raise AssertionError("a material without E was taken")
        finally:
            _close(w)


class TestThePanel:
    def test_assign_excavate_fill_by_clicks(self):
        w = _window()
        try:
            a = w.do("material_set", name="a", E=1e6, nu=0.3)["material"]
            b = w.do("material_set", name="b", E=2e6, nu=0.3)["material"]
            w.act_assign()
            assert not w.assign_panel.isHidden() and w.assign_panel.list.count() == 2
            w.assign_panel.choose(("material", a))
            assert w.tools.mode == tc.ASSIGN
            w.tools.clicked(1.0, 1.0, LEFT)
            w.tools.clicked(5.0, 5.0, LEFT)
            m = w.session.model
            assert {x.material for x in m.assignments} == {a}
            w.assign_panel.choose(("material", b))
            w.tools.clicked(1.0, 1.0, LEFT)                       # the same region, b
            assert sorted(x.material for x in w.session.model.assignments) == [a, b]
            w.tools.clicked(20.0, 20.0, LEFT)                     # in no region: said
            assert w.statusBar().currentMessage()
            # three stages: excavate from stage 1 on, fill in stage 1 only, fill from 2 on
            w.do("stage_add")
            w.do("stage_add")
            hole = lambda: [x for x in w.session.model.assignments  # noqa: E731
                            if x.point == (5.0, 5.0)][0].excavated
            panel = w.assign_panel
            panel.choose(("excavate", True))
            w.stage_tabs.setCurrentIndex(0)
            w.tools.clicked(5.0, 5.0, LEFT)
            assert hole() == (True, True, True)
            panel.choose(("excavate", False))
            panel.this_stage_only.setChecked(True)
            w.tools.clicked(5.0, 5.0, LEFT)
            assert hole() == (False, True, True)
            panel.this_stage_only.setChecked(False)
            w.stage_tabs.setCurrentIndex(1)
            w.tools.clicked(5.0, 5.0, LEFT)
            assert hole() == (False, False, False)
            # excavated in stage 2 only: an element coming back in 3, refused and said
            panel.choose(("excavate", True))
            panel.this_stage_only.setChecked(True)
            w.tools.clicked(5.0, 5.0, LEFT)
            assert "coming back" in w.statusBar().currentMessage()
            assert hole() == (False, False, False)
            w.tools.key(Qt.Key.Key_Escape)
            assert w.tools.mode == tc.NONE
        finally:
            _close(w)

    def test_the_regions_menu(self):
        w = _window()
        try:
            a = w.do("material_set", name="a", E=1e6, nu=0.3)["material"]
            assert w.region_menu(20.0, 20.0) is None
            menu = w.region_menu(1.0, 1.0)
            texts = [x.text() for x in menu.actions()]
            assert texts[:3] == ["Assign Material", "Excavate", "Fill"]
            assert w.actions_by_key["define_materials"] in menu.actions()
            sub = menu.actions()[0].menu()
            [x for x in sub.actions() if x.text() == "a"][0].trigger()
            assert [x.material for x in w.session.model.assignments] == [a]
            menu = w.region_menu(1.0, 1.0)
            menu.actions()[1].trigger()                           # excavate
            assert w.session.model.assignments[0].excavated == (True,)
        finally:
            _close(w)
