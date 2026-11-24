# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.13 (spec 006, T18) — rules 7 and 12 on what part B adds: every option
of an operation moves what it says it moves, and what decided a result goes
with it.

The options of the operations that the tests of T11 to T17 do not already
move (the changelog has the table of all of them):

* ``boundary_add(cut=...)``: with the cuts the boundaries share vertices and
  the model is valid; without them they cross;
* ``analysis_run(variant=...)``: the compiled engine gives the reference's
  numbers to rounding (spec 001, the identity of variants), and the results
  file says which engine wrote it (rule 12), as does the report;
* ``results_field(level=..., absolute=..., range_mode=...)``: more
  triangles, the absolute values, the range of every stage;
* the settings of a query and the engine of a calculation come back with
  their answer (rule 12).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

import _models
import _results
from ogr_fem2d import api
from ogr_fem2d.api.workspace import Held
from ogr_fem2d.model import model as md
from ogr_fem2d.model import ogr_file
from ogr_fem2d.model import stages
from ogr_fem2d.results import calculate as calc


class _Saved:
    def __init__(self, m):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "modelo.ogrfem2d"
        ogr_file.write(m, self.path)
        self.ws = api.workspace(workdir=self.dir.name)
        self.pid = api.call(self.ws, "project_open", path="modelo.ogrfem2d")["project_id"]

    def call(self, name, /, **kw):
        return api.call(self.ws, name, project_id=self.pid, **kw)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.ws.shutdown()
        self.dir.cleanup()


class TestRule7:
    def test_cut(self):
        for cut, rules in ((True, set()), (False, {"crossing"})):
            ws = api.workspace()
            pid = ws.add(Held(_models.layers())).id
            api.call(ws, "boundary_add", project_id=pid, type="stage",
                     points_xy=[[5.0, 0.0], [5.0, -10.0]], cut=cut)
            m = ws.get(pid).project.model
            got = {p.rule for p in md.problems(m)} - {"region_unassigned"}
            assert got == rules, (cut, got)

    def test_variant(self):
        with _Saved(_results.loaded_layers()) as c:
            c.call("analysis_run", wait=120)
            ref = calc.open_results(c.path).results
            ref_u = ref.field(0, "displacement").copy()
            c.call("analysis_run", variant="rust", wait=120)
            rust = calc.open_results(c.path).results
            assert (ref.header.engine_variant, rust.header.engine_variant) == ("reference", "rust")
            u = rust.field(0, "displacement")
            assert np.allclose(u, ref_u, rtol=1e-10, atol=1e-14 * np.abs(ref_u).max())
            assert c.call("results_open")["engine"] == "rust"
            assert "Engine" in c.call("results_report")["report"]

    def test_field_options(self):
        two = stages.set_load_factor(_models.with_stages(_results.loaded_layers(), 2), 0, "2", 0.0)
        with _Saved(two) as c:
            c.call("analysis_run", wait=120)
            f0 = c.call("results_field", quantity="u_y", level=0, as_arrays=True)
            f2 = c.call("results_field", quantity="u_y", level=2, as_arrays=True)
            assert len(f2["triangles"]) == 16 * len(f0["triangles"])
            ab = c.call("results_field", quantity="u_y", level=0, absolute=True, as_arrays=True)
            assert np.array_equal(ab["values"], np.abs(f0["values"]))
            stage_range = c.call("results_field", quantity="sigma_1", level=0)["range"]
            all_range = c.call("results_field", quantity="sigma_1", level=0,
                               range_mode="auto_all")["range"]
            assert all_range != stage_range and all_range[1] > stage_range[1]


class TestRule12:
    def test_what_decided_it_goes_with_it(self):
        with _Saved(_results.loaded_layers()) as c:
            run = c.call("analysis_run", wait=120)
            assert run["provenance"]["program"].startswith("OGR FEM2D")
            q = c.call("results_query", quantity="sigma_1", kind="boundary", boundary="ext",
                       n=2, distance=0.5, side="inside")
            assert dict(q["settings"]) == {"boundary": "ext", "points": "2 per segment",
                                           "distance": 0.5, "side": "inside"}
            assert (q["unit"], q["convention"]) == ("pressure", "compression positive")
