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
        self.assign_panel = AssignPanel(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.assign_panel)
        self.assign_panel.hide()
        self.view.clicked.connect(self.tools.clicked)
        self.view.cursor_moved.connect(self.tools.moved)
        self.view.key_pressed.connect(self.tools.key)
        self._typed_points()
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
        self._mk("prefs", "Preferences...", self.act_preferences, "preferences")
        self._mk("exit", "Exit", self.close, None, "Ctrl+Q")
        self._mk("undo", "Undo", self.act_undo, "undo", "Ctrl+Z")
        self._mk("redo", "Redo", self.act_redo, "redo", "Ctrl+Y")
        self._mk("window_main", "Model", self.act_front, None)
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
        for key in ("project_settings", "stage_insert", "stage_rename", "field_stress",
                    "mesh_setup", "mesh_discretize", "mesh_generate", "define_materials",
                    "assign"):
            disabled_reasons.gate(self._actions[key], has, tr("There is no model: File > New."))
        disabled_reasons.gate(self._actions["stage_delete"], has and len(m.stages) > 1,
                              tr("The only stage cannot be deleted: add another first.")
                              if has else tr("There is no model: File > New."))
        self.view.length_factor = units.length_factor(m)
        state = None if m is None else mesh_state(m)
        disabled_reasons.gate(self._actions["mesh_reset"], state not in (None, "none"),
                              tr("There is no mesh."))
        self.view.mesh_stale = state == "stale"
        self.mesh_label.setText(self.mesh_text())
        self.mesh_label.setToolTip(self.mesh_notes())
        self.assign_panel.refresh(m)
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
    def _typed_points(self) -> None:
        """The status bar's X, Y field, with this program's reading of a
        point (absolute, relative, polar, a decimal comma: D10, D12). The
        field's own reading (absolute, points only) is left out."""
        field = self.statusBar().coord_input
        field.setValidator(None)
        field.returnPressed.disconnect()
        field.setPlaceholderText("x, y · @dx, dy · @d<a")
        field.setToolTip(tr("While drawing: x, y (or x; y with decimal commas), @dx, dy relative "
                            "to the last vertex, or @distance<angle in degrees; then Enter."))
        field.returnPressed.connect(self._typed)

    def _typed(self) -> None:
        field = self.statusBar().coord_input
        text = field.text()
        field.clear()
        self.tools.typed(text)

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
            self.statusBar().showMessage(
                tr("Converted: see the report of what came and what did not."), 10000)
        return got

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
        if path:
            self._do("project_save", path=path, overwrite=True)

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
        """The mesh, with what decided it on the status bar; the refusal's
        text, or None. It takes seconds with a large mesh (3.6 s for case
        005): the cursor says so."""
        from PySide6.QtWidgets import QApplication
        self.statusBar().showMessage(tr("Meshing..."))
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            QApplication.processEvents()
            got = self.session.call("mesh_generate")
        except OgrApiError as err:
            text = fem_i18n.say(getattr(err, "message", str(err)))
            self.statusBar().showMessage(text, 10000)
            return text
        finally:
            QApplication.restoreOverrideCursor()
        said = tr("Meshed: %d nodes, %d elements; smallest angle %.1f° (B = %.4g).") % (
            got["nodes"], got["elements"], got["min_angle"] or 0.0, got["quality_bound"])
        if got["warnings"]:
            said += " " + tr("Warnings of the mesher: %d (see the mesh on the status bar).") \
                % len(got["warnings"])
        self.statusBar().showMessage(said, 15000)
        return None

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
        if self.session.unsaved and not self.confirm_discard():
            event.ignore()
            return
        if self._own_session:
            self.session.close()
        super().closeEvent(event)


def about_text() -> str:
    return (f"OGR FEM2D {ogr_fem2d.__version__}\n\n" + tr(
        "2-D geotechnical analysis by finite elements, part of the OpenGeoRock Suite.") + "\n\n"
        + "Samuel Sáez López, Universidad Politécnica de Cartagena (UPCT).\n"
        + tr("Licence: AGPL-3.0-or-later.") + "\n"
        + tr("Icons: Font Awesome Free (CC BY 4.0, SIL OFL 1.1), through qtawesome (MIT)."))
