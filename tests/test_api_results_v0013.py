# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.13 (spec 006, T14) — the operations on the results (RF-6; spec 005).

Invariants protected:

* **every query of spec 005 has its operation and gives its numbers bit for
  bit**: along a line, on a boundary at a distance, at every node, at every
  point, through the stages; the summary; the table (the same text); the
  report (the same text); the field ready to be drawn (the same arrays);
* **results that are not valid are read only when asked for**: stale after
  the model changes, missing before calculating; asked for, every answer
  says their state;
* **what is asked wrongly is refused by name**: a quantity, a stage, a kind
  of query or a boundary that does not exist.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

import _results
from ogr_core.api import NotConfigured, NotFound

from ogr_fem2d import api
from ogr_fem2d.model import ogr_file
from ogr_fem2d.report import info
from ogr_fem2d.results import calculate as calc
from ogr_fem2d.results import drawing, queries, table


def _refused(fn, kind, *words):
    try:
        fn()
    except kind as err:
        for w in words:
            assert w in str(err), (w, str(err))
        return err
    raise AssertionError(f"accepted; expected {kind.__name__}")


class _Calculated:
    """The loaded layers in two stages, shown in MPa, calculated, open in a workspace."""

    def __enter__(self):
        from ogr_fem2d.model import stages
        import _models
        from ogr_fem2d.model import edit
        self.m = edit.set_units(stages.set_load_factor(
            _models.with_stages(_results.loaded_layers(), 2), 0, "2", 2.0), "metric_mpa")
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "modelo.ogrfem2d"
        ogr_file.write(self.m, self.path)
        calc.calculate(self.m, self.path)
        self.ws = api.workspace(workdir=self.dir.name)
        self.pid = api.call(self.ws, "project_open", path="modelo.ogrfem2d")["project_id"]
        self.r = calc.open_results(self.path, self.m).results
        return self

    def call(self, name, /, **kw):
        return api.call(self.ws, name, project_id=self.pid, **kw)

    def __exit__(self, *exc):
        self.ws.shutdown()
        self.dir.cleanup()


def _values(q):
    return [r["value"] for r in q["rows"]]


class TestTheNumbersOfSpec005:
    def test_every_query(self):
        with _Calculated() as c:
            view = queries.View(c.r, 1)
            line = [[2.0, 0.0], [2.0, -10.0]]
            got = c.call("results_query", quantity="sigma_1", kind="line", points_xy=line, n=11)
            assert _values(got) == queries.line(view, "sigma_1", line, 11).values()
            assert (got["state"], got["stage"], got["unit"]) == (calc.VALID, "2", "pressure")
            got = c.call("results_query", quantity="u_y", kind="boundary", boundary="ext",
                         n=3, distance=0.5, side="inside", stage="1")
            assert _values(got) == queries.on_boundary(queries.View(c.r, 0), "u_y", c.m, "ext", 3,
                                                       0.5, "inside").values()
            for kind, fn in (("nodes", queries.all_nodes), ("points", queries.all_points)):
                got = c.call("results_query", quantity="sigma_xx", kind=kind)
                assert _values(got) == fn(view, "sigma_xx").values(), kind
            h = c.call("results_query", quantity="sigma_yy", kind="history", x=10.0, y=-5.0)
            direct = queries.history(c.r, "sigma_yy", 10.0, -5.0)
            assert [s["rows"][0]["value"] for s in h["stages"]] == \
                [s.rows[0].value for s in direct.stages]

    def test_summary_table_report_field(self):
        with _Calculated() as c:
            view = queries.View(c.r, 1)
            s = c.call("results_summary", quantities=["sigma_1"])
            d = queries.summary(view, c.m, ["sigma_1"])
            assert s["reactions"] == list(d.reactions)
            assert [e["max"] for e in s["extremes"]] == [e.maximum for e in d.extremes]
            assert s["reactions_by_boundary"] == [[b, x, y] for b, x, y in d.reactions_by_boundary]
            got = c.call("results_table", path="eje", quantity="sigma_1", kind="line",
                         points_xy=[[2, 0], [2, -10]], n=5)
            text = Path(got["path"]).read_text(encoding="utf-8")
            assert text == table.to_csv(queries.line(view, "sigma_1", [[2, 0], [2, -10]], 5),
                                        units=c.m.units, analysis=c.m.analysis,
                                        fingerprint=c.r.header.model_fingerprint)
            rep = c.call("results_report")["report"]
            assert rep == info.to_text(info.report(c.m, calc.open_results(c.path, c.m)))
            f = c.call("results_field", quantity="sigma_1", as_arrays=True)
            direct = drawing.field(view, "sigma_1")
            assert np.array_equal(f["values"], direct.values) and np.array_equal(f["xy"], direct.xy)
            assert f["range"] == list(drawing.value_range(view, "sigma_1"))
            listed = c.call("results_field", quantity="sigma_1", level=0)
            assert listed["values"] == drawing.field(view, "sigma_1", 0).values.tolist()


class TestNotValid:
    def test_read_only_when_asked(self):
        with _Calculated() as c:
            assert c.call("results_open")["state"] == calc.VALID
            assert c.call("results_query", quantity="u", kind="nodes")["state"] == calc.VALID
            c.call("material_set", material="top", E=4.0e4)
            c.call("project_save")
            assert c.call("results_open")["state"] == calc.STALE
            _refused(lambda: c.call("results_query", quantity="sigma_1", kind="nodes"),
                     NotConfigured, "stale")
            got = c.call("results_query", quantity="sigma_1", kind="nodes", allow_invalid=True)
            assert got["state"] == calc.STALE
            s = c.call("results_summary", allow_invalid=True)
            assert s["state"] == calc.STALE and s["reactions_by_boundary"] == []
        with tempfile.TemporaryDirectory() as d:
            ogr_file.write(_results.loaded_layers(), Path(d) / "m.ogrfem2d")
            ws = api.workspace(workdir=d)
            pid = api.call(ws, "project_open", path="m.ogrfem2d")["project_id"]
            assert api.call(ws, "results_open", project_id=pid)["state"] == calc.MISSING
            _refused(lambda: api.call(ws, "results_query", project_id=pid, quantity="u",
                                      kind="nodes", allow_invalid=True), NotConfigured, "missing")
            ws.shutdown()


class TestRefused:
    def test_by_name(self):
        with _Calculated() as c:
            _refused(lambda: c.call("results_query", quantity="sigma_9", kind="nodes"), NotFound,
                     "'sigma_9'", "sigma_1")
            _refused(lambda: c.call("results_query", quantity="u", kind="grid"), NotFound, "'grid'")
            _refused(lambda: c.call("results_query", quantity="u", kind="nodes", stage="7"),
                     NotFound, "'7'")
            _refused(lambda: c.call("results_query", quantity="u", kind="boundary",
                                    boundary="tunel"), NotFound, "'tunel'", "ext")
