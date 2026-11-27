# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The main window of OGR FEM2D (spec 006, T20; RF-13, RF-21; D4, D13).

* **the actions**, one registry (``_mk``, as OGR Slip2D's): each with its
  text through ``tr()``, its icon and shortcut of the suite, and an entry
  in ``inventory`` (the operation it calls, or why none);
* **the menus** in the order of the work (``menus.ORDER``); those of later
  phases with one disabled entry that says when they come (D4), through
  ``ogr_ui.disabled_reasons``, which shows the reason of a disabled entry
  on the status bar;
* **the model** is the session's (``session.Session``): the window calls
  operations and draws again when the session says something changed. The
  title says the model, its file, whether it has unsaved changes, and the
  kind of analysis (the reference program let one forget it, P17);
* what asks the user (a file to open, discarding changes) is a method of
  its own (``ask_open_path``, ``confirm_discard``), so that a test drives
  the window without a modal dialog.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QFileDialog, QInputDialog, QLabel, QMainWindow, QMenu,
                               QMessageBox, QStackedWidget, QTabBar, QVBoxLayout, QWidget)

from ogr_core.api import OgrApiError
from ogr_core.units import Quantity as Q
from ogr_ui import disabled_reasons
from ogr_ui.i18n import tr
from ogr_ui.resources.icons import icon
from ogr_ui.user_prefs import Preferences
from ogr_ui.widgets.status_bar import OgrStatusBar

import ogr_fem2d
from ..api.ops.project import mesh_state
from ..model import model as md
from . import i18n as fem_i18n
from . import menus, units
from .canvas import controller as tc
from .assign_panel import AssignPanel
from .canvas.view import ModelView
from .dialogs.mesh_setup import guaranteed_angle
from .session import Session

FILE_FILTER = "OGR FEM2D (*.ogrfem2d);;OGR Slip2D (*.ogr);;DXF (*.dxf)"

#: where the language and the theme are kept on this machine (ogr_ui; a
#: test run gives it a folder of its own, OGR_SETTINGS_DIR)
PREFERENCES = Preferences("OGR FEM2D", "ogr-fem2d")
#: the recent models, in the same settings (T28)
RECENT_KEY, RECENT_MAX = "recent_files", 8

#: the restraints, as the menus name them
RESTRAINT_NAMES = {md.X: "Restrained in X", md.Y: "Restrained in Y",
                   md.XY: "Restrained in X and Y", md.FREE: "Free (no restraint)"}


