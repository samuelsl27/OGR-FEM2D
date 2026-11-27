# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The queries of the interpretation (spec 006, T32; RF-19, RF-20; spec 005,
RF-11 to RF-15): a line or a polyline, a boundary (on it, or at a distance
to one side), every node, and a point through the stages.

A query is ``results_query``'s, as the command line and an agent ask it:
the window shows its rows as they come, in the units shown, with what
decided them (the stage, the method and the settings, defaults included:
rule 12); its chart is of those rows (against the distance along the
query, or against the stage); its table is ``results_table``'s, written in
the units the model shows (spec 005, D15).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QHeaderView, QLabel, QPushButton, QSpinBox,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from ogr_core.api import OgrApiError
from ogr_core.units import Quantity as Q
from ogr_ui.i18n import tr

from ...results import quantities as qt
from .. import i18n as fem_i18n
from .. import units
from ..dialogs.fields import Number

#: the kinds of query, as the window names them
KIND_TEXT = {"line": "Line", "boundary": "Boundary", "nodes": "All nodes",
             "history": "Through the stages"}
#: the settings a query says (its keys), and the words of their values
SETTING_TEXT = {"vertices": "Vertices", "points": "Points", "boundary": "Boundary",
                "distance": "Distance", "side": "Side", "x": "x", "y": "y"}
VALUE_TEXT = {"at the vertices": "at the vertices", "on it": "on it", "inside": "inside",
              "outside": "outside", "left": "left", "right": "right"}
SOURCE_TEXT = {"spr": "recovered (SPR)", "element": "its element's field",
               "spr+element": "recovered (SPR) and its element's field",
               "fe": "finite-element field", "": ""}
REASON_TEXT = {"outside": "outside the mesh", "excavated": "in an excavated region",
               "removed": "no active element"}
METHOD_TEXT = {
    "finite-element field (shape functions)": "The finite-element field (shape functions).",
    "superconvergent patch recovery per material (Zienkiewicz and Taylor 2000, §14.4), "
    "interpolated with the shape functions (Eq. 14.27)":
        "Superconvergent patch recovery, material by material (Zienkiewicz and Taylor 2000, "
        "§14.4), interpolated with the shape functions (Eq. 14.27).",
}
SIDES_CLOSED = (("inside", "inside"), ("outside", "outside"))
SIDES_OPEN = (("left", "left (of its direction)"), ("right", "right (of its direction)"))


