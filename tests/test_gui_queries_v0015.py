# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.15 (spec 006, T32) — the queries of the interpretation: a line, a
polyline, a boundary (on it, or at a distance to one side), every node and
a point through the stages, with their chart and their table (RF-19,
RF-20; spec 005, RF-11 to RF-15).

Invariants protected:

* **each query gives its operation's numbers**: the rows of the window are
  ``results_query``'s, in the units shown;
* **the chart is of those rows** (against the distance along the query, or
  against the stage), and **the table is ``results_table``'s**, byte for
  byte;
* **each option moves the number**: the points along a line, the points on
  a boundary's segments, the distance and the side, the stage, the unit
  system shown;
* what decided the rows is said with them (the stage, the method, the
  settings: rule 12);
* a polyline is picked on the canvas and drawn there; Esc cancels.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import _results  # noqa: E402
from _settings import recent_kept  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402
from ogr_fem2d.model import ogr_file  # noqa: E402
from ogr_fem2d.results import calculate as calc  # noqa: E402

APP = QApplication.instance() or QApplication([])
LINE = [(1.5, 0.0), (9.5, 0.0)]


class _Open:
    def __init__(self, m):
        self.m = m

    def __enter__(self):
        self._recent = recent_kept()
        self._recent.__enter__()
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "modelo.ogrfem2d"
        ogr_file.write(self.m, self.path)
        calc.calculate(self.m, self.path)
        self.w = MainWindow()
        self.w.open_path(str(self.path))
        self.w.interpret()
        self.win = self.w.interpret_window
        return self

    def op(self, **kw):
        return self.w.session.call("results_query", allow_invalid=True, **kw)

    def __exit__(self, *exc):
        self.w.confirm_discard = lambda: True
        self.w.close()
        self.dir.cleanup()
        self._recent.__exit__(*exc)


def _three():
    return _results.excavated_tunnel(3)


def _values(qw):
    return [r["value"] for r in qw.rows()]


class TestTheNumbersAreTheOperations:
    def test_a_line_and_its_points(self):
        with _Open(_three()) as o:
            qw = o.win.query_line(LINE, 20)
            want = o.op(quantity="sigma_1", kind="line", points_xy=[list(p) for p in LINE],
                        n=20, stage=o.win.stage_id)
            assert _values(qw) == [r["value"] for r in want["rows"]]
            assert [r["distance"] for r in qw.rows()] == [r["distance"] for r in want["rows"]]
            assert len(qw.rows()) == 20 and qw.table.rowCount() == 20
            assert len(o.win.query_line(LINE, 7).rows()) == 7            # n moves it
            assert len(o.win.query_line(LINE).rows()) == 2               # at the vertices
            o.win.set_stage(0)                       # before the excavation
            other = o.win.query_line(LINE, 20)
            assert _values(other) != _values(qw)                         # the stage moves it
            lines = qw.header_lines()
            assert lines[0] == "Sigma 1 (in plane) [kPa]" and "Points: 20" in lines
            assert any(x.startswith("Superconvergent patch recovery") for x in lines)

    def test_a_boundary_its_points_its_distance_and_side(self):
        with _Open(_three()) as o:
            on = o.win.query_boundary("hole", 4)
            want = o.op(quantity="sigma_1", kind="boundary", boundary="hole", n=4,
                        stage=o.win.stage_id)
            assert _values(on) == [r["value"] for r in want["rows"]]
            assert len(on.rows()) == 16
            assert len(o.win.query_boundary("hole").rows()) == 4         # its vertices
            out = o.win.query_boundary("hole", 4, 0.5, "outside")
            assert _values(out) != _values(on)
            assert [r["x"] for r in out.rows()] != [r["x"] for r in on.rows()]
            inside = o.win.query_boundary("hole", 4, 0.5, "inside")
            assert {r["from"] for r in inside.rows()} == {"in an excavated region"}
            assert "Side: outside" in out.header_lines() and "Distance: 0.5 m" in \
                out.header_lines()

    def test_every_node_and_a_point_through_the_stages(self):
        with _Open(_three()) as o:
            nodes = o.win.query_nodes()
            want = o.op(quantity="sigma_1", kind="nodes", stage=o.win.stage_id)
            assert _values(nodes) == [r["value"] for r in want["rows"]]
            assert not nodes.btn_chart.isEnabled() and nodes.btn_chart.toolTip()
            h = o.win.query_history(5.0, 0.0)
            want = o.op(quantity="sigma_1", kind="history", x=5.0, y=0.0)
            assert _values(h) == [s["rows"][0]["value"] for s in want["stages"]]
            assert [r["index"] for r in h.rows()] == [1, 2, 3]
            (_label, xs, ys), = h.series()
            assert xs == [1, 2, 3] and ys == _values(h)

    def test_the_units_shown(self):
        with _Open(_three()) as o:
            kpa = o.win.query_line(LINE, 5)
            o.w.session.call("project_settings", units="imperial_ksf")
            o.w.session.call("project_save")
            o.win.open()
            ksf = o.win.query_line(LINE, 5)
            ratio = [a / b for a, b in zip(_values(kpa), _values(ksf)) if b]
            assert ratio and all(abs(r - ratio[0]) < 1e-9 * abs(ratio[0]) for r in ratio)
            assert abs(ratio[0] - 47.880258980) < 1e-3                  # kPa in one ksf
            assert abs(ksf.rows()[-1]["distance"] - 8.0 / 0.3048) < 1e-9   # in feet


