# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The assignment panel (spec 006, T26; RF-14; D7): a panel beside the canvas,
as the reference program's floating «Assign» window, that stays open while
the regions are clicked.

* choosing a material, **Excavate** or **Fill** puts the canvas in the mode
  of assigning that: a click inside a region assigns it there, in the stage
  shown (RF-15), through ``material_assign`` or ``region_excavate`` (one
  step each); a click outside every region is said;
* **This stage only** keeps an excavation (or a fill) to the stage shown;
  without it, it holds from that stage on. A region has one material for
  the whole analysis (RF-4, until spec 012): the operation refuses another
  one in a later stage, and the refusal is said;
* the list is the model's materials with their colour, kept up to date.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDockWidget, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QPushButton, QVBoxLayout, QWidget)

from ogr_ui.i18n import tr

from ..model import model as md
from .dialogs.materials import entry, swatch

#: what a click assigns: ("material", id), ("excavate", True) or ("excavate", False)
EXCAVATE, FILL = ("excavate", True), ("excavate", False)


class AssignPanel(QDockWidget):
    def __init__(self, window):
        super().__init__(tr("Assign"), window)
        self.setObjectName("assign_panel")
        self.w = window
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.addWidget(QLabel(tr("Choose, then click inside the regions:")))
        self.list = QListWidget()
        self.list.itemClicked.connect(self._material_chosen)
        lay.addWidget(self.list, 1)
        row = QHBoxLayout()
        self.excavate = QPushButton(tr("Excavate"))
        self.fill_button = QPushButton(tr("Fill"))
        self.excavate.clicked.connect(lambda: self.choose(EXCAVATE))
        self.fill_button.clicked.connect(lambda: self.choose(FILL))
        row.addWidget(self.excavate)
        row.addWidget(self.fill_button)
        lay.addLayout(row)
        self.this_stage_only = QCheckBox(tr("This stage only"))
        self.this_stage_only.setToolTip(tr(
            "An excavation or a fill in the stage shown only; without it, from that stage on."))
        lay.addWidget(self.this_stage_only)
        self.setWidget(body)
        self.what: Optional[tuple] = None

    def refresh(self, m: Optional[md.Model]) -> None:
        chosen = self.what[1] if self.what and self.what[0] == "material" else None
        self.list.clear()
        for mat in (() if m is None else m.materials):
            item = QListWidgetItem(swatch(mat.color), entry(mat))
            item.setData(Qt.ItemDataRole.UserRole, mat.id)
            self.list.addItem(item)
            if mat.id == chosen:
                item.setSelected(True)

    def _material_chosen(self, item: QListWidgetItem) -> None:
        self.choose(("material", item.data(Qt.ItemDataRole.UserRole)))

    def choose(self, what: tuple) -> None:
        """Assign ``what`` with the next clicks inside regions."""
        self.what = what
        self.w.tools.start_assign()
