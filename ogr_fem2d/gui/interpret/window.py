# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The interpretation's window (spec 006, T31; RF-12, RF-19, RF-20; D11, D15;
the guide, §4 and §6).

The results of the model open in a window of their own, over the same
session, and are read only through the operations (``results_open``,
``results_field``, ``results_query``):

* **the selector is the catalogue** of spec 005 (``results.quantities``),
  with its names in axisymmetry when the model is axisymmetric (RF-6);
* **a tab per stage of the results** (RF-19); the stage shown is the one
  drawn and the one asked;
* **the field** is ``results_field``'s triangles contoured by
  ``drawn.draw`` and painted in one item (``FieldItem``); **its legend**
  says the quantity, the unit shown, the convention, the stage and where
  the values come from (recovered at the nodes, or the finite-element
  field), and paints with the settings' colours, the canvas's (guide §6);
* **its options**: the range (this stage, all stages, or the user's), the
  intervals, the palette and the mode (OGR-GUI's Contour Options), and the
  absolute value. «Fit to results» fits to the whole range of the values
  drawn (``fit_percentile=1``, OGR GUI 0.1.1): a percentile would hide the
  peak of a stress (T19), and the range is the one the drawing takes;
* **the value under the cursor** is the query's (``results_query``, kind
  ``at``), interpolated exactly, not read off the colours (D11);
* **results that are not valid are said**, above the canvas and in the
  legend and the title: stale (of another model), incomplete or cancelled
  (only the stages written). They are shown, as the operations show them
  with ``allow_invalid``, never as if valid (RF-12).

Values come from the operations in m, kN and kPa and are shown in the
model's units (``gui/units.py``, the window's one place for that).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import replace
from typing import Optional

import numpy as np

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QAction, QActionGroup, QColor, QPainterPath, QPen
from PySide6.QtWidgets import (QComboBox, QDockWidget, QGraphicsPathItem, QInputDialog, QLabel,
                               QMainWindow, QTabBar, QTextBrowser, QVBoxLayout, QWidget)

from ogr_core.api import OgrApiError
from ogr_core.units import Quantity as Q
from ogr_ui.contours import ContourMode, ContourSettings
from ogr_ui.i18n import tr
from ogr_ui.widgets.legend import ColourScaleLegend

from ...results import calculate as calc
from ...results import drawing
from ...results import quantities as qt
from .. import i18n as fem_i18n
from .. import units
from ..canvas.view import ModelView
from .drawn import Drawn, draw, merging
from .field_item import FieldItem

#: the quantity shown first
FIRST = "sigma_1"
#: the palette a field starts with (D5; the guide, §12): its lightness grows with the value,
#: so the order of the values reads in grey and to those who do not tell red from green
#: (OGR GUI's automatic settings start with a diverging one, light in the middle)
DEFAULT_PALETTE = "Viridis"
#: the core's quantity of each unit of the catalogue (None: shown as it is)
UNIT_Q = {qt.PRESSURE: Q.PRESSURE, qt.LENGTH: Q.LENGTH, qt.DIMENSIONLESS: None,
          qt.ANGLE: None}
#: the ranges, as the window offers them
RANGES = ((drawing.AUTO_STAGE, "This stage"), (drawing.AUTO_ALL, "All stages"),
          (drawing.CUSTOM, "Custom (Contour Options)"))
#: where the values come from, by kind
SOURCE_TEXT = {qt.STRESS: "Recovered at the nodes (SPR, material by material)",
               qt.STRAIN: "Recovered at the nodes (SPR, material by material)",
               qt.DISPLACEMENT: "At the nodes (the finite-element field)"}
#: the conventions of the catalogue, said
CONVENTION_TEXT = {"compression positive": "Compression positive",
                   "shortening positive": "Shortening positive",
                   "along +x and +y": "Positive along +x and +y",
                   "from +x, anticlockwise, degrees": "From +x, anticlockwise"}
#: results that are not valid, said above the canvas
STATE_TEXT = {
    calc.STALE: "These results are of another model: it changed after the calculation. "
                "Calculate again: Analysis > Compute.",
    "incomplete": "Incomplete results: a stage could not be solved; only the stages "
                  "before it are shown.",
    "cancelled": "Cancelled results: only the stages solved before the cancel are shown.",
}
#: the states of the results, as the panel of what decided it says them
STATE_WORD = {"valid": "Valid", "stale": "Stale", "incomplete": "Incomplete",
              "cancelled": "Cancelled"}
