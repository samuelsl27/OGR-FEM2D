# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The field stress (spec 006, T24; RF-14, RF-16; spec 004, D6 and D14): the
stress in the ground before the first stage.

* **constant**: sigma_1, sigma_3 (in the plane), sigma_z (out of it) and
  the angle of sigma_1 from the horizontal, anticlockwise;
* **gravity**: the elevation of the ground surface and the horizontal
  strata from the top down, each to its bottom with its unit weight, its K
  (in the plane) and its Kz (out of it), as ``initial_stress.Stratum``.

**The convention is written next to every field** (RF-16): compression
positive, as the model keeps it (004, D6); the conversion to the engine's
stays in its one place (``model/conventions.py``, rule 10). The values are
shown in the model's unit system and kept in kPa, m and kN/m³ (004, D5): a
value the user did not touch goes back exactly as it was, not through the
rounding of what is shown.

The dialog gives the arguments of ONE ``field_set`` (one step to undo), or
nothing when nothing changed; a refusal of the operation (sigma_1 smaller
than sigma_3, a stratum whose bottom is not below its top) is said in the
dialog, which stays open. With no strata yet, the first one goes down to
the bottom of the model; its unit weight, K and Kz, and every cell of a
stratum added, are the user's to write (no default that moves the number,
guide §10).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QSize
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout,
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QPushButton,
                               QRadioButton, QStackedWidget, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from ogr_core.units import Quantity as Q
from ogr_ui.dialog_size import open_at_content_size
from ogr_ui.i18n import tr

from ...model import model as md
from .. import units
from ..canvas import paths
from .coordinates import TableError, read_number
from .fields import Number as _Number

#: the columns of the strata: (the model's name, its quantity)
STRATA = (("bottom", Q.LENGTH), ("unit_weight", Q.UNIT_WEIGHT), ("k", Q.DIMENSIONLESS),
          ("kz", Q.DIMENSIONLESS))


