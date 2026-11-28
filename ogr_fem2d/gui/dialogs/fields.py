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

from typing import Optional

from ogr_core.units import Quantity as Q
from ogr_ui.widgets import NumberBox

from ...model import model as md
from .. import units


#: the number box of the dialogs: a decimal point, and only a point, whatever the language and
#: the machine's locale, a comma refused as it is typed (D12, modified by the owner on
#: 2026-11-28); OGR GUI's since 0.2.0 (this program's own until then: Qt's box follows the
#: machine's locale, and with Spain's took «2.5» as 25)
DecimalBox = NumberBox


class Number:
    def __init__(self, m: md.Model, value: Optional[float], q: Q, decimals: int = 3,
                 lo: float = -1e12, hi: float = 1e12, none_text: Optional[str] = None):
        self.m, self.si, self.q, self.none_text = m, value, q, none_text
        self.box = DecimalBox()
        self.box.setRange(lo, hi)
        self.box.setDecimals(decimals)
        self.box.setStepType(NumberBox.StepType.AdaptiveDecimalStepType)
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
