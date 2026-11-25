# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The materials (spec 006, T26; RF-14; spec 004, D9, D11 and D16): the list
of the model's materials on the left, each with its colour, and the one
chosen on the right, as the reference program's dialog had them.

* **each action is an operation, done at once** (one step to undo each):
  Add (``material_set`` without an id), Delete (``material_delete``, which
  refuses a material a region has, and the dialog says so), Apply
  (``material_set`` with only what changed). Choosing another material
  applies what was changed in the one shown first;
* **E and nu have no default** (D16): a new material shows them «to be
  given», and the list marks a material without them, which calculating
  refuses naming it;
* **the unit weight acts only with self weight** (D11): the field is
  enabled only with an initial loading that has the body force, and says
  why when it is not;
* the values are shown in the model's units and kept in kPa and kN/m³
  (``dialogs.fields``).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPushButton, QVBoxLayout, QWidget)

from ogr_core.units import Quantity as Q
from ogr_ui.dialog_size import open_at_content_size
from ogr_ui.i18n import tr

from ...model import model as md
from .fields import Number

#: the initial loadings, as the reference program names them
LOADINGS = ((md.FIELD_STRESS, "Field stress only"),
            (md.FIELD_AND_BODY, "Field stress and body force"),
            (md.BODY_FORCE, "Body force only"),
            (md.NO_LOADING, "None"))
WITH_WEIGHT = (md.FIELD_AND_BODY, md.BODY_FORCE)


def swatch(colour: str) -> QIcon:
    pix = QPixmap(14, 14)
    pix.fill(QColor(colour))
    return QIcon(pix)


def incomplete(mat: md.Material) -> bool:
    return mat.E is None or mat.nu is None


def entry(mat: md.Material) -> str:
    """The material's line in a list: its name, and what it lacks."""
    name = mat.name or mat.id
    return name + ("  " + tr("(E and ν to be given)") if incomplete(mat) else "")