def _note(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    return label


class FieldStressDialog(QDialog):
    """``apply(kwargs)`` does ``field_set`` and gives the refusal's text, or
    None; the dialog closes only when there is none."""

    def __init__(self, m: md.Model, apply: Callable[[dict], Optional[str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Field Stress"))
        self.model, self._apply = m, apply
        f = m.field
        const = f if isinstance(f, md.ConstantField) else md.ConstantField()
        lay = QVBoxLayout(self)
        kind = QHBoxLayout()
        self.constant = QRadioButton(tr("Constant"))
        self.gravity = QRadioButton(tr("Gravity"))
        (self.gravity if isinstance(f, md.GravityField) else self.constant).setChecked(True)
        kind.addWidget(QLabel(tr("Field stress type:")))
        kind.addWidget(self.constant)
        kind.addWidget(self.gravity)
        kind.addStretch(1)
        lay.addLayout(kind)
        self.pages = QStackedWidget()
        self.pages.addWidget(self._constant_page(m, const))
        self.pages.addWidget(self._gravity_page(m, f))
        self.gravity.toggled.connect(lambda on: self.pages.setCurrentIndex(1 if on else 0))
        self.pages.setCurrentIndex(1 if self.gravity.isChecked() else 0)
        lay.addWidget(self.pages)
        self.error = QLabel("")
        self.error.setWordWrap(True)
        lay.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("Apply"))
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)
        open_at_content_size(self, QSize(520, 420))

    # ------------------------------------------------------------ pages
    def _constant_page(self, m: md.Model, f: md.ConstantField) -> QWidget:
        page = QGroupBox(tr("Constant field (compression positive)"))
        form = QFormLayout(page)
        self.sigma_1 = _Number(m, f.sigma_1, Q.PRESSURE)
        self.sigma_3 = _Number(m, f.sigma_3, Q.PRESSURE)
        self.sigma_z = _Number(m, f.sigma_z, Q.PRESSURE)
        self.angle = _Number(m, f.angle, Q.ANGLE)
        form.addRow(tr("σ1, major in the plane (compression +)"), self.sigma_1.box)
        form.addRow(tr("σ3, minor in the plane (compression +)"), self.sigma_3.box)
        form.addRow(tr("σz, out of the plane (compression +)"), self.sigma_z.box)
        form.addRow(tr("Angle of σ1 from the horizontal (anticlockwise)"), self.angle.box)
        if m.analysis == md.AXISYMMETRIC:
            form.addRow(_note(tr("In axisymmetry σz is the hoop stress σθ: the field needs "
                                 "σr = σθ and τrz = 0 (radial equilibrium), so σ1 horizontal at "
                                 "0° (or σ3 at 90°) equal to σz.")))
        return page

    def _gravity_page(self, m: md.Model, f) -> QWidget:
        page = QGroupBox(tr("Gravitational field (compression positive)"))
        lay = QVBoxLayout(page)
        form = QFormLayout()
        box = paths.bounds(m)
        top = box[3] if box is not None else 0.0
        self.bottom_of_model = box[1] if box is not None else top - 10.0
        self.surface = _Number(m, f.surface if isinstance(f, md.GravityField) else top, Q.LENGTH)
        form.addRow(tr("Elevation of the ground surface"), self.surface.box)
        lay.addLayout(form)
        strata_note = tr("The strata from the top down, each to its bottom: σv is the weight "
                         "of what is above, σh = K σv in the plane and σz = Kz σv out of it.")
        lay.addWidget(_note(strata_note))
        self.strata = QTableWidget(0, len(STRATA))
        self.strata.setHorizontalHeaderLabels([
            tr("Bottom (%s)") % units.label(m, Q.LENGTH),
            tr("Unit weight (%s)") % units.label(m, Q.UNIT_WEIGHT), tr("K"), tr("Kz")])
        self.strata.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._strata_si = []
        for s in (f.strata if isinstance(f, md.GravityField) else ()):
            self._add_row([getattr(s, name) for name, _q in STRATA])
        if self.strata.rowCount() == 0:
            self._add_row([self.bottom_of_model, None, None, None])
        lay.addWidget(self.strata)
        row = QHBoxLayout()
        more = QPushButton(tr("Add Stratum"))
        more.clicked.connect(lambda: self._add_row([None] * len(STRATA)))
        less = QPushButton(tr("Remove Stratum"))
        less.clicked.connect(self._remove_row)
        row.addWidget(more)
        row.addWidget(less)
        self.strata_add, self.strata_remove = more, less
        row.addStretch(1)
        lay.addLayout(row)
        return page

    def _shown(self, value, q: Q) -> str:
        return "" if value is None else f"{units.to_user_value(self.model, value, q):.6g}"

    def _add_row(self, values) -> None:
        r = self.strata.rowCount()
        self.strata.insertRow(r)
        for c, ((_name, q), v) in enumerate(zip(STRATA, values)):
            self.strata.setItem(r, c, QTableWidgetItem(self._shown(v, q)))
        self._strata_si.append(list(values))

    def _remove_row(self) -> None:
        r = self.strata.currentRow()
        r = self.strata.rowCount() - 1 if r < 0 else r
        if r >= 0:
            self.strata.removeRow(r)
            del self._strata_si[r]

    def _strata(self) -> list[md.Stratum]:
        out = []
        for r in range(self.strata.rowCount()):
            values = []
            for c, (name, q) in enumerate(STRATA):
                item = self.strata.item(r, c)
                text = item.text().strip() if item else ""
                si = self._strata_si[r][c]
                if si is not None and text == self._shown(si, q):
                    values.append(si)                       # not touched: as it was
                    continue
                try:
                    v = read_number(text)
                except TableError:
                    raise TableError(tr("Stratum %d: write its %s.") % (
                        r + 1, self.strata.horizontalHeaderItem(c).text())) from None
                values.append(units.from_user_value(self.model, v, q))
            out.append(md.Stratum(*values))
        return out

    # ------------------------------------------------------------ what it gives
    def field(self):
        """The field as written (TableError if a cell is not a number)."""
        if self.constant.isChecked():
            return md.ConstantField(self.sigma_1.value(), self.sigma_3.value(),
                                    self.sigma_z.value(), self.angle.value())
        return md.GravityField(self.surface.value(), tuple(self._strata()))

    def changes(self) -> dict:
        """The arguments of ``field_set``, or {} if the field is the model's."""
        f = self.field()
        if f == self.model.field:
            return {}
        if isinstance(f, md.ConstantField):
            return {"kind": "constant", "sigma_1": f.sigma_1, "sigma_3": f.sigma_3,
                    "sigma_z": f.sigma_z, "angle": f.angle}
        return {"kind": "gravity", "surface": f.surface,
                "strata": [{"bottom": s.bottom, "unit_weight": s.unit_weight, "k": s.k,
                            "kz": s.kz} for s in f.strata]}

    def _accept(self) -> None:
        try:
            changes = self.changes()
        except TableError as err:
            self.error.setText(str(err))
            return
        refused = self._apply(changes) if changes else None
        if refused:
            self.error.setText(refused)
            return
        self.accept()
