# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The mesh's settings, in two steps (spec 006, T25; RF-14, RF-20; spec 003):
**Discretize** shows the nodes the boundaries will have without changing
the model, and **Mesh** makes the mesh, as the reference program's dialog
had them (Mesh is enabled once discretized).

* **graded** (spec 003, D5): the nodes spread over the excavations (or over
  the external when there is none), which has **no default**: an empty
  field is said, not filled in (guide §10); an optional bound on the length
  of every edge;
* **uniform**: the length of every edge, or an approximate number of
  elements to derive it from, one of the two;
* the element (T3 or T6) and **B**, the bound on the ratio of
  circumradius to shortest edge, with the smallest angle it guarantees
  written next to it (arcsin(1 / 2B), Shewchuk 2002a);
* **windows**: rectangles whose elements are no longer than their size. A
  window that is not a rectangle (given through ``mesh_settings``) is shown
  and kept as it is.

Lengths are shown in the model's units and kept in metres (``gui.units``).
What the dialog gives is the arguments of ONE ``mesh_settings``, only what
changed; a refusal is said in the dialog, which stays open.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Callable, Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QPushButton,
                               QRadioButton, QSpinBox, QTableWidget, QTableWidgetItem,
                               QVBoxLayout)

from ogr_core.units import Quantity as Q
from ogr_ui.dialog_size import open_at_content_size
from ogr_ui.i18n import tr

from ...mesh import geometry as g
from ...model import model as md
from .. import units
from .coordinates import TableError, read_number
from .fields import DecimalBox


def guaranteed_angle(b: float) -> float:
    """The smallest angle, in degrees, a bound B on circumradius over
    shortest edge guarantees: arcsin(1 / 2B) (Shewchuk 2002a)."""
    return math.degrees(math.asin(min(1.0, 1.0 / (2.0 * b))))


def _rectangle(polygon) -> Optional[tuple[float, float, float, float]]:
    """(x0, y0, x1, y1) if ``polygon`` is a rectangle along the axes."""
    if len(polygon) != 4:
        return None
    xs, ys = sorted({p[0] for p in polygon}), sorted({p[1] for p in polygon})
    if len(xs) != 2 or len(ys) != 2:
        return None
    if sorted(polygon) != sorted((x, y) for x in xs for y in ys):
        return None
    return xs[0], ys[0], xs[1], ys[1]