class MaterialsDialog(QDialog):
    """``do(op, **kwargs)`` calls an operation and gives (its result, the
    refusal's text or None); ``model()`` gives the model as it is now."""

    def __init__(self, model: Callable[[], md.Model], do: Callable, parent=None,
                 material: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle(tr("Define Materials"))
        self._model, self._do = model, do
        m = model()
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        self.list = QListWidget()
        left.addWidget(self.list, 1)
        row = QHBoxLayout()
        self.add_button = QPushButton(tr("Add"))
        self.delete_button = QPushButton(tr("Delete"))
        row.addWidget(self.add_button)
        row.addWidget(self.delete_button)
        left.addLayout(row)
        lay.addLayout(left)

        right = QVBoxLayout()
        head = QFormLayout()
        self.name = QLineEdit()
        head.addRow(tr("Name"), self.name)
        self.colour = QPushButton()
        self.colour.clicked.connect(self._pick_colour)
        head.addRow(tr("Colour"), self.colour)
        self.loading = QComboBox()
        for key, text in LOADINGS:
            self.loading.addItem(tr(text), key)
        head.addRow(tr("Initial element loading"), self.loading)
        self.unit_weight = Number(m, 0.0, Q.UNIT_WEIGHT, lo=0.0)
        head.addRow(tr("Unit weight"), self.unit_weight.box)
        right.addLayout(head)
        elastic = QGroupBox(tr("Elastic properties (isotropic)"))
        ef = QFormLayout(elastic)
        self.E = Number(m, None, Q.PRESSURE, lo=0.0, none_text=tr("(to be given)"))
        self.nu = Number(m, None, Q.DIMENSIONLESS, decimals=4, lo=-1.0, hi=0.4999,
                         none_text=tr("(to be given)"))
        ef.addRow(tr("Young's modulus E"), self.E.box)
        ef.addRow(tr("Poisson's ratio ν"), self.nu.box)
        right.addWidget(elastic)
        self.error = QLabel("")
        self.error.setWordWrap(True)
        right.addWidget(self.error)
        right.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.apply_button = buttons.addButton(tr("Apply"), QDialogButtonBox.ButtonRole.ApplyRole)
        self.apply_button.clicked.connect(self.apply_shown)
        buttons.rejected.connect(self._close)
        right.addWidget(buttons)
        holder = QWidget()
        holder.setLayout(right)
        lay.addWidget(holder, 1)

        self.loading.currentIndexChanged.connect(self._show_weight)
        self.add_button.clicked.connect(self.add)
        self.delete_button.clicked.connect(self.delete)
        self._shown_id: Optional[str] = None
        self._colour = "#d4a373"
        self.fill(material)
        self.list.currentRowChanged.connect(self._chosen)
        open_at_content_size(self, QSize(560, 360))

    # ------------------------------------------------------------ the list
    def fill(self, choose: Optional[str] = None) -> None:
        m = self._model()
        self.list.blockSignals(True)
        self.list.clear()
        for mat in m.materials:
            item = QListWidgetItem(swatch(mat.color), entry(mat))
            item.setData(Qt.ItemDataRole.UserRole, mat.id)
            self.list.addItem(item)
        self.list.blockSignals(False)
        ids = [mat.id for mat in m.materials]
        target = choose if choose in ids else (self._shown_id if self._shown_id in ids else None)
        k = ids.index(target) if target else (0 if ids else -1)
        self.list.setCurrentRow(k)
        self._show(m.materials[k] if k >= 0 else None)

    def _chosen(self, k: int) -> None:
        if self._shown_id is not None and self.changes():
            self.apply_shown()                     # what was changed goes in first
            self.list.blockSignals(True)           # (filling the list again moved the row)
            self.list.setCurrentRow(k)
            self.list.blockSignals(False)
        m = self._model()
        self._show(m.materials[k] if 0 <= k < len(m.materials) else None)

    def _show(self, mat: Optional[md.Material]) -> None:
        self._shown_id = None if mat is None else mat.id
        on = mat is not None
        for w in (self.name, self.colour, self.loading, self.E.box, self.nu.box,
                  self.apply_button, self.delete_button):
            w.setEnabled(on)
        if mat is None:
            self.unit_weight.box.setEnabled(False)
            return
        self.name.setText(mat.name)
        self._set_colour(mat.color)
        self.loading.setCurrentIndex(max(self.loading.findData(mat.initial_loading), 0))
        self.unit_weight.set(mat.unit_weight)
        self.E.set(mat.E)
        self.nu.set(mat.nu)
        self._show_weight()
        self.error.setText("")

    def _show_weight(self) -> None:
        on = self._shown_id is not None and self.loading.currentData() in WITH_WEIGHT
        self.unit_weight.box.setEnabled(on)
        self.unit_weight.box.setToolTip("" if on else tr(
            "The unit weight acts only with an initial loading that has the body force."))

    def _set_colour(self, colour: str) -> None:
        self._colour = colour
        self.colour.setIcon(swatch(colour))
        self.colour.setText(colour)

    def _pick_colour(self) -> None:
        c = QColorDialog.getColor(QColor(self._colour), self, tr("Colour"))
        if c.isValid():
            self._set_colour(c.name())

    # ------------------------------------------------------------ what it does
    def shown(self) -> Optional[md.Material]:
        return None if self._shown_id is None else self._model().material(self._shown_id)

    def changes(self) -> dict:
        """The arguments of ``material_set`` that changed in the one shown."""
        mat = self.shown()
        if mat is None:
            return {}
        now = {"name": self.name.text(), "color": self._colour,
               "initial_loading": self.loading.currentData(),
               "unit_weight": self.unit_weight.value(), "E": self.E.value(),
               "nu": self.nu.value()}
        return {k: v for k, v in now.items() if v is not None and v != getattr(mat, k)}

    def apply_shown(self) -> bool:
        mat = self.shown()
        lost = [shown for shown, name, box in (("E", "E", self.E), ("ν", "nu", self.nu))
                if mat is not None and box.value() is None and getattr(mat, name) is not None]
        if lost:                        # the operation cannot take them away (D16): said
            self.error.setText(tr("%s cannot be taken away once given: write its value.")
                               % ", ".join(lost))
            return False
        changes = self.changes()
        if not changes:
            return True
        _got, refused = self._do("material_set", material=self._shown_id, **changes)
        if refused:
            self.error.setText(refused)
            return False
        self.fill(self._shown_id)
        return True

    def add(self) -> None:
        if self._shown_id is not None and not self.apply_shown():
            return
        got, refused = self._do("material_set", name=tr("Material %d")
                                % (len(self._model().materials) + 1))
        if refused:
            self.error.setText(refused)
            return
        self.fill(got["material"])

    def delete(self) -> None:
        if self._shown_id is None:
            return
        _got, refused = self._do("material_delete", material=self._shown_id)
        if refused:
            self.error.setText(refused)
            return
        self._shown_id = None
        self.fill()

    def _close(self) -> None:
        if self.apply_shown():
            self.accept()
