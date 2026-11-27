# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.14 (spec 006, T23) — the project settings and the stages (RF-14,
RF-15; spec 004, D5; P17).

Invariants protected:

* **the dialog gives what was changed, and each choice moves the model**
  (rule 7): the kind of analysis, the unit system, the title, the author,
  the date and the notes, each alone; nothing changed is no operation and
  no step to undo; all of them at once are ONE step;
* **a refusal is said in the dialog**, which stays open: axisymmetry with a
  vertex left of the axis;
* **the kind of analysis is in the title and in the status bar** (P17),
  and in axisymmetry the axis is drawn at x = 0; a vertex drawn left of it
  is refused, saying why;
* **the units change what is shown, never the values** (004, D5): in feet
  the cursor's coordinates are in feet, a typed point in feet lands where
  it says (in metres in the model), the table's header says ft, and the
  grid's spacing is a round number of feet; the model's values are those
  of before;
* **the stages are the tabs** (RF-15): add after the one shown, rename,
  delete (each one step to undo; the only stage cannot be deleted, and the
  action says so); the tabs follow, the one shown is the one edited.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from ogr_core.numbers import nice_step  # noqa: E402
from ogr_core.units.unit_system import SYSTEMS  # noqa: E402
from ogr_ui import i18n as ui_i18n  # noqa: E402

from ogr_fem2d.gui import i18n as fem_i18n  # noqa: E402
from ogr_fem2d.gui import units  # noqa: E402
from ogr_fem2d.gui.canvas import controller as tc  # noqa: E402
from ogr_fem2d.gui.dialogs.coordinates import CoordinatesDialog  # noqa: E402
from ogr_fem2d.gui.dialogs.project_settings import ProjectSettingsDialog  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402
from ogr_fem2d.model import model as md  # noqa: E402

APP = QApplication.instance() or QApplication([])
LEFT, RIGHT = Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton
FT = 0.3048
_KEEP = []


def _window():
    w = MainWindow()
    w.resize(900, 700)
    w.show()
    _KEEP.append(w)
    w.act_new()
    return w


def _close(w):
    w.confirm_discard = lambda: True
    w.close()


def _square(w, side=10.0, x0=0.0):
    w.do("boundary_add", type=md.EXTERNAL, closed=True,
         points_xy=[[x0, 0.0], [x0 + side, 0.0], [x0 + side, side], [x0, side]])


class TestTheDialog:
    def test_each_choice_moves_the_model(self):
        w = _window()
        try:
            cases = [
                (lambda d: d.axisymmetric.setChecked(True), lambda m: m.analysis,
                 md.AXISYMMETRIC),
                (lambda d: d.units.setCurrentIndex(d.units.findData("imperial_ksf")),
                 lambda m: m.units, "imperial_ksf"),
                (lambda d: d.title_edit.setText("Túnel"), lambda m: m.summary.title, "Túnel"),
                (lambda d: d.author_edit.setText("S."), lambda m: m.summary.author, "S."),
                (lambda d: d.date_edit.setText("2026-11-25"), lambda m: m.summary.date,
                 "2026-11-25"),
                (lambda d: d.notes_edit.setPlainText("a\nb"), lambda m: m.summary.notes, "a\nb"),
            ]
            for change, read, want in cases:
                before = w.session.model
                steps = len(w.session.history()[0])
                dlg = w.project_settings_dialog()
                change(dlg)
                assert len(dlg.changes()) == 1, dlg.changes()
                dlg._accept()
                m = w.session.model
                assert read(m) == want and read(before) != want
                assert len(w.session.history()[0]) == steps + 1
                w.act_undo()
                assert read(w.session.model) == read(before)
            # nothing changed: no operation, no step
            dlg = w.project_settings_dialog()
            assert dlg.changes() == {}
            dlg._accept()
            assert w.session.history()[0] == []
            # all at once: one step
            dlg = w.project_settings_dialog()
            for change, _read, _want in cases:
                change(dlg)
            dlg._accept()
            assert len(w.session.history()[0]) == 1
            assert all(read(w.session.model) == want for _c, read, want in cases)
        finally:
            _close(w)

    def test_a_refusal_is_said_in_the_dialog(self):
        w = _window()
        try:
            _square(w, x0=-5.0)
            dlg = w.project_settings_dialog()
            dlg.axisymmetric.setChecked(True)
            dlg._accept()
            assert "x = r < 0" in dlg.error.text() or "axis" in dlg.error.text(), dlg.error.text()
            assert w.session.model.analysis == md.PLANE_STRAIN
            assert dlg.result() == 0                      # still open
        finally:
            _close(w)

    def test_every_unit_system_has_its_spanish(self):
        table = fem_i18n.spanish()
        assert [s.label for s in SYSTEMS.values() if s.label not in table] == []


