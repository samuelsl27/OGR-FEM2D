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
from PySide6.QtWidgets import QFileDialog, QLabel, QMainWindow, QMessageBox

from ogr_core.api import OgrApiError
from ogr_ui import disabled_reasons
from ogr_ui.i18n import tr
from ogr_ui.resources.icons import icon
from ogr_ui.user_prefs import Preferences
from ogr_ui.widgets.status_bar import OgrStatusBar

import ogr_fem2d
from . import i18n as fem_i18n
from . import menus
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
        self._empty = QLabel()
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(self._empty)
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
        self._mk("about", "About OGR FEM2D...", self.act_about, "about")
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
        self._empty.setText(tr("No model: File > New, or File > Open.") if not has else
                            tr("Draw the external boundary: Boundaries > Add External."))

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
    def _do(self, op: str, /, **kwargs):
        try:
            return self.session.call(op, **kwargs)
        except OgrApiError as err:
            self.show_error(err)
            return None

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