class BoundaryQueryDialog(QDialog):
    """Which boundary, how many points on each segment, and at what
    distance to which side (D12: on it by default)."""

    def __init__(self, m, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Query on a Boundary"))
        self.m = m
        self.form = QFormLayout()
        self.boundary = QComboBox()
        for b in m.boundaries:
            self.boundary.addItem(f"{b.name or b.id} ({b.id})", b.id)
        self.boundary.currentIndexChanged.connect(self._sides)
        self.points = QSpinBox()
        self.points.setRange(0, 1000)
        self.points.setSpecialValueText(tr("at the vertices"))
        self.points.setToolTip(tr("Points on each segment; at the vertices, the boundary's own."))
        self.distance = Number(m, 0.0, Q.LENGTH, decimals=4)
        self.distance.box.setToolTip(tr("Along the boundary's normal: 0 is on the boundary."))
        self.side = QComboBox()
        self.distance.box.valueChanged.connect(self._sides)
        self.form.addRow(tr("Boundary:"), self.boundary)
        self.form.addRow(tr("Points per segment:"), self.points)
        self.form.addRow(tr("Distance:"), self.distance.box)
        self.form.addRow(tr("Side:"), self.side)
        lay = QVBoxLayout(self)
        lay.addLayout(self.form)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                              | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._sides()

    def _sides(self, *_a) -> None:
        b = self.m.boundary(self.boundary.currentData())
        keep = self.side.currentData()
        self.side.clear()
        for key, text in (SIDES_CLOSED if b is None or b.closed else SIDES_OPEN):
            self.side.addItem(tr(text), key)
        k = self.side.findData(keep)
        self.side.setCurrentIndex(max(0, k))
        on = (self.distance.value() or 0.0) != 0.0
        self.side.setEnabled(on)
        self.side.setToolTip("" if on else tr("A side is for a distance other than 0."))

    def query(self) -> dict:
        """The arguments of ``results_query`` (the distance in metres)."""
        d = self.distance.value() or 0.0
        return {"boundary": self.boundary.currentData(),
                "n": self.points.value() or None, "distance": d,
                "side": self.side.currentData() if d != 0.0 else None}


class QueryWindow(QDialog):
    """A query's rows, with what decided them, its chart and its table."""

    def __init__(self, win, kind: str, args: dict, got: dict, parent=None):
        super().__init__(parent or win)
        self.win, self.kind, self.args, self.got = win, kind, args, got
        m = win.session.model
        self.m = m
        q = qt.get(args["quantity"])
        self.q = q
        self.factor = win.factor(q.id)
        self.unit = win.unit_text(q.id)
        self.length = units.length_label(m)
        self.lf = units.length_factor(m)
        self.setWindowTitle(tr("Query: %s") % tr(KIND_TEXT[kind]))
        lay = QVBoxLayout(self)
        self.header = QLabel("\n".join(self.header_lines()))
        self.header.setWordWrap(True)
        lay.addWidget(self.header)
        self.table = QTableWidget()
        self.table.verticalHeader().hide()
        lay.addWidget(self.table, 1)
        self._fill()
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.btn_chart = QPushButton(tr("Chart..."))
        self.btn_chart.clicked.connect(self.chart)
        self.btn_chart.setEnabled(kind != "nodes")
        self.btn_chart.setToolTip(tr("A chart needs a line, a boundary or the stages.")
                                  if kind == "nodes" else "")
        self.btn_export = QPushButton(tr("Export Table..."))
        self.btn_export.clicked.connect(self.act_export)
        close = QPushButton(tr("Close"))
        close.clicked.connect(self.close)
        for b in (self.btn_chart, self.btn_export, close):
            buttons.addWidget(b)
        lay.addLayout(buttons)
        self.resize(720, 520)

    # ------------------------------------------------------------ what it says
    def header_lines(self) -> list[str]:
        g = self.got
        lines = [f"{tr(self.q.name(self.m.analysis))} [{self.unit}]"]
        if self.kind != "history":
            st = next((s for s in self.win.stages if s["id"] == g["stage"]), None)
            lines.append(tr("Stage: %s") % ((st or {}).get("name") or g["stage"]))
            lines.append(tr(METHOD_TEXT.get(g["method"], g["method"])))
            for key, value in g["settings"]:
                lines.append(f"{tr(SETTING_TEXT.get(key, key))}: {self._setting(key, value)}")
        else:
            x, y = units.to_user(self.m, (g["x"], g["y"]))
            lines.append(tr("At x = %s, y = %s (%s)") % (f"{x:.4g}", f"{y:.4g}", self.length))
        if g["state"] != "valid":
            lines.insert(0, tr("NOT VALID: %s") % tr(g["state"].capitalize()))
        return lines

    def _setting(self, key: str, value) -> str:
        if key == "distance":
            return f"{float(value) * self.lf:.4g} {self.length}"
        if key == "vertices":
            return "; ".join("(%s, %s)" % tuple(f"{c * self.lf:.4g}" for c in p) for p in value)
        if key in ("x", "y"):
            return f"{float(value) * self.lf:.4g} {self.length}"
        if isinstance(value, str):
            if value.endswith(" per segment"):
                return tr("%s per segment") % value.split()[0]
            return tr(VALUE_TEXT.get(value, value))
        return str(value)

    def rows(self) -> list[dict]:
        """The rows as shown: (distance or stage, x, y, value) in the units
        shown, the material's name and where the value comes from."""
        out = []
        if self.kind == "history":
            for k, s in enumerate(self.got["stages"]):
                for r in s["rows"]:
                    out.append(self._row(r, stage=s["name"] or s["stage"], index=k + 1))
        else:
            for r in self.got["rows"]:
                out.append(self._row(r))
        return out

    def _row(self, r: dict, stage=None, index=None) -> dict:
        mat = None if r.get("material") is None else self.m.materials[r["material"]]
        value = None if r["value"] is None else r["value"] * self.factor
        why = REASON_TEXT.get(r.get("reason") or "", r.get("reason") or "")
        return {"point": r["point"], "stage": stage, "index": index,
                "distance": None if r.get("distance") is None else r["distance"] * self.lf,
                "x": r["x"] * self.lf, "y": r["y"] * self.lf, "value": value,
                "material": None if mat is None else (mat.name or mat.id),
                "material_index": r.get("material"),
                "from": tr(SOURCE_TEXT.get(r.get("source") or "", r.get("source") or ""))
                if value is not None else tr(why)}

    def columns(self) -> list[tuple[str, str]]:
        first = [("stage", tr("Stage"))] if self.kind == "history" else \
            [("point", tr("Point"))] + ([("distance", tr("Distance (%s)") % self.length)]
                                        if self.kind != "nodes" else [])
        return first + [("x", f"x ({self.length})"), ("y", f"y ({self.length})"),
                        ("value", f"{tr(self.q.name(self.m.analysis))} ({self.unit})"),
                        ("material", tr("Material")), ("from", tr("From"))]

    def _fill(self) -> None:
        cols, rows = self.columns(), self.rows()
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels([t for _k, t in cols])
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, (key, _t) in enumerate(cols):
                v = r[key]
                text = "" if v is None else (f"{v:.6g}" if isinstance(v, float) else str(v))
                self.table.setItem(i, j, QTableWidgetItem(text))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    # ------------------------------------------------------------ the chart
    def series(self) -> list[tuple[str, list, list]]:
        """What the chart draws: one series per material (on a contact, a
        value from each side), against the distance or the stage."""
        by: dict = {}
        for r in self.rows():
            if r["value"] is None:
                continue
            x = r["index"] if self.kind == "history" else r["distance"]
            by.setdefault(r["material"], ([], []))
            by[r["material"]][0].append(x)
            by[r["material"]][1].append(r["value"])
        many = len(by) > 1
        return [(tr("material %s") % name if many and name else "", xs, ys)
                for name, (xs, ys) in by.items()]

    def chart(self):
        from ogr_ui.xy_chart import show_xy_chart
        xlabel = tr("Stage") if self.kind == "history" else tr("Distance (%s)") % self.length
        ylabel = f"{tr(self.q.name(self.m.analysis))} ({self.unit})"
        return show_xy_chart(self, self.windowTitle(), self.series(), xlabel, ylabel)

    # ------------------------------------------------------------ the table
    def ask_export_path(self) -> Optional[str]:
        path, _f = QFileDialog.getSaveFileName(self, tr("Export Table"), "", "CSV (*.csv)")
        return path or None

    def export(self, path: str) -> Optional[str]:
        """The query as ``results_table`` writes it; the refusal's text, or None."""
        try:
            self.win.session.call("results_table", path=path, overwrite=True,
                                  allow_invalid=True, **self.args)
        except OgrApiError as err:
            return fem_i18n.say(getattr(err, "message", str(err)))
        return None

    def act_export(self) -> None:
        path = self.ask_export_path()
        if path:
            said = self.export(path)
            self.header.setText("\n".join(self.header_lines() + (
                [said] if said else [tr("Written: %s") % path])))
