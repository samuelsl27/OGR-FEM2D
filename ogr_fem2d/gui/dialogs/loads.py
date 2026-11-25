# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The dialogs of the conditions and the loads (spec 006, T27; RF-14, RF-16;
spec 004, D6, D7 and D10): what an imposed displacement, a distributed load
or a point load is, before it is put on the boundary by clicks; and the
factors of every load and condition in every stage.

* **the convention is written next to each value** (RF-16): a normal load
  is positive when it pushes into the ground; the other orientations are
  positive along their direction (vertical: downward); a point load is per
  metre out of the plane (in axisymmetry, of the whole ring); a
  displacement is along +x and +y;
* **the factors by stage** (D10): the total in a stage is factor x value; a
  restraint is active or not; an imposed displacement whose factor is
  empty does not act there. Each change is one operation
  (``load_stage``, ``condition_stage``) in that stage only.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHeaderView,
                               QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout)

from ogr_core.units import Quantity as Q
from ogr_ui.dialog_size import open_at_content_size
from ogr_ui.i18n import tr

from ...model import model as md
from .coordinates import TableError, read_number
from .fields import Number

ORIENTATION_NAMES = {
    md.NORMAL: "Normal to the boundary (+ into the ground)",
    md.VERTICAL: "Vertical (+ downward)",
    md.HORIZONTAL: "Horizontal (+ towards +x)",
    md.ANGLE_FROM_HORIZONTAL: "At an angle from the horizontal (anticlockwise)",
    "angle_to_boundary": "At an angle to the boundary (anticlockwise)",
}


def _buttons(dialog: QDialog, verb: str) -> QDialogButtonBox:
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                               | QDialogButtonBox.StandardButton.Cancel)
    buttons.button(QDialogButtonBox.StandardButton.Ok).setText(verb)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    return buttons


