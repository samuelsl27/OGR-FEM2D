# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A number of a dialog (spec 006, T24 and T26): kept in SI, shown in the
model's units (``gui.units``) with the unit in the box; a value the user did
not touch is given back exactly as it was, not through the rounding of what
is shown. A value that may be missing (E and nu until given, D16) shows
``none_text`` at the box's minimum and gives None there.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import re
from typing import Optional

from PySide6.QtCore import QLocale
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QDoubleSpinBox

from ogr_core.units import Quantity as Q

from ...model import model as md
from .. import units


#: what a box takes while it is being written: a sign, figures, one decimal point or comma, and
#: an exponent
_WRITING = re.compile(r"[-+]?\d*(?:[.,]\d*)?(?:[eE][-+]?\d*)?")


class DecimalBox(QDoubleSpinBox):
    """A number box that shows the language's decimal separator (D12: a
    comma in Spanish) and takes a point or a comma whatever the language,
    with no thousands separator: Qt's own box follows the machine's locale,
    and in Spanish would take «2.5» as 25 (T37's finding)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLocale(QLocale.c())
        self.setGroupSeparatorShown(False)

    def _body(self, text: str) -> str:
        t = text
        if self.prefix() and t.startswith(self.prefix()):
            t = t[len(self.prefix()):]
        if self.suffix() and t.endswith(self.suffix()):
            t = t[:-len(self.suffix())]
        return t.strip()

    def textFromValue(self, value: float) -> str:  # noqa: N802 - Qt's name
        return units.shown(super().textFromValue(value))

    def valueFromText(self, text: str) -> float:  # noqa: N802
        body = self._body(text)
        if self.specialValueText() and text == self.specialValueText():
            return self.minimum()
        try:
            return float(body.replace(",", "."))
        except ValueError:
            return self.value()

    def validate(self, text: str, pos: int):
        if self.specialValueText() and text == self.specialValueText():
            return QValidator.State.Acceptable, text, pos
        body = self._body(text)
        if not _WRITING.fullmatch(body):
            return QValidator.State.Invalid, text, pos
        try:
            v = float(body.replace(",", "."))
        except ValueError:
            return QValidator.State.Intermediate, text, pos
        if self.minimum() <= v <= self.maximum():
            return QValidator.State.Acceptable, text, pos
        return QValidator.State.Intermediate, text, pos


class Number:
    def __init__(self, m: md.Model, value: Optional[float], q: Q, decimals: int = 3,
                 lo: float = -1e12, hi: float = 1e12, none_text: Optional[str] = None):
        self.m, self.si, self.q, self.none_text = m, value, q, none_text
        self.box = DecimalBox()
        self.box.setRange(lo, hi)
        self.box.setDecimals(decimals)
        self.box.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        if none_text:
            self.box.setSpecialValueText(none_text)
        label = units.label(m, q)
        if label:
            self.box.setSuffix(" " + label)
        self.box.setValue(lo if value is None else units.to_user_value(m, value, q))
        self.shown = self.box.value()

    def value(self) -> Optional[float]:
        v = self.box.value()
        if v == self.shown:
            return self.si                                  # not touched: as it was
        if self.none_text and v == self.box.minimum():
            return None
        return units.from_user_value(self.m, v, self.q)

    def set(self, value: Optional[float]) -> None:
        """Show another kept value (another material in the same dialog)."""
        self.si = value
        self.box.setValue(self.box.minimum() if value is None
                          else units.to_user_value(self.m, value, self.q))
        self.shown = self.box.value()