class MeshSetupDialog(QDialog):
    """``apply(kwargs)`` does ``mesh_settings`` and gives the refusal's
    text or None; ``discretize()`` and ``mesh()`` do the two steps and give
    the refusal's text or None."""

    def __init__(self, m: md.Model, apply: Callable[[dict], Optional[str]],
                 discretize: Callable[[], Optional[str]], mesh: Callable[[], Optional[str]],
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Mesh Setup"))
        self.model, self._apply, self._discretize, self._mesh = m, apply, discretize, mesh
        st = m.mesh_settings
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.kind = QComboBox()
        self.kind.addItem(tr("Graded"), g.GRADED)
        self.kind.addItem(tr("Uniform"), g.UNIFORM)
        self.kind.setCurrentIndex(max(self.kind.findData(st.kind), 0))
        form.addRow(tr("Mesh type"), self.kind)
        self.element = QComboBox()
        self.element.addItem(tr("3-noded triangles"), 3)
        self.element.addItem(tr("6-noded triangles"), 6)
        self.element.setCurrentIndex(max(self.element.findData(st.nodes_per_element), 0))
        form.addRow(tr("Element type"), self.element)
        self.bound = DecimalBox()
        self.bound.setDecimals(4)
        self.bound.setRange(g.DEFAULT_QUALITY_BOUND, 100.0)
        self.bound.setSingleStep(0.1)
        self.bound.setValue(st.quality_bound)
        self._bound_shown = self.bound.value()
        self.bound_note = QLabel("")
        self.bound.valueChanged.connect(self._show_bound)
        self._show_bound()
        row = QHBoxLayout()
        row.addWidget(self.bound)
        row.addWidget(self.bound_note, 1)
        form.addRow(tr("Quality bound B"), row)
        lay.addLayout(form)

        # graded
        self.graded = QGroupBox(tr("Graded"))
        gf = QFormLayout(self.graded)
        excavations = any(b.kind == md.EXCAVATION for b in m.boundaries)
        self.nodes = QSpinBox()
        self.nodes.setRange(0, 1_000_000)
        self.nodes.setSpecialValueText(tr("(to be given)"))
        self.nodes.setValue(st.boundary_nodes or 0)
        gf.addRow(tr("Nodes on the excavations") if excavations
                  else tr("Nodes on the external"), self.nodes)
        self.max_size = self._length(st.max_size, tr("(none)"))
        gf.addRow(tr("Longest edge (optional)"), self.max_size)
        lay.addWidget(self.graded)

        # uniform
        self.uniform = QGroupBox(tr("Uniform"))
        uf = QFormLayout(self.uniform)
        self.by_size = QRadioButton(tr("Element size"))
        self.by_count = QRadioButton(tr("Number of elements (about)"))
        (self.by_count if st.elements is not None else self.by_size).setChecked(True)
        self.size = self._length(st.size, tr("(to be given)"))
        self.count = QSpinBox()
        self.count.setRange(0, 10_000_000)
        self.count.setSpecialValueText(tr("(to be given)"))
        self.count.setValue(st.elements or 0)
        uf.addRow(self.by_size, self.size)
        uf.addRow(self.by_count, self.count)
        lay.addWidget(self.uniform)

        # windows
        box = QGroupBox(tr("Refinement windows"))
        wl = QVBoxLayout(box)
        length = units.label(m, Q.LENGTH)
        self.windows = QTableWidget(0, 5)
        self.windows.setHorizontalHeaderLabels(
            [tr("x min (%s)") % length, tr("y min (%s)") % length, tr("x max (%s)") % length,
             tr("y max (%s)") % length, tr("Size (%s)") % length])
        self.windows.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._windows_kept: list[Optional[g.Window]] = []
        for w in st.windows:
            self._add_window(w)
        wl.addWidget(self.windows)
        wrow = QHBoxLayout()
        self.window_add = QPushButton(tr("Add Window"))
        self.window_add.clicked.connect(lambda: self._add_window(None))
        self.window_remove = QPushButton(tr("Remove Window"))
        self.window_remove.clicked.connect(self._remove_window)
        wrow.addWidget(self.window_add)
        wrow.addWidget(self.window_remove)
        wrow.addStretch(1)
        wl.addLayout(wrow)
        lay.addWidget(box)

        self.error = QLabel("")
        self.error.setWordWrap(True)
        lay.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.discretize_button = buttons.addButton(tr("Discretize"),
                                                   QDialogButtonBox.ButtonRole.ActionRole)
        self.mesh_button = buttons.addButton(tr("Mesh"), QDialogButtonBox.ButtonRole.AcceptRole)
        self.mesh_button.setToolTip(tr("Discretize first."))
        self.apply_button = buttons.addButton(tr("Apply"), QDialogButtonBox.ButtonRole.ApplyRole)
        self.discretize_button.clicked.connect(self.do_discretize)
        self.mesh_button.clicked.connect(self.do_mesh)
        self.apply_button.clicked.connect(self._accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)
        self.kind.currentIndexChanged.connect(self._show_kind)
        self._show_kind()
        open_at_content_size(self, QSize(560, 560))

    # ------------------------------------------------------------ pieces
    def _length(self, value: Optional[float], none_text: str) -> QDoubleSpinBox:
        box = DecimalBox()
        box.setDecimals(3)
        box.setRange(0.0, 1e9)
        box.setSpecialValueText(none_text)
        box.setSuffix(" " + units.label(self.model, Q.LENGTH))
        box.setValue(0.0 if value is None else units.to_user_value(self.model, value, Q.LENGTH))
        box.setProperty("si", value)
        box.setProperty("shown", box.value())
        return box

    def _length_value(self, box: QDoubleSpinBox) -> Optional[float]:
        if box.value() == box.property("shown"):
            return box.property("si")                    # not touched: as it was
        return None if box.value() == 0.0 else units.from_user_value(
            self.model, box.value(), Q.LENGTH)

    def _show_bound(self) -> None:
        self.bound_note.setText(tr("smallest angle guaranteed: %.1f°")
                                % guaranteed_angle(self.bound.value()))

    def _show_kind(self) -> None:
        graded = self.kind.currentData() == g.GRADED
        self.graded.setEnabled(graded)
        self.uniform.setEnabled(not graded)
        self.mesh_button.setEnabled(False)               # to discretize again first

    def _shown(self, v: float) -> str:
        return units.number(units.to_user_value(self.model, v, Q.LENGTH), ".6g")

    def _add_window(self, w: Optional[g.Window]) -> None:
        r = self.windows.rowCount()
        self.windows.insertRow(r)
        rect = None if w is None else _rectangle(w.polygon)
        if w is not None and rect is None:                # kept as it is
            item = QTableWidgetItem(tr("a polygon of %d vertices") % len(w.polygon))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.windows.setItem(r, 0, item)
            self.windows.setSpan(r, 0, 1, 4)
            size = QTableWidgetItem(self._shown(w.size))
            size.setFlags(size.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.windows.setItem(r, 4, size)
        else:
            values = ("",) * 5 if w is None else tuple(self._shown(v) for v in (*rect, w.size))
            for c, text in enumerate(values):
                self.windows.setItem(r, c, QTableWidgetItem(text))
        self._windows_kept.append(w)

    def _remove_window(self) -> None:
        r = self.windows.currentRow()
        r = self.windows.rowCount() - 1 if r < 0 else r
        if r >= 0:
            self.windows.removeRow(r)
            del self._windows_kept[r]

    def _windows(self) -> tuple[g.Window, ...]:
        out = []
        for r, kept in enumerate(self._windows_kept):
            rect = None if kept is None else _rectangle(kept.polygon)
            if kept is not None and rect is None:
                out.append(kept)
                continue
            texts = [(self.windows.item(r, c).text().strip() if self.windows.item(r, c) else "")
                     for c in range(5)]
            if kept is not None and texts == [self._shown(v) for v in (*rect, kept.size)]:
                out.append(kept)                          # not touched: as it was
                continue
            try:
                x0, y0, x1, y1, size = (units.from_user_value(self.model, read_number(t), Q.LENGTH)
                                        for t in texts)
            except TableError:
                raise TableError(tr("Window %d: its corners and its size must be numbers.")
                                 % (r + 1)) from None
            out.append(g.Window(((x0, y0), (x1, y0), (x1, y1), (x0, y1)), size))
        return tuple(out)

    # ------------------------------------------------------------ what it gives
    def changes(self) -> dict:
        """The arguments of ``mesh_settings`` that the user changed."""
        st = self.model.mesh_settings
        kind = self.kind.currentData()
        graded = kind == g.GRADED
        bound = st.quality_bound if self.bound.value() == self._bound_shown else self.bound.value()
        now = {"kind": kind, "nodes_per_element": self.element.currentData(),
               "quality_bound": bound,
               "boundary_nodes": (self.nodes.value() or None) if graded else None,
               "max_size": self._length_value(self.max_size) if graded else None,
               "size": (self._length_value(self.size)
                        if not graded and self.by_size.isChecked() else None),
               "elements": ((self.count.value() or None)
                            if not graded and self.by_count.isChecked() else None)}
        out, clear = {}, []
        for k, v in now.items():
            if v != getattr(st, k):
                if v is None:
                    clear.append(k)
                else:
                    out[k] = v
        if clear:
            out["clear"] = clear
        windows = self._windows()
        if windows != st.windows:
            out["windows"] = [{"polygon": [list(p) for p in w.polygon], "size": w.size}
                              for w in windows]
        return out

    def _apply_changes(self) -> bool:
        """Apply what changed; False (and said) if refused."""
        try:
            changes = self.changes()
        except TableError as err:
            self.error.setText(str(err))
            return False
        refused = self._apply(changes) if changes else None
        if refused:
            self.error.setText(refused)
            return False
        self.error.setText("")
        return True

    def do_discretize(self) -> None:
        if not self._apply_changes():
            return
        refused = self._discretize()
        if refused:
            self.error.setText(refused)
            return
        self.mesh_button.setEnabled(True)
        self.mesh_button.setToolTip("")

    def do_mesh(self) -> None:
        if not self._apply_changes():
            return
        refused = self._mesh()
        if refused:
            self.error.setText(refused)
            return
        self.accept()

    def _accept(self) -> None:
        if self._apply_changes():
            self.accept()