class ImposeDialog(QDialog):
    """An imposed displacement: ux and/or uy (an empty one is not imposed)."""

    def __init__(self, m: md.Model, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Impose Displacement"))
        lay = QVBoxLayout(self)
        form = self.form = QFormLayout()
        self.ux = Number(m, None, Q.LENGTH, decimals=6, lo=-1e9, none_text=tr("(not imposed)"))
        self.uy = Number(m, None, Q.LENGTH, decimals=6, lo=-1e9, none_text=tr("(not imposed)"))
        form.addRow(tr("ux (+ towards +x)"), self.ux.box)
        form.addRow(tr("uy (+ upward)"), self.uy.box)
        lay.addLayout(form)
        lay.addWidget(QLabel(tr("Then click the segments or vertices where it goes.")))
        lay.addWidget(_buttons(self, tr("Choose where")))

    def params(self) -> dict:
        out = {"kind": md.DISPLACEMENT}
        for name, box in (("ux", self.ux), ("uy", self.uy)):
            v = box.value()
            if v is not None:
                out[name] = v
        return out


class LoadDialog(QDialog):
    """A distributed load (from its start to its end) or a point load."""

    def __init__(self, m: md.Model, kind: str, parent=None):
        super().__init__(parent)
        self.kind = kind
        point = kind == "point"
        self.setWindowTitle(tr("Add Point Load") if point else tr("Add Distributed Load"))
        lay = QVBoxLayout(self)
        form = self.form = QFormLayout()
        q = Q.FORCE if point else Q.PRESSURE
        self.magnitude = Number(m, 0.0, q)
        self.magnitude_end = None
        if point:
            per = (tr("of the whole ring") if m.analysis == md.AXISYMMETRIC
                   else tr("per metre out of the plane"))
            form.addRow(tr("Magnitude (%s)") % per, self.magnitude.box)
        else:
            self.magnitude_end = Number(m, None, q, lo=-1e12 - 1.0,
                                        none_text=tr("(as at the start)"))
            form.addRow(tr("Magnitude at the start"), self.magnitude.box)
            form.addRow(tr("Magnitude at the end"), self.magnitude_end.box)
        self.orientation = QComboBox()
        for key in (md.POINT_ORIENTATIONS if point else md.ORIENTATIONS):
            self.orientation.addItem(tr(ORIENTATION_NAMES.get(key, key)), key)
        form.addRow(tr("Orientation"), self.orientation)
        self.angle = Number(m, 0.0, Q.ANGLE)
        form.addRow(tr("Angle"), self.angle.box)
        self.orientation.currentIndexChanged.connect(self._show_angle)
        self._show_angle()
        lay.addLayout(form)
        lay.addWidget(QLabel(tr("Then click the vertices where it goes.") if point else
                             tr("Then click the segments where it goes (start to end, in the "
                                "order of the boundary's vertices).")))
        lay.addWidget(_buttons(self, tr("Choose where")))

    def _show_angle(self) -> None:
        on = "angle" in (self.orientation.currentData() or "")
        self.angle.box.setEnabled(on)
        self.angle.box.setToolTip("" if on else tr("Only for an orientation at an angle."))

    def params(self) -> dict:
        out = {"kind": self.kind, "magnitude": self.magnitude.value(),
               "orientation": self.orientation.currentData()}
        if "angle" in out["orientation"]:
            out["angle"] = self.angle.value()
        if self.magnitude_end is not None and self.magnitude_end.value() is not None:
            out["magnitude_end"] = self.magnitude_end.value()
        return out


class StageFactorsDialog(QDialog):
    """Every load and condition by stage: a factor, or active or not."""

    def __init__(self, m: md.Model, do: Callable, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Factors by Stage"))
        self.model, self._do = m, do
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(tr("The total in a stage is factor × value (0 takes a load off); a "
                                "restraint is ticked where it acts; an imposed displacement with "
                                "no factor does not act there.")))
        self.rows: list[tuple[str, int]] = [("load", k) for k in range(len(m.loads))]
        self.rows += [("condition", k) for k in range(len(m.conditions))]
        n = len(m.stages)
        self.table = QTableWidget(len(self.rows), n)
        self.table.setHorizontalHeaderLabels([s.name or tr("Stage %s") % s.id for s in m.stages])
        self.table.setVerticalHeaderLabels([self._name(kind, k) for kind, k in self.rows])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for r, (kind, k) in enumerate(self.rows):
            for s in range(n):
                self.table.setItem(r, s, self._cell(kind, k, s))
        lay.addWidget(self.table)
        self.error = QLabel("")
        self.error.setWordWrap(True)
        lay.addWidget(self.error)
        buttons = _buttons(self, tr("Apply"))
        buttons.accepted.disconnect()
        buttons.accepted.connect(self._accept)
        lay.addWidget(buttons)
        open_at_content_size(self, QSize(560, 320))

    def _name(self, kind: str, k: int) -> str:
        if kind == "load":
            ld = self.model.loads[k]
            what = tr("point load") if isinstance(ld, md.PointLoad) else tr("distributed load")
        else:
            c = self.model.conditions[k]
            what = tr("imposed displacement") if c.kind == md.DISPLACEMENT else \
                tr("restraint %s") % c.kind
        return f"{k + 1}. {what}"

    def _cell(self, kind: str, k: int, s: int) -> QTableWidgetItem:
        if kind == "load":
            f = self.model.loads[k].factors
            return QTableWidgetItem(f"{f[s] if s < len(f) else 1.0:g}")
        c = self.model.conditions[k]
        if c.kind == md.DISPLACEMENT:
            f = c.factors[s] if s < len(c.factors) else 1.0
            return QTableWidgetItem("" if f is None else f"{f:g}")
        item = QTableWidgetItem("")
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        active = c.active[s] if s < len(c.active) else True
        item.setCheckState(Qt.CheckState.Checked if active else Qt.CheckState.Unchecked)
        return item

    def changes(self) -> list[tuple[str, dict]]:
        """The operations that make the table the model's, in order."""
        out = []
        for r, (kind, k) in enumerate(self.rows):
            for s, stage in enumerate(self.model.stages):
                item = self.table.item(r, s)
                was = self._cell(kind, k, s)
                if kind == "condition" and self.model.conditions[k].kind != md.DISPLACEMENT:
                    now = item.checkState() == Qt.CheckState.Checked
                    if now != (was.checkState() == Qt.CheckState.Checked):
                        out.append(("condition_stage", {"condition": k, "stage": stage.id,
                                                        "active": now, "this_stage_only": True}))
                    continue
                text = item.text().strip()
                if text == was.text():
                    continue
                if kind == "condition" and text == "":
                    value = None
                else:
                    try:
                        value = read_number(text)
                    except TableError:
                        raise TableError(tr("Row %d, %s: write a number.") % (
                            r + 1, self.table.horizontalHeaderItem(s).text())) from None
                if kind == "load":
                    out.append(("load_stage", {"load": k, "stage": stage.id, "factor": value,
                                               "this_stage_only": True}))
                else:
                    out.append(("condition_stage", {"condition": k, "stage": stage.id,
                                                    "factor": value, "this_stage_only": True}))
        return out

    def _accept(self) -> None:
        try:
            changes = self.changes()
        except TableError as err:
            self.error.setText(str(err))
            return
        for op, kwargs in changes:
            _got, refused = self._do(op, **kwargs)
            if refused:
                self.error.setText(refused)
                return
        self.accept()
