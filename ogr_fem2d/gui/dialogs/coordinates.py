# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The table of coordinates (spec 006, T22; D10): the vertices of a boundary
typed as rows of X and Y, which the reference program's prompt opened with
``t`` and which its users found more reliable than typing fast (P05).

A cell takes a number with a point or a comma as its decimal mark (D12); an
empty row is skipped; a cell that is not a number is said, naming its row,
and no point is taken.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import re

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHeaderView, QLabel, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from ogr_ui.i18n import tr

_NUMBER = re.compile(r"[-+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][-+]?\d+)?")


class TableError(ValueError):
    pass


def read_rows(rows) -> list[tuple[float, float]]:
    """The points of ``[(x text, y text)]`` (see the module's notes)."""
    out = []
    for k, (x, y) in enumerate(rows):
        x, y = (x or "").strip(), (y or "").strip()
        if not x and not y:
            continue
        if not (_NUMBER.fullmatch(x) and _NUMBER.fullmatch(y)):
            raise TableError(tr("Row %d: X and Y must be numbers.") % (k + 1))
        out.append((float(x.replace(",", ".")), float(y.replace(",", "."))))
    return out


class CoordinatesDialog(QDialog):
    def __init__(self, parent=None, rows: int = 8, length: str = "m"):
        super().__init__(parent)
        self.setWindowTitle(tr("Enter Coordinates"))
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(tr("The vertices in order; an empty row is skipped.")))
        self.table = QTableWidget(rows, 2)
        self.table.setHorizontalHeaderLabels([tr("X (%s)") % length, tr("Y (%s)") % length])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table)
        more = QPushButton(tr("Add Row"))
        more.clicked.connect(lambda: self.table.insertRow(self.table.rowCount()))
        lay.addWidget(more)
        self.error = QLabel("")
        lay.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("Add the vertices"))
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)
        self.result_points: list[tuple[float, float]] = []

    def set_rows(self, rows) -> None:
        self.table.setRowCount(max(len(rows), 1))
        for k, (x, y) in enumerate(rows):
            self.table.setItem(k, 0, QTableWidgetItem(str(x)))
            self.table.setItem(k, 1, QTableWidgetItem(str(y)))

    def rows(self):
        cell = lambda r, c: self.table.item(r, c).text() if self.table.item(r, c) else ""
        return [(cell(r, 0), cell(r, 1)) for r in range(self.table.rowCount())]

    def _accept(self) -> None:
        try:
            self.result_points = read_rows(self.rows())
        except TableError as err:
            self.error.setText(str(err))
            return
        self.accept()