class TestAnalysis:
    def test_in_the_title_the_status_bar_and_the_axis(self):
        w = _window()
        try:
            assert "Plane strain" in w.analysis_label.text() and w.view.axis_item is None
            w.do("project_settings", analysis=md.AXISYMMETRIC)
            assert "Axisymmetric" in w.windowTitle() and "Axisymmetric" in w.analysis_label.text()
            axis = w.view.axis_item
            assert axis is not None
            line = axis.line()
            assert line.x1() == line.x2() == 0.0 and line.y1() != line.y2()
            # a vertex left of the axis, refused when it is drawn, saying why
            w.tools.start(tc.DRAW, md.EXTERNAL)
            for p in ((-1.0, 0.0), (5.0, 0.0), (5.0, 5.0)):
                w.tools.clicked(*p, LEFT)
            w.tools.key(Qt.Key.Key_Return)
            assert w.session.model.boundaries == ()
            assert "x = r < 0" in w.statusBar().currentMessage()
        finally:
            _close(w)


class TestUnits:
    def test_feet_are_shown_and_read_and_the_values_kept(self):
        w = _window()
        try:
            _square(w, side=3.048)                       # 10 ft
            before = w.session.model
            w.do("project_settings", units="imperial_ksf")
            m = w.session.model
            assert m.boundaries == before.boundaries      # the values, untouched
            assert "ft" in w.analysis_label.text()
            # the cursor, in feet
            w.view.cursor_moved.emit(3.048, 1.524)
            assert w.statusBar().coord_label.text() == "X: +10.000   Y: +5.000"
            # a typed point, in feet
            w.tools.start(tc.DRAW, md.MATERIAL)
            for text in ("0, 4", "@10, 0"):
                w.statusBar().coord_input.setText(text)
                w.statusBar().coord_input.returnPressed.emit()
            w.tools.key(Qt.Key.Key_Return)
            got = w.session.model.boundary("mat1").vertices
            assert all(abs(a - b) < 1e-12 for p, q in zip(got, ((0.0, 4 * FT), (10 * FT, 4 * FT)))
                       for a, b in zip(p, q)), got
            # the table's points, in feet
            w.tools.start(tc.DRAW, md.STAGE)
            w.tools.points([(2.0, 1.0), (8.0, 1.0)])
            w.tools.finish()
            stg = w.session.model.boundary("stg1").vertices
            assert all(abs(a - b) < 1e-12 for p, q in zip(stg, ((2 * FT, FT), (8 * FT, FT)))
                       for a, b in zip(p, q)), stg
            # the table's header
            dlg = CoordinatesDialog(w, length=units.length_label(w.session.model))
            assert dlg.table.horizontalHeaderItem(0).text() == "X (ft)"
            # the grid: a round number of feet
            step_ft = w.view.grid_step() / FT
            assert abs(step_ft - nice_step(step_ft)) < 1e-9 * step_ft, step_ft
            w.do("project_settings", units="metric_kpa")
            assert w.session.model.boundary("mat1").vertices == got
        finally:
            _close(w)


class TestStages:
    def test_add_rename_delete(self):
        w = _window()
        try:
            acts = w.actions_by_key
            assert w.stage_tabs.count() == 1
            assert not acts["stage_delete"].isEnabled()
            assert acts["stage_delete"].statusTip()
            acts["stage_insert"].trigger()
            assert w.stage_tabs.count() == 2 and w.stage == 1     # the new one, shown
            assert w.stage_tabs.tabText(1) == "Stage 2"            # a stage without a name
            w.ask_text = lambda *_a: "Excavar"
            acts["stage_rename"].trigger()
            assert w.session.model.stages[1].name == "Excavar"
            assert w.stage_tabs.tabText(1) == "Excavar"
            w.stage_tabs.setCurrentIndex(0)
            acts["stage_insert"].trigger()                        # after the one shown
            assert [s.name for s in w.session.model.stages][2] == "Excavar"
            assert w.stage == 1
            assert acts["stage_delete"].isEnabled()
            acts["stage_delete"].trigger()
            assert [s.name for s in w.session.model.stages] == ["Stage 1", "Excavar"]
            assert w.stage_tabs.count() == 2
            w.ask_text = lambda *_a: None                          # cancelled: nothing
            steps = len(w.session.history()[0])
            acts["stage_rename"].trigger()
            assert len(w.session.history()[0]) == steps
            w.ask_text = lambda *_a: "Excavar"                     # the same name: nothing
            w.stage_tabs.setCurrentIndex(1)
            acts["stage_rename"].trigger()
            assert len(w.session.history()[0]) == steps
        finally:
            _close(w)

    def test_the_tabs_context_menu_has_the_same_actions(self):
        w = _window()
        try:
            menu = w.stage_menu()
            assert [a for a in menu.actions() if not a.isSeparator()] == [
                w.actions_by_key[k] for k in ("stage_insert", "stage_rename", "stage_delete")]
        finally:
            _close(w)

    def test_in_spanish(self):
        ui_i18n.set_language("es")
        try:
            w = _window()
            try:
                assert "Deformación plana" in w.analysis_label.text()
            finally:
                _close(w)
        finally:
            ui_i18n.set_language("en")