class TestTheChartAndTheTable:
    def test_the_chart_is_of_the_rows(self):
        with _Open(_three()) as o:
            qw = o.win.query_line(LINE, 10)
            (label, xs, ys), = qw.series()
            assert xs == [r["distance"] for r in qw.rows()] and ys == _values(qw)
            dlg = qw.chart()
            assert dlg is not None and not dlg.isHidden()
            dlg.close()

    def test_the_table_is_the_operations(self):
        with _Open(_three()) as o:
            qw = o.win.query_boundary("hole", 3, 0.25, "outside")
            mine = Path(o.dir.name) / "consulta.csv"
            theirs = Path(o.dir.name) / "operacion.csv"
            assert qw.export(str(mine)) is None
            o.w.session.call("results_table", path=str(theirs), quantity="sigma_1",
                             kind="boundary", boundary="hole", n=3, distance=0.25,
                             side="outside", stage=o.win.stage_id)
            assert mine.read_bytes() == theirs.read_bytes() and len(mine.read_bytes()) > 100


class TestOnTheCanvas:
    def test_a_polyline_picked_drawn_and_cancelled(self):
        with _Open(_three()) as o:
            win = o.win
            win.ask_points = lambda: 0
            win.pick("polyline")
            for p in ((2.0, 0.0), (5.0, 3.0), (8.0, 0.0)):
                win._clicked(*p, Qt.MouseButton.LeftButton)
            assert not win.query_windows
            win._clicked(0.0, 0.0, Qt.MouseButton.RightButton)
            qw = win.query_windows[-1]
            assert len(qw.rows()) == 3 and win.picking is None          # at its vertices
            assert len(win.view.query_items) == 1
            win.pick("line")
            win._clicked(2.0, 0.0, Qt.MouseButton.LeftButton)
            win._key(Qt.Key.Key_Escape)
            assert win.picking is None and len(win.query_windows) == 1
            win.pick("line")                                    # two clicks make a line
            win._clicked(2.0, 0.0, Qt.MouseButton.LeftButton)
            win._clicked(8.0, 0.0, Qt.MouseButton.LeftButton)
            assert win.picking is None and len(win.query_windows) == 2
            assert len(win.view.query_items) == 2
            win.act_query_clear()
            assert win.view.query_items == []

    def test_the_boundary_dialog(self):
        with _Open(_three()) as o:
            dlg = o.win.boundary_dialog()
            dlg.boundary.setCurrentIndex(dlg.boundary.findData("hole"))
            assert not dlg.side.isEnabled()
            assert dlg.query() == {"boundary": "hole", "n": None, "distance": 0.0, "side": None}
            dlg.points.setValue(5)
            dlg.distance.box.setValue(0.75)
            assert dlg.side.isEnabled()
            dlg.side.setCurrentIndex(dlg.side.findData("outside"))
            assert dlg.query() == {"boundary": "hole", "n": 5, "distance": 0.75,
                                   "side": "outside"}


class TestInSpanish:
    def test_the_tables(self):
        from ogr_ui import i18n as ui_i18n
        from ogr_ui.testing import texts
        from ogr_fem2d.gui import i18n as fem_i18n
        from ogr_fem2d.gui.interpret import queries as iq
        from ogr_fem2d.gui.interpret import window as iw
        table = {**ui_i18n.package_translations("es"), **fem_i18n.spanish()}
        english = list(iq.KIND_TEXT.values()) + list(iq.VALUE_TEXT.values())
        english += [v for k, v in iq.SETTING_TEXT.items() if k not in ("x", "y")]
        english += [v for v in iq.SOURCE_TEXT.values() if v] + list(iq.REASON_TEXT.values())
        english += list(iq.METHOD_TEXT.values()) + list(iw.PICK_TEXT.values())
        english += [t for _k, t in iq.SIDES_CLOSED + iq.SIDES_OPEN]
        assert texts.missing_translations(english, table) == []
        from ogr_fem2d.results import queries
        assert set(iq.METHOD_TEXT) == {queries.method_of(q) for q in ("u_x", "sigma_1")}
