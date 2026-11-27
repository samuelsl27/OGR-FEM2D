# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.15 (spec 006, T35; RF-22) — cases 005, 006 and 007 through the
interface: opened in the window, calculated with Compute (the calculation's
window), and interpreted: their queries (``comparaciones_consulta``) asked
in the interpretation's window, their charts, and the contours of their
quantities drawn.

Invariants protected:

* **the window's numbers are the operations'**: each query of the window
  gives, row for row and bit for bit, what ``results_query`` gives in a
  workspace of its own on the same results, and what the queries
  (``results.queries``) read from the ``.h5`` the window wrote;
* **they are the case's**: every row within the tolerance its esperado.json
  fixed before measuring, against its closed solution (Kirsch, Michell,
  Lamé: ``_query_references``), as spec 005 found them by the operations;
* **the chart is of those rows**, in the units shown (MPa: the cases are
  written in MPa);
* **the contours tell the closed solution**: where the closed form is the
  case's (near the hole, under the strip, near the cavity), the colour
  painted is the legend's colour of the closed solution's value, away
  from a level by more than the case's tolerance.
"""
from __future__ import annotations

import math
import os
import shutil
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

import _cases_model as cm  # noqa: E402
import _query_references as refs  # noqa: E402
from _settings import recent_kept  # noqa: E402
from ogr_fem2d import api  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402
from ogr_fem2d.model import ogr_file  # noqa: E402
from ogr_fem2d.results import calculate as calc  # noqa: E402
from ogr_fem2d.results import queries as qy  # noqa: E402

APP = QApplication.instance() or QApplication([])

# where the closed form is the case's, for the contours: (x, y) -> bool
REGION = {
    refs.C005: lambda x, y: 1.05 <= math.hypot(x, y) <= 5.0,
    refs.C006: lambda x, y: 0.0 <= x <= 5.0 and -5.0 <= y <= -0.25,
    refs.C007: lambda x, y: 1.05 <= math.hypot(x, y) <= 3.5,
}


def _args(query, quantity, stage):
    if query["tipo"] == "linea":
        return {"quantity": quantity, "stage": stage, "kind": "line",
                "points_xy": [list(query["desde"]), list(query["hasta"])], "n": query["n"]}
    return {"quantity": quantity, "stage": stage, "kind": "boundary",
            "boundary": query["contorno"], "n": query["n_por_segmento"],
            "distance": query["distancia"]}


def _asked(win, query):
    if query["tipo"] == "linea":
        return win.query_line([query["desde"], query["hasta"]], query["n"])
    return win.query_boundary(query["contorno"], query["n_por_segmento"], query["distancia"])


def _direct(view, m, query, quantity):
    if query["tipo"] == "linea":
        rows = qy.line(view, quantity, [query["desde"], query["hasta"]], query["n"]).rows
    else:
        rows = qy.on_boundary(view, quantity, m, query["contorno"], query["n_por_segmento"],
                              query["distancia"]).rows
    return [(r.x, r.y, r.distance, r.value) for r in rows]


def _of(rows):
    return [(r["x"], r["y"], r["distance"], r["value"]) for r in rows]


def _contours_tell_the_closed_form(name, win, quantity, tolerance, exact, scale):
    """The colour painted at the centres of the field's triangles in the
    case's region is that of the closed form's value; how many were seen."""
    win.set_quantity(quantity)
    s = win.settings_of(quantity)
    item = win.view.result_item
    f = win.factor()
    margin = tolerance * scale * f
    xy, tris = win.field["xy"], win.field["triangles"]
    inside = [t for t in range(len(tris)) if REGION[name](*xy[tris[t]].mean(axis=0))]
    assert inside, (name, quantity)
    checked = 0
    for t in inside[::max(1, len(inside) // 600)]:
        cx, cy = xy[tris[t]].mean(axis=0)
        v = exact(quantity, cx, cy) * f
        if min(abs(v - lv) for lv in s.levels()) <= margin:
            continue                                  # within the tolerance of a band's edge
        assert item.colour_at(cx, cy) == s.colour_for(v), (name, quantity, cx, cy, v)
        checked += 1
    return checked


def _through_the_window(name):
    """The case opened, calculated and interpreted in the window: how many
    centres each quantity's contours were checked at, and the worst error
    of each query."""
    spec = cm.case(name)["comparaciones_consulta"]
    exact, scales = refs.EXACT[name]()
    error = refs.errors(name)
    keep = refs.KEEP.get(name, lambda query, x, y: True)
    with recent_kept(), tempfile.TemporaryDirectory() as d:
        path = Path(d) / "modelo.ogrfem2d"
        shutil.copy(cm.path(name), path)
        w = MainWindow()
        ws = None
        try:
            w.open_path(str(path))
            w.actions_by_key["compute"].trigger()                    # Analysis > Compute
            w.compute_window.wait()
            job = w.session.ws.jobs.get(w.compute_window.followed)
            assert job.status()["state"] == "done", (name, job.status())
            assert calc.open_results(path).status == calc.VALID
            w.actions_by_key["interpret"].trigger()                  # Analysis > Interpret
            win = w.interpret_window
            assert not win.isHidden() and win.stages
            win.set_stage(spec["fase"])
            stage = win.stage_id

            ws = api.workspace(workdir=Path(d))                      # the operations, apart
            pid = api.call(ws, "project_open", path="modelo.ogrfem2d")["project_id"]
            assert api.call(ws, "results_open", project_id=pid)["stages"][spec["fase"]]["id"] \
                == stage
            m = ogr_file.read(path)
            view = qy.View(calc.open_results(path).results, spec["fase"])
            compared, worsts = 0, {}
            for query in spec["consultas"]:
                for mq in query["magnitudes"]:
                    q = mq["magnitud"]
                    win.set_quantity(q)
                    qw = _asked(win, query)
                    assert not isinstance(qw, str), (name, q, qw)
                    ops = api.call(ws, "results_query", project_id=pid,
                                   **_args(query, q, stage))["rows"]
                    assert _of(qw.got["rows"]) == _of(ops), (name, query["tipo"], q)
                    assert _of(qw.got["rows"]) == _direct(view, m, query, q), (name, q)
                    rows = [r for r in qw.got["rows"] if keep(query, r["x"], r["y"])]
                    assert rows and all(r["value"] is not None for r in rows), (name, q)
                    worst = max(error(q, mq["unidad_tolerancia"], r["x"], r["y"], r["value"])
                                for r in rows)
                    assert worst <= mq["tolerancia_absoluta"], (name, query["tipo"], q, worst)
                    worsts[(query["tipo"], q)] = worst
                    # the chart: the rows shown, against the distance, in MPa or m
                    shown = [r for r in qw.rows() if r["value"] is not None]
                    (_label, xs, ys), = qw.series()
                    assert xs == [r["distance"] for r in shown]
                    assert ys == [r["value"] for r in shown]
                    assert ys == [r["value"] * qw.factor for r in qw.got["rows"]
                                  if r["value"] is not None]
                    if q != "u":
                        assert qw.unit == "MPa" and qw.factor == 1.0e-3, (qw.unit, qw.factor)
                    compared += 1
            assert compared == sum(len(q["magnitudes"]) for q in spec["consultas"])
            assert len(win.view.queries) == compared                  # each drawn on the canvas

            seen = {}
            for query in spec["consultas"]:
                for mq in query["magnitudes"]:
                    q = mq["magnitud"]
                    if q in seen:
                        continue
                    seen[q] = _contours_tell_the_closed_form(
                        name, win, q, mq["tolerancia_absoluta"], exact,
                        scales[mq["unidad_tolerancia"]])
            assert all(n >= 100 for n in seen.values()), seen
            return seen, worsts
        finally:
            if ws is not None:
                ws.shutdown()
            w.confirm_discard = lambda: True
            w.confirm_stop_calculation = lambda: True
            w.close()


class TestTheCasesThroughTheWindow:
    def test_005_kirsch(self):
        assert set(_through_the_window(refs.C005)[0]) == {"sigma_1", "sigma_3", "u"}

    def test_006_the_strip(self):
        assert set(_through_the_window(refs.C006)[0]) == {"sigma_1", "sigma_3"}

    def test_007_the_cavity(self):
        assert set(_through_the_window(refs.C007)[0]) == {"sigma_1", "sigma_z", "sigma_3", "u"}