class MainWindow(QMainWindow):
    def __init__(self, session: Optional[Session] = None, parent=None):
        super().__init__(parent)
        fem_i18n.install()
        self.session = session if session is not None else Session()
        self._own_session = session is None
        self._actions: dict[str, QAction] = {}
        self._menus: dict[str, object] = {}
        self.setStatusBar(OgrStatusBar(self))
        self.analysis_label = QLabel()
        self.statusBar().insertPermanentWidget(0, self.analysis_label)
        self.mesh_label = QLabel()
        self.statusBar().insertPermanentWidget(1, QLabel(" │ "))
        self.statusBar().insertPermanentWidget(2, self.mesh_label)
        self._empty = QLabel()
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view = ModelView()
        self.view.cursor_moved.connect(self._show_cursor)
        self.stage_tabs = QTabBar()
        self.stage_tabs.setShape(QTabBar.Shape.RoundedSouth)
        self.stage_tabs.currentChanged.connect(self._stage_chosen)
        self.stage_tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.stage_tabs.customContextMenuRequested.connect(
            lambda pos: self.stage_menu().exec(self.stage_tabs.mapToGlobal(pos)))
        self.stage_tabs.tabBarDoubleClicked.connect(lambda _k: self.act_stage_rename())
        canvas = QWidget()
        lay = QVBoxLayout(canvas)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.view, 1)
        lay.addWidget(self.stage_tabs)
        self._stack = QStackedWidget()
        self._stack.addWidget(self._empty)
        self._stack.addWidget(canvas)
        self.setCentralWidget(self._stack)
        self.tools = tc.ToolController(self)
        #: the stretch just placed: (action, its key, its index, boundary, start, end)
        self._last_stretch = None
        self.assign_panel = AssignPanel(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.assign_panel)
        self.assign_panel.hide()
        self.view.clicked.connect(self.tools.clicked)
        self.view.cursor_moved.connect(self.tools.moved)
        self.view.key_pressed.connect(self.tools.key)
        # the X, Y field reads absolute, relative and polar points itself (ogr_ui 0.1.3),
        # from the reference the tools give it; the point comes absolute, in the units shown
        self.statusBar().manual_coords_submitted.connect(self.tools.typed_point)
        self._build_actions()
        self._build_menus()
        disabled_reasons.install(self)
        self.session.on_changed(lambda _op: self.refresh())
        self.refresh()

    # ------------------------------------------------------------ actions
    @property
    def actions_by_key(self) -> dict[str, QAction]:
        return dict(self._actions)

    def _mk(self, key: str, text: str, slot, icon_key: Optional[str] = None,
            shortcut: Optional[str] = None) -> QAction:
        act = QAction(tr(text), self)
        if icon_key:
            act.setIcon(icon(icon_key))
            act.setProperty("ogr_icon_key", icon_key)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        act.triggered.connect(slot)
        self._actions[key] = act
        return act

    def _build_actions(self) -> None:
        self._mk("new", "New", self.act_new, "new_project", "Ctrl+N")
        self._mk("open", "Open...", self.act_open, "open_project", "Ctrl+O")
        self._mk("save", "Save", self.act_save, "save", "Ctrl+S")
        self._mk("save_as", "Save As...", self.act_save_as, "save_as", "Ctrl+Shift+S")
        self._mk("import_slip2d", "Import OGR Slip2D Model...",
                 lambda: self.act_import("OGR Slip2D (*.ogr)"), None)
        self._mk("import_dxf", "Import DXF...", lambda: self.act_import("DXF (*.dxf)"),
                 "import_dxf")
        self._mk("clear_recent", "Clear the List", self.act_clear_recent, None)
        self._mk("prefs", "Preferences...", self.act_preferences, "preferences")
        self._mk("exit", "Exit", self.close, None, "Ctrl+Q")
        self._mk("undo", "Undo", self.act_undo, "undo", "Ctrl+Z")
        self._mk("redo", "Redo", self.act_redo, "redo", "Ctrl+Y")
        self._mk("window_main", "Model", self.act_front, None)
        self._mk("window_compute", "Calculation", self.act_compute_window, None)
        self._mk("compute", "Compute", self.act_compute, "compute", "F9")
        self._mk("interpret", "Interpret", self.act_interpret, "interpret", "F10")
        self._mk("report", "Report...", self.act_report, None, "F11")
        self._mk("zoom_all", "Zoom All", self.view.zoom_all, "zoom_all", "F2")
        self._mk("zoom_in", "Zoom In", lambda: self.view.zoom_by(1.5), "zoom_in", "F5")
        self._mk("zoom_out", "Zoom Out", lambda: self.view.zoom_by(1 / 1.5), "zoom_out", "F4")
        self._mk("show_grid", "Grid", self.act_show_grid, "grid", "F7").setCheckable(True)
        self._mk("show_mesh", "Mesh", self.act_show_mesh, None).setCheckable(True)
        self._actions["show_grid"].setChecked(self.view.show_grid)
        self._actions["show_mesh"].setChecked(self.view.show_mesh)
        self._mk("about", "About OGR FEM2D...", self.act_about, "about")
        self._mk("project_settings", "Project Settings...", self.act_project_settings,
                 "project_settings")
        self._mk("stage_insert", "Add Stage", self.act_stage_insert, None)
        self._mk("stage_rename", "Rename Stage...", self.act_stage_rename, None)
        self._mk("stage_delete", "Delete Stage", self.act_stage_delete, None)
        self._mk("field_stress", "Field Stress...", self.act_field_stress, None)
        self._mk("mesh_setup", "Mesh Setup...", self.act_mesh_setup, None, "Ctrl+U")
        self._mk("mesh_discretize", "Discretize", self.act_discretize, None)
        self._mk("mesh_generate", "Discretize and Mesh", self.act_mesh, None, "Ctrl+M")
        self._mk("mesh_reset", "Reset Mesh", self.act_mesh_reset, None)
        self._mk("segment_divisions", "Segment Divisions...", self.act_divisions, None)
        for key, text, kind in (("restrain_x", "Restrain X", md.X),
                                ("restrain_y", "Restrain Y", md.Y),
                                ("restrain_xy", "Restrain X, Y", md.XY),
                                ("release", "Free", md.FREE)):
            self._mk(key, text, lambda _c=False, k=kind: self.tools.start_place(
                {"op": "condition_set", "kind": k}), None)
        self._mk("impose", "Impose Displacement...", self.act_impose, None)
        self._mk("default_restraint", "External Default...", self.act_default_restraint,
                 None)
        self._mk("delete_condition", "Delete Condition", lambda: self.tools.start_place(
            {"op": "condition_delete"}), None)
        self._mk("add_distributed", "Add Distributed Load...",
                 lambda: self.act_load("distributed"), "distributed_load")
        self._mk("add_point", "Add Point Load...", lambda: self.act_load("point"),
                 "line_load")
        self._mk("delete_load", "Delete Load", lambda: self.tools.start_place(
            {"op": "load_delete"}), "delete_load")
        self._mk("stage_factors", "Factors by Stage...", self.act_stage_factors, None)
        self._mk("define_materials", "Define Materials...", self.act_materials,
                 "define_materials")
        self._mk("assign", "Assign Properties...", self.act_assign, "assign", "Ctrl+A")
        t = self.tools
        self._mk("add_excavation", "Add Excavation", lambda: t.start(tc.DRAW, md.EXCAVATION),
                 "add_polygon", "Ctrl+1")
        self._mk("add_external", "Add External", lambda: t.start(tc.DRAW, md.EXTERNAL),
                 "ext_boundary", "Ctrl+2")
        self._mk("add_material", "Add Material Boundary", lambda: t.start(tc.DRAW, md.MATERIAL),
                 "mat_boundary", "Ctrl+3")
        self._mk("add_stage", "Add Stage Boundary", lambda: t.start(tc.DRAW, md.STAGE),
                 "add_polyline", "Ctrl+4")
        self._mk("add_circle", "Add Circular Excavation",
                 lambda: t.start(tc.CIRCLE, md.EXCAVATION), "add_circle")
        self._mk("draw_arc", "Arc", t.start_arc, None, "A")
        self._mk("coords_table", "Enter Coordinates...", self.act_coords_table, None, "T")
        self._mk("finish_boundary", "Finish Boundary", t.finish, None)
        self._mk("move_vertex", "Move Vertex", lambda: t.start(tc.MOVE), "move_vertex")
        self._mk("insert_vertex", "Insert Vertex", lambda: t.start(tc.INSERT), "insert_vertex")
        self._mk("delete_vertex", "Delete Vertex", lambda: t.start(tc.DELETE_VERTEX),
                 "delete_vertex")
        self._mk("delete_boundary", "Delete Boundary", lambda: t.start(tc.DELETE_BOUNDARY),
                 "boundary_delete")
        self._mk("agent_bridge", "Agent Bridge (MCP)", self.act_agent_bridge,
                 None).setCheckable(True)
        for key, (text, why) in menus.SOON.items():
            act = self._mk(key, text, lambda: None)
            disabled_reasons.gate(act, False, tr(why))
        for menu, (key, text, why) in menus.FUTURE.items():
            act = self._mk(key, text, lambda: None)
            disabled_reasons.gate(act, False, tr(why))

    def _build_menus(self) -> None:
        bar = self.menuBar()
        for title in menus.ORDER:
            m = bar.addMenu(tr(title))
            self._menus[title] = m
            for entry in menus.MENUS.get(title, ()):
                if entry == "-":
                    m.addSeparator()
                elif entry == menus.RECENT:
                    self.recent_menu = m.addMenu(tr("Open Recent"))
                    self.recent_menu.aboutToShow.connect(self.fill_recent)
                    self.fill_recent()
                else:
                    m.addAction(self._actions[entry])

    # ------------------------------------------------------------ the state
    def title(self) -> str:
        m = self.session.model
        if m is None:
            return "OGR FEM2D"
        name = m.summary.title or (self.session.path.stem if self.session.path else tr("Untitled"))
        star = "*" if self.session.unsaved else ""
        kind = tr("Axisymmetric") if m.analysis == "axisymmetric" else tr("Plane strain")
        return f"{name}{star} — {kind} — OGR FEM2D"

    def refresh(self) -> None:
        """Title, the state of every action and the empty-state guide."""
        self.setWindowTitle(self.title())
        has = self.session.model is not None
        undo, redo = self.session.history()
        disabled_reasons.gate(self._actions["save"], has, tr("There is no model: File > New."))
        disabled_reasons.gate(self._actions["save_as"], has, tr("There is no model: File > New."))
        disabled_reasons.gate(self._actions["undo"], bool(undo), tr("Nothing to undo."))
        disabled_reasons.gate(self._actions["redo"], bool(redo), tr("Nothing to redo."))
        if undo:
            self._actions["undo"].setText(tr("Undo") + f": {fem_i18n.say(undo[-1])}")
        else:
            self._actions["undo"].setText(tr("Undo"))
        if redo:
            self._actions["redo"].setText(tr("Redo") + f": {fem_i18n.say(redo[-1])}")
        else:
            self._actions["redo"].setText(tr("Redo"))
        self._empty.setText(tr("No model: File > New, or File > Open."))
        self._stack.setCurrentIndex(1 if has else 0)
        for key in ("zoom_all", "zoom_in", "zoom_out"):
            disabled_reasons.gate(self._actions[key], has, tr("There is no model: File > New."))
        m = self.session.model
        self.analysis_label.setText(self.analysis_text())
        for key in ("project_settings", "report", "stage_insert", "stage_rename", "field_stress",
                    "mesh_setup", "mesh_discretize", "mesh_generate", "define_materials",
                    "assign", "restrain_x", "restrain_y", "restrain_xy", "release",
                    "impose", "default_restraint", "delete_condition", "add_distributed",
                    "add_point", "delete_load", "stage_factors", "segment_divisions"):
            disabled_reasons.gate(self._actions[key], has, tr("There is no model: File > New."))
        disabled_reasons.gate(self._actions["stage_delete"], has and len(m.stages) > 1,
                              tr("The only stage cannot be deleted: add another first.")
                              if has else tr("There is no model: File > New."))
        self.view.length_factor = units.length_factor(m)
        state = None if m is None else mesh_state(m)
        disabled_reasons.gate(self._actions["mesh_reset"], state not in (None, "none"),
                              tr("There is no mesh."))
        self.view.mesh_stale = state == "stale"
        disabled_reasons.gate(self._actions["compute"], state == "current", {
            None: tr("There is no model: File > New."),
            "none": tr("There is no mesh: Mesh > Discretize and Mesh."),
            "stale": tr("The mesh is of another geometry: Mesh > Discretize and Mesh."),
        }.get(state, ""))
        h5 = None if self.session.path is None else self.session.path.with_suffix(".h5")
        disabled_reasons.gate(self._actions["interpret"], h5 is not None and h5.exists(),
                              tr("There are no results: Analysis > Compute."))
        self.mesh_label.setText(self.mesh_text())
        self.mesh_label.setToolTip(self.mesh_notes())
        self.assign_panel.refresh(m)
        win = getattr(self, "_interpret_window", None)
        if win is not None and win.isVisible():
            win.note_state()
        if "draw_arc" in self._actions:
            self.refresh_tools()
        self._fill_stage_tabs(m)
        self.view.set_model(m, self.stage_tabs.currentIndex() if m is not None else 0)
        if m is not None and not m.boundaries:
            self.statusBar().showMessage(
                tr("Draw the external boundary: Boundaries > Add External."), 10000)

    def analysis_text(self) -> str:
        """The kind of analysis and the units shown, for the status bar
        (P17: the reference program let one forget the kind)."""
        m = self.session.model
        if m is None:
            return ""
        kind = tr("Axisymmetric") if m.analysis == md.AXISYMMETRIC else tr("Plane strain")
        s = units.system(m)
        return " · ".join((kind, s.label_for(Q.LENGTH), s.label_for(Q.PRESSURE)))

    def mesh_text(self) -> str:
        """The mesh's state, for the status bar: none, of another
        geometry (calculating will refuse it, RF-12), or its size."""
        m = self.session.model
        if m is None:
            return ""
        state = mesh_state(m)
        if state == "none":
            return tr("No mesh: Mesh > Discretize and Mesh")
        if state == "stale":
            return tr("Mesh of another geometry: Mesh > Discretize and Mesh")
        npe = m.mesh.notes.get("nodes_per_element") or len(m.mesh.elements[0])
        return tr("Mesh: %d nodes, %d elements T%d") % (len(m.mesh.nodes),
                                                       len(m.mesh.elements), npe)

    def mesh_notes(self) -> str:
        """What decided the mesh, and its warnings (rule 12; RF-20)."""
        m = self.session.model
        if m is None or m.mesh is None:
            return ""
        notes = m.mesh.notes
        lines = []
        b = notes.get("quality_bound")
        if b is not None:
            lines.append(tr("Quality bound B = %.4g (smallest angle guaranteed %.1f°)")
                         % (b, guaranteed_angle(b)))
        worst = notes.get("quality", {}).get("min_angle", {}).get("worst")
        if worst is not None:
            lines.append(tr("Smallest angle of the mesh: %.2f°") % worst)
        for w in m.mesh.warnings:
            lines.append(tr("Warning of the mesher: %s") % w)
        return "\n".join(lines)

    def _show_cursor(self, x: float, y: float) -> None:
        """The cursor's coordinates in the units shown."""
        self.statusBar().update_coords(*units.to_user(self.session.model, (x, y)))

    def _fill_stage_tabs(self, m) -> None:
        """One tab per stage, the one shown kept (RF-15)."""
        names = [] if m is None else [s.name or tr("Stage %s") % s.id for s in m.stages]
        current = self.stage_tabs.currentIndex()
        self.stage_tabs.blockSignals(True)
        while self.stage_tabs.count():
            self.stage_tabs.removeTab(0)
        for name in names:
            self.stage_tabs.addTab(name)
        if names:
            self.stage_tabs.setCurrentIndex(min(max(current, 0), len(names) - 1))
        self.stage_tabs.blockSignals(False)

    def _stage_chosen(self, k: int) -> None:
        if k >= 0:
            self.view.set_stage(k)

    @property
    def stage(self) -> int:
        """The stage shown, which is the one edited (RF-15)."""
        return max(self.stage_tabs.currentIndex(), 0)

    def act_show_grid(self) -> None:
        self.view.show_grid = self._actions["show_grid"].isChecked()
        self.view.viewport().update()

    def act_show_mesh(self) -> None:
        self.view.show_mesh = self._actions["show_mesh"].isChecked()
        self.view.set_model(self.session.model)

    def show_error(self, err: Exception) -> None:
        """An operation's refusal, on the status bar (it does not insist,
        guide §7)."""
        text = fem_i18n.say(getattr(err, "message", str(err)))
        hint = getattr(err, "hint", None)
        self.statusBar().showMessage(text + (f" {fem_i18n.say(hint)}" if hint else ""), 10000)

    # ------------------------------------------------------------ asking
    def ask_open_path(self) -> Optional[str]:
        path, _f = QFileDialog.getOpenFileName(self, tr("Open"), "", FILE_FILTER)
        return path or None

    def ask_save_path(self) -> Optional[str]:
        path, _f = QFileDialog.getSaveFileName(self, tr("Save As"), "", "OGR FEM2D (*.ogrfem2d)")
        return path or None

    def confirm_discard(self) -> bool:
        box = QMessageBox(QMessageBox.Icon.Warning, tr("Unsaved changes"),
                          tr("The model has changes that are not saved."), parent=self)
        discard = box.addButton(tr("Discard changes"), QMessageBox.ButtonRole.DestructiveRole)
        box.addButton(tr("Cancel"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        return box.clickedButton() is discard

    # ------------------------------------------------------------ doing
    def do(self, op: str, /, **kwargs):
        """An operation on the model; its refusal on the status bar."""
        try:
            return self.session.call(op, **kwargs)
        except OgrApiError as err:
            self.show_error(err)
            return None

    _do = do

    # ------------------------------------------------------------ tools
    def act_coords_table(self) -> None:
        from .dialogs.coordinates import CoordinatesDialog
        dlg = CoordinatesDialog(self, length=units.length_label(self.session.model))
        if dlg.exec():
            self.tools.points(dlg.result_points)

    def refresh_tools(self) -> None:
        """What the tools can do now: drawing needs a model, a step of
        drawing needs a boundary being drawn."""
        has = self.session.model is not None
        drawing = self.tools.mode == tc.DRAW
        for key in ("add_excavation", "add_external", "add_material", "add_stage", "add_circle",
                    "move_vertex", "insert_vertex", "delete_vertex", "delete_boundary"):
            disabled_reasons.gate(self._actions[key], has, tr("There is no model: File > New."))
        for key in ("draw_arc", "coords_table", "finish_boundary"):
            disabled_reasons.gate(self._actions[key], drawing,
                                  tr("Draw a boundary first: Boundaries > Add."))

    def _leave_current(self) -> bool:
        """The current model is closed, its changes discarded if the user
        says so; False if the user keeps it."""
        if self.session.model is None:
            return True
        if self.session.unsaved and not self.confirm_discard():
            return False
        self._do("project_close", discard_changes=True)
        return True

    def act_new(self) -> None:
        if self._leave_current():
            self._do("project_new")

    def open_path(self, path: str) -> Optional[dict]:
        if not self._leave_current():
            return None
        got = self._do("project_open", path=str(path))
        if got and got.get("report"):
            from .dialogs.import_report import ImportReportDialog
            self.report_window = ImportReportDialog(Path(path).name, got["report"],
                                                    got["problems"], self)
            self.report_window.show()               # beside the model, not in the way
            self.statusBar().showMessage(
                tr("Converted: see the report of what came and what did not."), 10000)
        elif got:
            self.remember_recent(path)
        return got

    # ------------------------------------------------------------ recent files
    def recent_files(self) -> list[str]:
        """The models opened or saved last, newest first (kept on this
        machine, as the language)."""
        value = PREFERENCES.settings().value(RECENT_KEY, [])
        if isinstance(value, str):
            value = [value]
        return [str(v) for v in (value or [])]

    @staticmethod
    def _store_recent(files: list) -> None:
        s = PREFERENCES.settings()
        s.setValue(RECENT_KEY, files)
        s.sync()

    def remember_recent(self, path) -> None:
        p = str(Path(path).resolve())
        files = [p] + [f for f in self.recent_files() if f != p]
        self._store_recent(files[:RECENT_MAX])
        self.fill_recent()

    def fill_recent(self) -> None:
        menu = self.recent_menu
        menu.clear()
        files = self.recent_files()
        for k, f in enumerate(files):
            act = menu.addAction(f"&{k + 1} {Path(f).name}")
            act.setToolTip(f)
            act.setStatusTip(f)
            act.triggered.connect(lambda _c=False, f=f: self.open_recent(f))
        if not files:
            empty = menu.addAction(tr("(no model opened yet)"))
            empty.setEnabled(False)
        menu.addSeparator()
        menu.addAction(self._actions["clear_recent"])
        disabled_reasons.gate(self._actions["clear_recent"], bool(files),
                              tr("The list is empty."))

    def open_recent(self, path: str) -> None:
        if not Path(path).exists():                 # said, and taken off the list
            self._store_recent([f for f in self.recent_files() if f != path])
            self.fill_recent()
            self.statusBar().showMessage(tr("%s is no longer there: taken off the list.")
                                         % path, 10000)
            return
        self.open_path(path)

    def act_clear_recent(self) -> None:
        self._store_recent([])
        self.fill_recent()

    def act_import(self, filters: str) -> None:
        path = self.ask_import_path(filters)
        if path:
            self.open_path(path)

    def ask_import_path(self, filters: str) -> Optional[str]:
        path, _f = QFileDialog.getOpenFileName(self, tr("Import"), "", filters)
        return path or None

    def act_open(self) -> None:
        path = self.ask_open_path()
        if path:
            self.open_path(path)

    def act_save(self) -> None:
        if self.session.model is None:
            return
        if self.session.path is None:
            self.act_save_as()
        else:
            self._do("project_save")

    def act_save_as(self) -> None:
        path = self.ask_save_path()
        if path and self._do("project_save", path=path, overwrite=True) is not None:
            self.remember_recent(path)

    def act_undo(self) -> None:
        self._do("project_history", action="undo")

    def act_redo(self) -> None:
        self._do("project_history", action="redo")

    # ------------------------------------------------------------ settings, stages
    def project_settings_dialog(self):
        """The dialog, connected: what it gives is one ``project_settings``."""
        from .dialogs.project_settings import ProjectSettingsDialog
        return ProjectSettingsDialog(self.session.model, self._applying("project_settings"),
                                     self)

    def act_project_settings(self) -> None:
        if self.session.model is not None:
            self.project_settings_dialog().exec()

    def field_stress_dialog(self):
        """The dialog, connected: what it gives is one ``field_set``."""
        from .dialogs.field_stress import FieldStressDialog
        return FieldStressDialog(self.session.model, self._applying("field_set"), self)

    def act_field_stress(self) -> None:
        if self.session.model is not None:
            self.field_stress_dialog().exec()

    def _applying(self, op: str):
        """For a dialog: do ``op`` with what it gives; the refusal's text,
        or None."""
        def apply(changes):
            try:
                self.session.call(op, **changes)
            except OgrApiError as err:
                return fem_i18n.say(getattr(err, "message", str(err)))
            return None
        return apply

    # ------------------------------------------------------------ the mesh
    def mesh_setup_dialog(self):
        """The dialog, connected: settings by ``mesh_settings``, then the
        two steps."""
        from .dialogs.mesh_setup import MeshSetupDialog
        return MeshSetupDialog(self.session.model, self._applying("mesh_settings"),
                               self.discretize, self.mesh, self)

    def act_mesh_setup(self) -> None:
        if self.session.model is not None:
            self.mesh_setup_dialog().exec()

    def discretize(self) -> Optional[str]:
        """The first step: the nodes of the boundaries, drawn and counted;
        the refusal's text, or None."""
        try:
            got = self.session.call("mesh_discretize")
        except OgrApiError as err:
            return fem_i18n.say(getattr(err, "message", str(err)))
        points = {tuple(p) for s in got["segments"] for p in s["nodes"]}
        self.view.show_discretization(sorted(points))
        self.statusBar().showMessage(
            tr("Discretized: %d nodes on %d segments. Then: Mesh > Discretize and Mesh.")
            % (len(points), len(got["segments"])), 10000)
        return None

    def mesh(self) -> Optional[str]:
        """The mesh, made in a child process while the window goes on
        drawing (decided on 2026-11-25: 2 to 4 s with the meshes of the
        cases), with a dialog that can cancel it; then put in the model, one
        step to undo, and what decided it on the status bar. The refusal's
        text, or None."""
        from ogr_ui.dialogs.progress_dialog import TaskProgressDialog
        try:
            job = self.session.call("mesh_generate", background=True)["job_id"]
        except OgrApiError as err:
            return self._said_refusal(err)
        dlg = TaskProgressDialog(self, tr("Meshing"), on_cancel=lambda: self.session.call(
            "job_cancel", job_id=job, grace_s=0.0))
        dlg.lbl_status.setText(tr("Meshing..."))
        self.mesh_dialog = dlg
        dlg.show()
        state = self.wait_job(job)
        dlg.finish()
        if state != "done":
            text = (tr("Meshing cancelled: the model is as it was.") if state == "cancelled"
                    else tr("The mesher failed: %s") % self._job_error(job))
            self.statusBar().showMessage(text, 10000)
            return text
        try:
            got = self.session.call("mesh_collect", job_id=job)
        except OgrApiError as err:
            return self._said_refusal(err)
        said = tr("Meshed: %d nodes, %d elements; smallest angle %.1f° (B = %.4g).") % (
            got["nodes"], got["elements"], got["min_angle"] or 0.0, got["quality_bound"])
        if got["warnings"]:
            said += " " + tr("Warnings of the mesher: %d (see the mesh on the status bar).") \
                % len(got["warnings"])
        self.statusBar().showMessage(said, 15000)
        return None

    def wait_job(self, job: str, every_ms: int = 100) -> str:
        """Wait for a job while the window goes on (an event loop of its
        own, asking every ``every_ms``); its final state."""
        from PySide6.QtCore import QEventLoop, QTimer
        loop, timer, state = QEventLoop(), QTimer(), {}

        def ask():
            st = self.session.call("job_get", job_id=job)
            if st["state"] in ("done", "failed", "cancelled", "crashed"):
                state["final"] = st["state"]
                loop.quit()
        timer.timeout.connect(ask)
        timer.start(every_ms)
        ask()
        if "final" not in state:
            loop.exec()
        timer.stop()
        return state["final"]

    def _job_error(self, job: str) -> str:
        st = self.session.call("job_get", job_id=job)
        return str(st.get("error") or st.get("log_tail") or st.get("state"))

    def _said_refusal(self, err) -> str:
        text = fem_i18n.say(getattr(err, "message", str(err)))
        self.statusBar().showMessage(text, 10000)
        return text

    def act_discretize(self) -> None:
        refused = self.discretize()
        if refused:
            self.statusBar().showMessage(refused, 10000)

    def act_mesh(self) -> None:
        """Both steps at once."""
        if self.session.model is not None and self.discretize() is None:
            self.mesh()
        elif self.session.model is not None:
            self.act_discretize()

    def act_mesh_reset(self) -> None:
        self._do("mesh_reset")

    # ------------------------------------------------------------ calculating
    @property
    def compute_window(self):
        """The calculation's window, made the first time it is asked for."""
        if getattr(self, "_compute_window", None) is None:
            from .compute_window import ComputeWindow
            self._compute_window = ComputeWindow(self.session, self)
            self._compute_window.job_ended.connect(self.calculated)
            self._compute_window.results_wanted.connect(self.act_interpret)
        return self._compute_window

    def confirm_save_to_compute(self) -> bool:
        box = QMessageBox(QMessageBox.Icon.Question, tr("Compute"),
                          tr("The results are written beside the model's file, with its "
                             "fingerprint: the model is saved first."), parent=self)
        save = box.addButton(tr("Save and Compute"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(tr("Cancel"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        return box.clickedButton() is save

    def compute(self) -> Optional[str]:
        """Calculate the model in a child process (RF-9), followed by the
        calculation's window; the model is saved first, as the results
        are written beside its file (it asks). The refusal's text, or None."""
        if self.session.model is None:
            return None
        if self.session.path is None or self.session.unsaved:
            if not self.confirm_save_to_compute():
                return None
            self.act_save()
            if self.session.path is None or self.session.unsaved:
                return None                             # Save As was cancelled
        m = self.session.model
        try:
            job = self.session.call("analysis_run")["job_id"]
        except OgrApiError as err:
            return self._said_compute_refusal(err)
        win = self.compute_window
        win.follow(job, m)
        win.show()
        win.raise_()
        self.statusBar().showMessage(tr("Calculating: Window > Calculation shows how it goes."),
                                     10000)
        return None

    def _said_compute_refusal(self, err) -> str:
        """A refusal to calculate, naming the object of the model that
        causes it (RF-11, RF-12)."""
        from .problems import problem_text
        found = (getattr(err, "details", None) or {}).get("problems") or []
        if found:
            text = tr("Not calculated: %s") % problem_text(found[0])
            if len(found) > 1:
                text += " " + tr("(and %d more problems)") % (len(found) - 1)
        else:
            text = tr("Not calculated: %s") % fem_i18n.say(getattr(err, "message", str(err)))
            hint = getattr(err, "hint", None)
            text += f" {fem_i18n.say(hint)}" if hint else ""
        self.statusBar().showMessage(text, 15000)
        return text

    def act_compute(self) -> None:
        self.compute()

    @property
    def interpret_window(self):
        """The interpretation's window, made the first time it is asked for."""
        if getattr(self, "_interpret_window", None) is None:
            from .interpret.window import InterpretWindow
            self._interpret_window = InterpretWindow(self)
        return self._interpret_window

    def interpret(self) -> Optional[str]:
        """The results of the model, read again and shown; the refusal's
        text, or None."""
        win = self.interpret_window
        said = win.open()
        win.show()
        win.raise_()
        return said

    def act_interpret(self) -> None:
        self.interpret()

    @property
    def info_window(self):
        """The report's window, made the first time it is asked for."""
        if getattr(self, "_info_window", None) is None:
            from .info_window import InfoWindow
            self._info_window = InfoWindow(self.session, self)
        return self._info_window

    def act_report(self) -> Optional[str]:
        win = self.info_window
        said = win.read()
        win.show()
        win.raise_()
        return said

    def act_compute_window(self) -> None:
        win = self.compute_window
        win.show()
        win.raise_()

    def calculated(self, job: str, state: str) -> None:
        """A calculation ended: its summary on the status bar (guide §5)."""
        self.statusBar().showMessage(self.compute_window.summary_text(job), 20000)
        self.refresh()
        win = getattr(self, "_interpret_window", None)
        if win is not None and win.isVisible():
            win.open()                                   # the results just written

    # ------------------------------------------------------------ the agent bridge
    @property
    def agent_bridge(self):
        """The window's agent bridge (D8), made the first time it is asked for."""
        if getattr(self, "_agent_bridge", None) is None:
            from .agent_bridge import AgentBridge
            self._agent_bridge = AgentBridge(self)
        return self._agent_bridge

    def act_agent_bridge(self, on: bool) -> Optional[str]:
        """Serve this window to the MCP server, or stop; what it says."""
        act = self._actions["agent_bridge"]
        if on:
            try:
                port = self.agent_bridge.start()
            except OSError as err:
                act.setChecked(False)
                text = tr("The agent bridge could not start: %s") % err
                self.statusBar().showMessage(text, 15000)
                return text
            text = tr("Agent bridge on (127.0.0.1:%d): the MCP server works on this window, and "
                      "its edits are undone here.") % port
        else:
            self.agent_bridge.stop()
            text = tr("Agent bridge off: the MCP server works on its own models.")
        act.setChecked(self.agent_bridge.running)
        self.statusBar().showMessage(text, 15000)
        return text

    def confirm_stop_calculation(self) -> bool:
        box = QMessageBox(QMessageBox.Icon.Warning, tr("A calculation is running"),
                          tr("Closing stops the calculation that is running: its results "
                             "will not be complete."), parent=self)
        stop = box.addButton(tr("Stop it and Close"), QMessageBox.ButtonRole.DestructiveRole)
        box.addButton(tr("Cancel"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        return box.clickedButton() is stop

    def running_jobs(self) -> list[str]:
        return [j["job_id"] for j in self.session.call("job_list")["jobs"]
                if j["state"] in ("queued", "running")]

    # ------------------------------------------------------------ materials
    def said(self, op: str, /, **kwargs):
        """For a dialog: (the operation's result, None) or (None, the
        refusal's text)."""
        try:
            return self.session.call(op, **kwargs), None
        except OgrApiError as err:
            return None, fem_i18n.say(getattr(err, "message", str(err)))

    def materials_dialog(self, material: Optional[str] = None):
        from .dialogs.materials import MaterialsDialog
        return MaterialsDialog(lambda: self.session.model, self.said, self, material)

    def act_materials(self, material: Optional[str] = None) -> None:
        if self.session.model is not None:
            self.materials_dialog(material or None).exec()

    def act_assign(self) -> None:
        """The assignment panel, beside the canvas."""
        if self.session.model is not None:
            self.assign_panel.show()
            self.assign_panel.raise_()
            self.resizeDocks([self.assign_panel], [240], Qt.Orientation.Horizontal)

    def assign_at(self, x: float, y: float, what=None) -> None:
        """Assign ``what`` (the panel's choice by default) to the region
        at (x, y), in the stage shown."""
        m = self.session.model
        what = what or self.assign_panel.what
        if m is None or what is None:
            return
        stage = m.stages[self.stage].id
        only = self.assign_panel.this_stage_only.isChecked()
        if what[0] == "material":
            done = self._do("material_assign", material=what[1], x=x, y=y, stage=stage,
                            this_stage_only=only)
        else:
            done = self._do("region_excavate", x=x, y=y, stage=stage, excavated=what[1],
                            this_stage_only=only)
        if done is not None:
            self.statusBar().showMessage(tr("Assigned in the stage shown."), 5000)

    def region_menu(self, x: float, y: float) -> Optional[QMenu]:
        """The menu of the region at (x, y) (D7): its material, excavate,
        fill, the materials; None if the click is in no region."""
        from ..model import regions
        m = self.session.model
        if m is None:
            return None
        try:
            regions.region_of(m, (x, y))
        except md.ModelError:
            return None
        menu = QMenu(self)
        sub = menu.addMenu(tr("Assign Material"))
        from .dialogs.materials import swatch
        for mat in m.materials:
            act = sub.addAction(swatch(mat.color), mat.name or mat.id)
            act.triggered.connect(lambda _c=False, i=mat.id: self.assign_at(
                x, y, ("material", i)))
        sub.setEnabled(bool(m.materials))
        menu.addAction(tr("Excavate")).triggered.connect(
            lambda: self.assign_at(x, y, ("excavate", True)))
        menu.addAction(tr("Fill")).triggered.connect(
            lambda: self.assign_at(x, y, ("excavate", False)))
        menu.addSeparator()
        menu.addAction(self._actions["define_materials"])
        return menu

    def region_context(self, x: float, y: float) -> None:
        from PySide6.QtGui import QCursor
        menu = self.region_menu(x, y)
        if menu is not None:
            menu.exec(QCursor.pos())

    # ------------------------------------------------------------ conditions, loads
    def impose_dialog(self):
        from .dialogs.loads import ImposeDialog
        return ImposeDialog(self.session.model, self)

    def act_impose(self) -> None:
        dlg = self.impose_dialog()
        if self.session.model is not None and dlg.exec():
            self.tools.start_place({"op": "condition_set", **dlg.params()})

    def load_dialog(self, kind: str):
        from .dialogs.loads import LoadDialog
        return LoadDialog(self.session.model, kind, self)

    def act_load(self, kind: str) -> None:
        dlg = self.load_dialog(kind)
        if self.session.model is not None and dlg.exec():
            self.tools.start_place({"op": "load_set", **dlg.params()})

    def stage_factors_dialog(self):
        from .dialogs.loads import StageFactorsDialog
        return StageFactorsDialog(self.session.model, self.said, self)

    def act_stage_factors(self) -> None:
        if self.session.model is not None:
            self.stage_factors_dialog().exec()

    def ask_choice(self, title: str, label: str, options: list, current: int):
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getItem(self, title, label, options, current, False)
        return options.index(text) if ok else None

    def act_default_restraint(self) -> None:
        """What the external has where no condition says otherwise (the
        reference program fixed it without showing it: it is drawn)."""
        m = self.session.model
        if m is None:
            return
        kinds = list(md.RESTRAINTS)
        names = [tr(RESTRAINT_NAMES[k]) for k in kinds]
        k = self.ask_choice(tr("External Default"), tr("Where no condition says otherwise, "
                            "the external is:"), names, kinds.index(m.default_restraint))
        if k is not None:
            self._do("condition_default", kind=kinds[k])

    def ask_int(self, title: str, label: str, value: int, lo: int) -> Optional[int]:
        from PySide6.QtWidgets import QInputDialog
        n, ok = QInputDialog.getInt(self, title, label, value, lo, 100000)
        return n if ok else None

    def act_divisions(self) -> None:
        """The divisions of the segments clicked next (0: the mesher
        decides, spec 003)."""
        if self.session.model is None:
            return
        n = self.ask_int(tr("Segment Divisions"),
                         tr("Divisions of each segment clicked (0: the mesher decides):"), 8, 0)
        if n is not None:
            self.tools.start_place({"op": "set_divisions", "divisions": n or None})

    def place(self, action: dict, vertex=None, boundary=None, start=None, end=None) -> None:
        """Do ``action`` on a vertex or on a segment (start to end). A
        segment that continues the stretch just placed by the same action
        widens it, one condition or load (said), as the stretch of the
        model is from vertex to vertex (004, D7)."""
        m = self.session.model
        op = action["op"]
        if op == "set_divisions":
            if vertex is not None:
                self.statusBar().showMessage(tr("Click a segment, not a vertex."), 5000)
                return
            b = m.boundary(boundary)
            self._do("boundary_edit", boundary=boundary, op="set_divisions",
                     segment=b.vertices.index(tuple(start)), divisions=action["divisions"])
            return
        last = self._last_stretch
        if (vertex is None and last is not None and last[0] is action
                and last[3] == boundary and op in ("condition_set", "load_set")):
            _a, key, k, _b, s0, e0 = last
            span = ((s0, end) if tuple(start) == tuple(e0) else
                    (start, e0) if tuple(end) == tuple(s0) else None)
            if span is not None:
                kwargs = {x: v for x, v in action.items() if x != "op"}
                if self._do(op, **kwargs, **{key: k}, boundary=boundary, start=list(span[0]),
                            end=list(span[1])) is not None:
                    self._last_stretch = (action, key, k, boundary, span[0], span[1])
                    self.statusBar().showMessage(tr("The stretch grows to the segment "
                                                    "clicked."), 5000)
                return
        where = ({"vertex": list(vertex)} if vertex is not None else
                 {"boundary": boundary, "start": list(start), "end": list(end)})
        if op in ("condition_delete", "load_delete"):
            k = self._found(m, op, vertex, boundary, start, end)
            if k is None:
                self.statusBar().showMessage(tr("Nothing of that kind there."), 5000)
            else:
                self._do(op, **({"condition": k} if op == "condition_delete" else {"load": k}))
            return
        kwargs = {k: v for k, v in action.items() if k != "op"}
        if op == "load_set" and (kwargs["kind"] == "point") != (vertex is not None):
            self.statusBar().showMessage(
                tr("A point load goes on a vertex.") if kwargs["kind"] == "point" else
                tr("A distributed load goes on a segment."), 8000)
            return
        got = self._do(op, **kwargs, **where)
        key = "condition" if op == "condition_set" else "load"
        self._last_stretch = (None if got is None or vertex is not None else
                              (action, key, got[key], boundary, tuple(start), tuple(end)))

    @staticmethod
    def _found(m, op, vertex, boundary, start, end):
        """The last condition (or load) at that vertex or on that segment."""
        items = m.conditions if op == "condition_delete" else m.loads
        for k in range(len(items) - 1, -1, -1):
            it = items[k]
            v = getattr(it, "vertex", None)
            span = getattr(it, "span", None)
            if vertex is not None and v is not None and tuple(v) == tuple(vertex):
                return k
            if boundary is not None and span is not None and span.boundary == boundary:
                b = m.boundary(boundary)
                seg = b.vertices.index(tuple(start)) if tuple(start) in b.vertices else None
                if seg is not None and seg in (md.span_indices(b, span) or []):
                    return k
        return None

    def stage_menu(self) -> QMenu:
        """The tabs' context menu: the actions of the Analysis menu."""
        menu = QMenu(self)
        for key in ("stage_insert", "stage_rename", "stage_delete"):
            menu.addAction(self._actions[key])
        return menu

    def ask_text(self, title: str, label: str, current: str) -> Optional[str]:
        text, ok = QInputDialog.getText(self, title, label, text=current)
        return text if ok else None

    def act_stage_insert(self) -> None:
        """A stage after the one shown, which then shows (RF-15)."""
        k = self.stage + 1
        if self._do("stage_add", index=k) is not None:
            self.stage_tabs.setCurrentIndex(k)

    def act_stage_rename(self) -> None:
        m = self.session.model
        if m is None:
            return
        s = m.stages[self.stage]
        name = self.ask_text(tr("Rename Stage"), tr("Name of the stage:"), s.name)
        if name is not None:                  # the same name is no step (the workspace)
            self._do("stage_rename", stage=s.id, name=name)

    def act_stage_delete(self) -> None:
        """The stage shown; one step to undo, so it does not ask (guide §9)."""
        m = self.session.model
        if m is not None:
            self._do("stage_delete", stage=m.stages[self.stage].id)

    def act_front(self) -> None:
        self.raise_()
        self.activateWindow()

    def preferences_dialog(self):
        """The dialog of the language and the theme, connected: a new
        language is saved and applies on the next start (D12, as Slip2D);
        a theme applies now and is saved."""
        from ogr_ui.dialogs.preferences_dialog import PreferencesDialog
        from ogr_ui.themes import current_theme
        dlg = PreferencesDialog(self, current_theme())
        dlg.language_changed.connect(self.change_language)
        dlg.theme_changed.connect(self.change_theme)
        return dlg

    def act_preferences(self) -> None:
        self.preferences_dialog().exec()

    def change_language(self, code: str) -> None:
        PREFERENCES.save_language(code)
        self.statusBar().showMessage(tr("The language changes the next time OGR FEM2D starts."),
                                     10000)

    def change_theme(self, name: str) -> None:
        from PySide6.QtWidgets import QApplication
        from ogr_ui.themes import apply_theme
        apply_theme(QApplication.instance(), name)
        PREFERENCES.save_theme(name)

    def act_about(self) -> None:
        QMessageBox.about(self, tr("About OGR FEM2D"), about_text())

    # ------------------------------------------------------------ closing
    def closeEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """With a calculation running it asks once, and stops it for real
        (guide §14); with changes not saved, it asks to discard them. Both
        are asked before anything is done, so a Cancel leaves all as it was."""
        running = self.running_jobs()
        if running and not self.confirm_stop_calculation():
            event.ignore()
            return
        if self.session.unsaved and not self.confirm_discard():
            event.ignore()
            return
        if running:
            self.compute_window.stop_all()
            self.compute_window.hide()
        if getattr(self, "_agent_bridge", None) is not None:
            self._agent_bridge.stop()
        for name in ("_interpret_window", "_info_window"):
            if getattr(self, name, None) is not None:
                getattr(self, name).close()
        if self._own_session:
            self.session.close()
        super().closeEvent(event)


def about_text() -> str:
    return (f"OGR FEM2D {ogr_fem2d.__version__}\n\n" + tr(
        "2-D geotechnical analysis by finite elements, part of the OpenGeoRock Suite.") + "\n\n"
        + "Samuel Sáez López, Universidad Politécnica de Cartagena (UPCT).\n"
        + tr("Licence: AGPL-3.0-or-later.") + "\n"
        + tr("Icons: Font Awesome Free (CC BY 4.0, SIL OFL 1.1), through qtawesome (MIT)."))