#: the queries drawn on the canvas
QUERY_PEN = "#111111"
#: what a query picks on the canvas, said on the status bar
PICK_TEXT = {"line": "Click the two ends of the line (Esc: cancel).",
             "polyline": "Click the vertices of the polyline; right click or Enter ends it "
                         "(Esc: cancel).",
             "history": "Click the point (Esc: cancel)."}
#: why a point has no value
REASON_TEXT = {"outside": "outside the mesh", "excavated": "in an excavated region",
               "removed": "no active element"}


class ResultsView(ModelView):
    """The model's canvas with a field over it: the regions, the mesh and
    the boundaries; not the field stress, the conditions nor the loads,
    which are of the modelling."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.show_mesh = False
        self.result_item: Optional[FieldItem] = None
        self.drawn: Optional[Drawn] = None
        self.opacity = 1.0
        #: the queries drawn: polylines of model points
        self.queries: list[list] = []
        self.query_items: list[QGraphicsPathItem] = []

    def _draw(self) -> None:
        super()._draw()
        self.result_item = None
        if self.drawn is not None and self.model is not None:
            self.result_item = FieldItem(self.drawn, self.opacity)
            self.scene().addItem(self.result_item)
        self.query_items = []
        if self.model is None:
            return
        pen = QPen(QColor(QUERY_PEN), 2.0)
        pen.setCosmetic(True)
        for points in self.queries:
            path = QPainterPath(QPointF(*points[0]))
            for p in points[1:]:
                path.lineTo(QPointF(*p))
            item = QGraphicsPathItem(path)
            item.setPen(pen)
            item.setZValue(3)
            self.scene().addItem(item)
            self.query_items.append(item)

    def show_field(self, drawn: Optional[Drawn], opacity: float = 1.0) -> None:
        self.drawn, self.opacity = drawn, opacity
        self._draw()

    def _draw_field(self) -> None:          # the field stress: modelling
        pass

    def _draw_conditions(self) -> None:
        pass

    def _draw_loads(self) -> None:
        pass


class InterpretWindow(QMainWindow):
    """The results of the session's model (see the module's notes)."""

    def __init__(self, main, parent=None):
        super().__init__(parent)
        self.main = main
        self.session = main.session
        self.setWindowTitle(tr("Interpret"))
        self._actions: dict[str, QAction] = {}
        #: quantity -> its settings, kept while the window lives
        self.settings: dict[str, ContourSettings] = {}
        self.quantity = FIRST
        self.range_mode = drawing.AUTO_STAGE
        self.absolute = False
        self.state: Optional[str] = None
        self.stages: list[dict] = []
        self.field: Optional[dict] = None
        #: (stage, level) -> the merging of its vertices (``drawn.merging``)
        self._merges: dict = {}
        #: what the canvas is picking for a query: {"kind", "points"}, or None
        self.picking: Optional[dict] = None
        self.query_windows: list = []

        self.view = ResultsView()
        self.view.cursor_moved.connect(self.show_value)
        self.view.clicked.connect(self._clicked)
        self.view.key_pressed.connect(self._key)
        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.setStyleSheet("QLabel { background: #fff3cd; color: #5c4400; "
                                  "padding: 6px; border: 1px solid #e0b000; }")
        self.banner.hide()
        self.stage_tabs = QTabBar()
        self.stage_tabs.setShape(QTabBar.Shape.RoundedSouth)
        self.stage_tabs.currentChanged.connect(lambda _k: self.redraw())
        centre = QWidget()
        lay = QVBoxLayout(centre)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.banner)
        lay.addWidget(self.view, 1)
        lay.addWidget(self.stage_tabs)
        self.setCentralWidget(centre)

        self.legend = ColourScaleLegend()
        self.legend_text = QLabel()
        self.legend_text.setWordWrap(True)
        side = QWidget()
        sl = QVBoxLayout(side)
        sl.addWidget(self.legend_text)
        sl.addWidget(self.legend, 1)
        sl.addWidget(QLabel(tr("What decided it")))
        #: the values that decided what is drawn (RF-20, rule 12)
        self.decided = QTextBrowser()
        self.decided.setMinimumWidth(260)
        sl.addWidget(self.decided, 1)
        dock = QDockWidget(tr("Legend"), self)
        dock.setObjectName("legend")
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setWidget(side)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

        self.quantity_box = QComboBox()
        self.quantity_box.currentIndexChanged.connect(self._quantity_chosen)
        self.range_box = QComboBox()
        for mode, text in RANGES:
            self.range_box.addItem(tr(text), mode)
        self.range_box.currentIndexChanged.connect(self._range_chosen)
        self.value_label = QLabel()
        self.statusBar().addPermanentWidget(self.value_label, 1)
        self._build_actions()
        bar = self.addToolBar(tr("Results"))
        bar.setObjectName("results")
        bar.addWidget(QLabel(tr("Quantity:") + " "))
        bar.addWidget(self.quantity_box)
        bar.addSeparator()
        bar.addWidget(QLabel(tr("Range:") + " "))
        bar.addWidget(self.range_box)
        bar.addAction(self._actions["absolute"])
        bar.addAction(self._actions["contour_options"])
        self.resize(1100, 720)

    # ------------------------------------------------------------ actions
    @property
    def actions_by_key(self) -> dict[str, QAction]:
        return dict(self._actions)

    def _mk(self, key: str, text: str, slot, shortcut: Optional[str] = None) -> QAction:
        act = QAction(tr(text), self)
        if shortcut:
            act.setShortcut(shortcut)
        act.triggered.connect(slot)
        self._actions[key] = act
        return act

    def _build_actions(self) -> None:
        self._mk("contour_options", "Contour Options...", self.act_contour_options)
        self._mk("absolute", "Absolute Value", self.act_absolute).setCheckable(True)
        group = QActionGroup(self)
        for mode, text in RANGES:
            act = self._mk("range_" + mode, text, lambda _c=False, md_=mode: self.set_range(md_))
            act.setCheckable(True)
            group.addAction(act)
        self._actions["range_" + drawing.AUTO_STAGE].setChecked(True)
        self._mk("zoom_all", "Zoom All", self.view.zoom_all, "F2")
        self._mk("show_mesh", "Mesh", self.act_show_mesh).setCheckable(True)
        self._mk("refresh", "Read the Results Again", self.open, "F5")
        self._mk("query_line", "Line...", lambda: self.pick("line"))
        self._mk("query_polyline", "Polyline...", lambda: self.pick("polyline"))
        self._mk("query_boundary", "On a Boundary...", self.act_query_boundary)
        self._mk("query_nodes", "All Nodes", self.act_query_nodes)
        self._mk("query_history", "Through the Stages at a Point...",
                 lambda: self.pick("history"))
        self._mk("query_clear", "Clear the Queries Drawn", self.act_query_clear)
        self._mk("window_model", "Model", self.act_model)
        self._mk("report", "Report...", lambda: self.main.act_report())
        self._mk("close", "Close", self.close)
        menus = (("Results", ("contour_options", "absolute", "-", "range_" + drawing.AUTO_STAGE,
                              "range_" + drawing.AUTO_ALL, "range_" + drawing.CUSTOM, "-",
                              "refresh", "report", "-", "close")),
                 ("Query", ("query_line", "query_polyline", "query_boundary", "query_nodes",
                            "-", "query_history", "-", "query_clear")),
                 ("View", ("zoom_all", "show_mesh")),
                 ("Window", ("window_model",)))
        for title, keys in menus:
            m = self.menuBar().addMenu(tr(title))
            for k in keys:
                if k == "-":
                    m.addSeparator()
                else:
                    m.addAction(self._actions[k])

    # ------------------------------------------------------------ opening
    def open(self) -> Optional[str]:
        """Read the results of the session's model again: their state and
        their stages, then draw. The refusal's text, or None."""
        try:
            got = self.session.call("results_open")
        except OgrApiError as err:
            return self._said(err)
        self.state = got["state"]
        self.stages = got["stages"]
        self.opened_info = got
        self._merges.clear()                       # the results may be others
        if not self.stages:
            text = tr("No results to show: %s") % (got.get("message") or self.state)
            self.statusBar().showMessage(text, 15000)
            return text
        m = self.session.model
        self._fill_quantities(m)
        keep = self.stage_tabs.currentIndex()
        self.stage_tabs.blockSignals(True)
        while self.stage_tabs.count():
            self.stage_tabs.removeTab(0)
        for s in self.stages:
            self.stage_tabs.addTab(s["name"] or tr("Stage %s") % s["id"])
        self.stage_tabs.setCurrentIndex(keep if 0 <= keep < len(self.stages)
                                        else len(self.stages) - 1)
        self.stage_tabs.blockSignals(False)
        said = STATE_TEXT.get(self.state)
        self.banner.setText(tr(said) if said else "")
        self.banner.setVisible(said is not None)
        title = m.summary.title or (self.session.path.stem if self.session.path else "")
        self.setWindowTitle(" — ".join(x for x in (
            tr("Interpret"), title, tr(self.state.capitalize()) if said else "") if x))
        first = self.view.model is None
        self.redraw()
        if first:
            self.view.zoom_all()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._warm_cursor)
        return None

    def _warm_cursor(self) -> None:
        """Ask one value once the field is drawn, so that the mesh's
        locator is made before the cursor needs it (0.24 s with case 005)."""
        m = self.session.model
        if m is not None and m.mesh is not None and m.mesh.nodes and self.stages:
            self.value_at(*m.mesh.nodes[0])

    def note_state(self) -> None:
        """The model changed: if its results changed state (stale, say),
        read them again, so the window says it (RF-12)."""
        try:
            state = self.session.call("results_open")["state"]
        except OgrApiError:
            state = None
        if state != self.state:
            self.open()

    def _fill_quantities(self, m) -> None:
        self.quantity_box.blockSignals(True)
        self.quantity_box.clear()
        kind = None
        for q in qt.CATALOGUE:
            if kind is not None and q.kind != kind:
                self.quantity_box.insertSeparator(self.quantity_box.count())
            kind = q.kind
            self.quantity_box.addItem(tr(q.name(m.analysis)), q.id)
        self.quantity_box.setCurrentIndex(self.quantity_box.findData(self.quantity))
        self.quantity_box.blockSignals(False)

    # ------------------------------------------------------------ choosing
    @property
    def stage_id(self) -> Optional[str]:
        k = self.stage_tabs.currentIndex()
        return self.stages[k]["id"] if 0 <= k < len(self.stages) else None

    def set_quantity(self, quantity: str) -> None:
        self.quantity_box.setCurrentIndex(self.quantity_box.findData(quantity))

    def _quantity_chosen(self, _k: int) -> None:
        data = self.quantity_box.currentData()
        if data:
            self.quantity = data
            self.redraw()

    def set_stage(self, k: int) -> None:
        self.stage_tabs.setCurrentIndex(k)

    def set_range(self, mode: str) -> None:
        self.range_box.setCurrentIndex(self.range_box.findData(mode))

    def _range_chosen(self, _k: int) -> None:
        self.range_mode = self.range_box.currentData()
        self._actions["range_" + self.range_mode].setChecked(True)
        self.redraw()

    def act_absolute(self, on: bool) -> None:
        self.absolute = bool(on)
        self.redraw()

    def act_show_mesh(self, on: bool) -> None:
        self.view.show_mesh = bool(on)
        self.view.show_field(self.view.drawn, self.view.opacity)

    def act_model(self) -> None:
        self.main.raise_()
        self.main.activateWindow()

    def settings_of(self, quantity: str) -> ContourSettings:
        if quantity not in self.settings:
            self.settings[quantity] = replace(ContourSettings.automatic(quantity),
                                              palette=DEFAULT_PALETTE)
        return self.settings[quantity]

    def contour_dialog(self):
        from ogr_ui.contours import ContourField
        from ogr_ui.dialogs.contour_options_dialog import ContourOptionsDialog
        s = self.settings_of(self.quantity)
        s.auto_range = self.range_mode != drawing.CUSTOM
        m = self.session.model
        name = qt.get(self.quantity).name(m.analysis)
        # the whole range (OGR GUI 0.1.1): the fit is then that of the drawing, this stage's
        # least and greatest value drawn, in the units shown; with the percentile at 1 the
        # fit takes only the two ends, and they are what is handed to it
        field = ContourField(self.quantity, name, s, fit_percentile=1.0)
        shown = [] if self.field is None else self.field["values"] * self.factor()
        ends = [] if not len(shown) else [float(np.nanmin(shown)), float(np.nanmax(shown))]
        dlg = ContourOptionsDialog(s, fields=[field], values=ends, parent=self)
        dlg.chk_auto.setToolTip(tr("Left on, the range is the one chosen in the window: "
                                   "this stage or all stages, from the least to the "
                                   "greatest value."))
        return dlg

    def apply_contour_settings(self, s: ContourSettings) -> None:
        """What the Contour Options dialog gave: the settings of the
        quantity; a range of its own (automatic off) is the custom range."""
        self.settings[self.quantity] = s
        if not s.auto_range:
            self.set_range(drawing.CUSTOM)
        elif self.range_mode == drawing.CUSTOM:
            self.set_range(drawing.AUTO_STAGE)
        self.redraw()

    def act_contour_options(self) -> None:
        dlg = self.contour_dialog()
        if dlg.exec():
            self.apply_contour_settings(dlg.settings)

    # ------------------------------------------------------------ drawing
    def factor(self, quantity: Optional[str] = None) -> float:
        """The units shown in one unit kept, of ``quantity``."""
        uq = UNIT_Q[qt.get(quantity or self.quantity).unit]
        return 1.0 if uq is None else units.to_user_value(self.session.model, 1.0, uq)

    def unit_text(self, quantity: Optional[str] = None) -> str:
        q = qt.get(quantity or self.quantity)
        uq = UNIT_Q[q.unit]
        if uq is not None:
            return units.label(self.session.model, uq)
        return "°" if q.unit == qt.ANGLE else tr("dimensionless")

    def redraw(self) -> Optional[str]:
        """Ask the field of the quantity in the stage shown, and draw it
        with its legend. The refusal's text, or None."""
        if not self.stages or self.stage_id is None:
            return None
        s = self.settings_of(self.quantity)
        f = self.factor()
        kw = {"quantity": self.quantity, "stage": self.stage_id, "absolute": self.absolute,
              "range_mode": self.range_mode, "allow_invalid": True, "as_arrays": True}
        if self.range_mode == drawing.CUSTOM:
            lo, hi = sorted((s.vmin / f, s.vmax / f))
            kw.update(low=lo, high=hi)
        try:
            got = self.session.call("results_field", **kw)
        except OgrApiError as err:
            return self._said(err)
        self.field = got
        lo, hi = (v * f for v in got["range"])
        if hi <= lo:                                     # a field of one value
            hi = lo + max(abs(lo) * 0.01, 1e-9)
        s.vmin, s.vmax = (min(lo, hi), max(lo, hi))
        key = (got["stage"], got["level"])
        if key not in self._merges:
            self._merges[key] = merging(got["xy"], got["triangles"], got["material"])
        drawn = draw(got["xy"], got["triangles"], got["values"] * f, got["material"], s,
                     self._merges[key])
        k = self.stage_tabs.currentIndex()
        self.view.set_model(self.session.model, k)
        self.view.show_field(drawn, s.opacity)
        self._legend(s)
        self.decided.setHtml(self.decided_html())
        return None

    def decided_parts(self) -> list[tuple[str, list[tuple[str, str]]]]:
        """What decided what is drawn (RF-20, rule 12), by part: the
        results (their state, who wrote them, the engine), the mesh (the
        bound B and what the mesher noted, the nodes the engine restrained
        on the axis), what decides the result as it was written with the
        results, and the drawing (its subdivision, its range, its bands)."""
        from ...report import info
        from ..info_window import said
        o = getattr(self, "opened_info", None) or {}
        m = self.session.model
        results = [(tr("State"), tr(STATE_WORD.get(self.state, self.state)))]
        if o.get("other_version"):
            results.append((tr("Written by"), o["other_version"]))
        results.append((tr("Engine"), str(o.get("engine", ""))))
        mesh_section, deciding_now = info.decided(m)
        mesh = [(said(a), said(b)) for a, b in mesh_section.rows]
        # the values written with the results; each said in the reader's
        # language when it is one this model also says (always, when valid)
        known = {str(what): what for what, _v in deciding_now.rows}
        whys = {}
        for _w, value in deciding_now.rows:
            for v in (getattr(value, "args", None) or {}).values():
                if isinstance(v, dict) and "text" in v:
                    whys[v["text"]] = v
        deciding = []
        for what, value, why in o.get("deciding", []):
            label = said(known[what]) if what in known else what
            w = whys.get(why)
            from ogr_core.messages import render
            from ...api.messages import FEM_MESSAGES
            why_text = render(FEM_MESSAGES, w["code"], w["args"], w["text"], translate=tr) \
                if w else why
            deciding.append((label, f"{value} ({why_text})"))
        s = self.settings_of(self.quantity)
        f = self.field or {}
        drawing = [(tr("Subdivision of each element"), str(f.get("level", ""))),
                   (tr("Range"), "%s: %s – %s %s" % (tr(dict(RANGES)[self.range_mode]),
                                                      s.format_value(s.vmin),
                                                      s.format_value(s.vmax), self.unit_text())),
                   (tr("Intervals"), str(s.intervals)),
                   (tr("Palette"), tr(s.palette))]
        return [(tr("The results"), results), (tr("The mesh"), mesh),
                (tr("What decides the result"), deciding), (tr("The drawing"), drawing)]

    def decided_html(self) -> str:
        import html
        out = []
        for title, rows in self.decided_parts():
            out.append(f"<h4>{html.escape(title)}</h4><table>")
            out += [f"<tr><td><b>{html.escape(str(a))}</b></td><td>{html.escape(str(b))}</td></tr>"
                    for a, b in rows]
            out.append("</table>")
        return "".join(out)

    def legend_lines(self) -> list[str]:
        """What the legend says of what is drawn (guide §6, RF-19)."""
        m = self.session.model
        q = qt.get(self.quantity)
        st = self.stages[self.stage_tabs.currentIndex()]
        lines = [f"{tr(q.name(m.analysis))} [{self.unit_text()}]"]
        if self.absolute:
            lines.append(tr("Absolute value"))
        lines.append(tr(CONVENTION_TEXT[q.convention]))
        lines.append(tr("Stage: %s") % (st["name"] or st["id"]))
        lines.append(tr(SOURCE_TEXT[q.kind]))
        lines.append(tr("Range: %s") % tr(dict(RANGES)[self.range_mode]))
        said = STATE_TEXT.get(self.state)
        if said:
            lines.insert(0, tr("NOT VALID: %s") % tr(self.state.capitalize()))
        return lines

    def _legend(self, s: ContourSettings) -> None:
        self.legend_text.setText("\n".join(self.legend_lines()))
        banded = s.mode in (ContourMode.FILLED, ContourMode.FILLED_LINES, ContourMode.LINES)
        self.legend.configure(s.vmin, s.vmax, s.colour_for, title="",
                              steps=s.intervals, decimals=s.decimals, scientific=s.scientific,
                              bands=s.band_colours() if banded else None,
                              labels=[s.format_value(v) for v in s.levels()] if banded else None)

    # ------------------------------------------------------------ the queries
    def pick(self, kind: str) -> None:
        """Pick on the canvas the points of a query (a line, a polyline, or
        the point of a history)."""
        self.picking = {"kind": kind, "points": []}
        self.statusBar().showMessage(tr(PICK_TEXT[kind]))

    def _clicked(self, x: float, y: float, button) -> None:
        p = self.picking
        if p is None:
            return
        if button == Qt.MouseButton.RightButton:
            if p["kind"] == "polyline" and len(p["points"]) >= 2:
                self._picked()
            return
        p["points"].append((x, y))
        if (p["kind"] == "line" and len(p["points"]) == 2) or p["kind"] == "history":
            self._picked()

    def _key(self, key) -> None:
        p = self.picking
        if p is None:
            return
        if key == Qt.Key.Key_Escape:
            self.picking = None
            self.statusBar().showMessage(tr("Query cancelled."), 5000)
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and len(p["points"]) >= 2:
            self._picked()

    def _picked(self) -> None:
        p, self.picking = self.picking, None
        self.statusBar().clearMessage()
        if p["kind"] == "history":
            self.query_history(*p["points"][0])
            return
        n = self.ask_points()
        if n is not None:
            self.query_line(p["points"], n or None)

    def ask_points(self) -> Optional[int]:
        """How many points along the line (0: at its vertices); None: cancelled."""
        n, ok = QInputDialog.getInt(self, tr("Query"), tr(
            "Points along it (0: at its vertices):"), 50, 0, 100000)
        return n if ok else None

    def _query(self, kind: str, **args):
        """``results_query`` of the quantity in the stage shown, and its
        window; or the refusal's text."""
        args = {"quantity": self.quantity, "kind": kind, **args}
        if kind != "history":
            args["stage"] = self.stage_id
        try:
            got = self.session.call("results_query", allow_invalid=True, **args)
        except OgrApiError as err:
            return self._said(err)
        from .queries import QueryWindow
        qw = QueryWindow(self, kind, args, got)
        self.query_windows.append(qw)
        qw.show()
        return qw

    def query_line(self, points, n: Optional[int] = None):
        """Along a line or a polyline: n points, or at its vertices."""
        out = self._query("line", points_xy=[list(map(float, p)) for p in points], n=n)
        if not isinstance(out, str):
            self.view.queries.append([tuple(p) for p in points])
            self.view.show_field(self.view.drawn, self.view.opacity)
        return out

    def query_boundary(self, boundary: str, n: Optional[int] = None, distance: float = 0.0,
                       side: Optional[str] = None):
        out = self._query("boundary", boundary=boundary, n=n, distance=distance, side=side)
        if not isinstance(out, str):
            self.view.queries.append([(r["x"], r["y"]) for r in out.got["rows"]])
            self.view.show_field(self.view.drawn, self.view.opacity)
        return out

    def query_nodes(self):
        return self._query("nodes")

    def query_history(self, x: float, y: float):
        return self._query("history", x=float(x), y=float(y))

    def boundary_dialog(self):
        from .queries import BoundaryQueryDialog
        return BoundaryQueryDialog(self.session.model, self)

    def act_query_boundary(self) -> None:
        dlg = self.boundary_dialog()
        if dlg.exec():
            self.query_boundary(**dlg.query())

    def act_query_nodes(self) -> None:
        self.query_nodes()

    def act_query_clear(self) -> None:
        self.view.queries = []
        self.view.show_field(self.view.drawn, self.view.opacity)

    # ------------------------------------------------------------ the cursor
    def value_at(self, x: float, y: float) -> str:
        """The value at (x, y) in the stage shown, as the status bar says
        it; the query's, interpolated exactly (D11)."""
        if not self.stages:
            return ""
        try:
            got = self.session.call("results_query", quantity=self.quantity, kind="at",
                                    stage=self.stage_id, x=x, y=y, allow_invalid=True)
        except OgrApiError as err:
            return fem_i18n.say(getattr(err, "message", str(err)))
        m = self.session.model
        f = self.factor()
        q = qt.get(self.quantity)
        name = tr(q.name(m.analysis))
        out = []
        for row in got["rows"]:
            if row["value"] is None:
                out.append(f"{name}: " + tr(REASON_TEXT.get(row["reason"], row["reason"])))
                continue
            v = abs(row["value"]) if self.absolute else row["value"]
            text = f"{name} = {v * f:.4g} {self.unit_text()}"
            if row["material"] is not None and q.kind != qt.DISPLACEMENT:
                mat = m.materials[row["material"]]
                text += " (" + tr("material %s") % (mat.name or mat.id) + ")"
            out.append(text)
        ux, uy = units.to_user(m, (x, y))
        return f"x = {ux:.4g}, y = {uy:.4g} {units.length_label(m)}: " + "; ".join(out)

    def show_value(self, x: float, y: float) -> None:
        self.value_label.setText(self.value_at(x, y))

    def _said(self, err) -> str:
        text = fem_i18n.say(getattr(err, "message", str(err)))
        hint = getattr(err, "hint", None)
        text += f" {fem_i18n.say(hint)}" if hint else ""
        self.statusBar().showMessage(text, 15000)
        return text
