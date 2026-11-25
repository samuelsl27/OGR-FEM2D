# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The project settings (spec 006, T23; RF-14): the kind of analysis, the unit
system shown and the project's summary, as OGR Slip2D's dialog has them (a
list of pages on the left, the page on the right).

* what it shows comes from the model, and what it gives (``changes``) is
  only what the user changed, the arguments of ONE ``project_settings``
  (one step to undo);
* the dialog says what each choice does: axisymmetry takes x as the radius
  and the axis as x = 0 (a vertex with x < 0 is refused); the unit system
  changes what is shown, never the values, which are kept in m, kN and kPa
  (spec 004, D5);
* a refusal of the operation (axisymmetry with a vertex left of the axis)
  is said in the dialog, which stays open with what was written.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QSize
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QPlainTextEdit,
                               QRadioButton, QStackedWidget, QVBoxLayout, QWidget)

from ogr_core.units.unit_system import SYSTEMS
from ogr_ui.dialog_size import list_width, open_at_content_size
from ogr_ui.i18n import tr

from ...model import model as md


def _note(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    return label


class ProjectSettingsDialog(QDialog):
    """``apply(changes)`` does the change and gives the refusal's text, or
    None; the dialog closes only when there is none."""

    def __init__(self, m: md.Model, apply: Callable[[dict], Optional[str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Project Settings"))
        self.model, self._apply = m, apply
        self.pages = QListWidget()
        self.stack = QStackedWidget()
        self._page(tr("General"), self._general(m))
        self._page(tr("Project Summary"), self._summary(m))
        self.pages.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.pages.setCurrentRow(0)
        self.pages.setFixedWidth(list_width(self.pages))
        body = QHBoxLayout()
        body.addWidget(self.pages)
        body.addWidget(self.stack, 1)
        lay = QVBoxLayout(self)
        lay.addLayout(body)
        self.error = QLabel("")
        self.error.setWordWrap(True)
        lay.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("Apply"))
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)
        self.stack.setMinimumWidth(420)
        open_at_content_size(self, QSize(600, 420))

    def _page(self, name: str, widget: QWidget) -> None:
        self.pages.addItem(name)
        self.stack.addWidget(widget)

    def _general(self, m: md.Model) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        kind = QGroupBox(tr("Analysis"))
        k = QVBoxLayout(kind)
        self.plane = QRadioButton(tr("Plane strain"))
        self.axisymmetric = QRadioButton(tr("Axisymmetric"))
        (self.axisymmetric if m.analysis == md.AXISYMMETRIC else self.plane).setChecked(True)
        k.addWidget(self.plane)
        k.addWidget(_note(tr("A section of a long body: no strain out of the plane; a load is "
                             "per metre out of the plane.")))
        k.addWidget(self.axisymmetric)
        k.addWidget(_note(tr("A body of revolution: x is the radius and the axis is x = 0, so the "
                             "model lies on x ≥ 0; a point load is of the whole ring.")))
        lay.addWidget(kind)
        units = QGroupBox(tr("Units"))
        u = QFormLayout(units)
        self.units = QComboBox()
        for sid, s in SYSTEMS.items():
            self.units.addItem(tr(s.label), sid)
        self.units.setCurrentIndex(max(self.units.findData(m.units), 0))
        self.units_shown = QLabel("")
        self.units.currentIndexChanged.connect(self._show_units)
        self._show_units()
        u.addRow(tr("Shown in"), self.units)
        u.addRow("", self.units_shown)
        u.addRow(_note(tr("The values are kept in m, kN and kPa: the unit system changes what is "
                          "shown and how what is typed is read, never the values.")))
        lay.addWidget(units)
        lay.addStretch(1)
        return page

    def _show_units(self) -> None:
        self.units_shown.setText(SYSTEMS[self.units.currentData()].summary)

    def _summary(self, m: md.Model) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        s = m.summary
        self.title_edit = QLineEdit(s.title)
        self.author_edit = QLineEdit(s.author)
        self.date_edit = QLineEdit(s.date)
        self.notes_edit = QPlainTextEdit(s.notes)
        form.addRow(tr("Title"), self.title_edit)
        form.addRow(tr("Author"), self.author_edit)
        form.addRow(tr("Date"), self.date_edit)
        form.addRow(tr("Notes"), self.notes_edit)
        return page

    # ------------------------------------------------------------ what it gives
    def changes(self) -> dict:
        """The arguments of ``project_settings`` that the user changed."""
        m = self.model
        now = {"analysis": md.AXISYMMETRIC if self.axisymmetric.isChecked() else md.PLANE_STRAIN,
               "units": self.units.currentData(),
               "title": self.title_edit.text(), "author": self.author_edit.text(),
               "date": self.date_edit.text(), "notes": self.notes_edit.toPlainText()}
        was = {"analysis": m.analysis, "units": m.units, "title": m.summary.title,
               "author": m.summary.author, "date": m.summary.date, "notes": m.summary.notes}
        return {k: v for k, v in now.items() if v != was[k]}

    def _accept(self) -> None:
        changes = self.changes()
        refused = self._apply(changes) if changes else None
        if refused:
            self.error.setText(refused)
            return
        self.accept()
