# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.11 (spec 005, T11) — a quantity through the stages, and the summary of
a stage (RF-15; D14).

Invariants protected:

* **through the stages**: a point gives one value per stage, with whether
  the stage was solved; a point of the hole has a value while the hole is
  there and none once it is excavated;
* **the extremes say where and of what kind**: the greatest and the least of
  a quantity at the points are those of every point, at their place; at the
  nodes, those of the recovered values;
* **equilibrium** (spec 002, RF-5): in plane strain the internal forces add
  up to zero, so the reactions add up to minus the external forces of the
  stage, the load and the weight: for two strata of 20 m under 100 kPa,
  2000 + 18 x 4 x 20 + 24 x 6 x 20 = 6320 kN/m upwards;
* **the reactions by boundary add up to the total**: a node on two
  boundaries counts once, for the first of the model.
"""
from __future__ import annotations

import tempfile

import numpy as np

import _results
from ogr_fem2d.engine import analysis
from ogr_fem2d.model import translate
from ogr_fem2d.results import queries as qy


class TestThroughTheStages:
    def test_a_point_of_the_hole(self):
        m = _results.excavated_tunnel(3)
        with tempfile.TemporaryDirectory() as d:
            h = qy.history(_results.calculated(m, d), "sigma_xx", 0.2, 0.1)
            assert [s.stage_id for s in h.stages] == ["1", "2", "3"]
            assert [s.solved for s in h.stages] == [False, True, False]
            assert h.stages[0].rows[0].value is not None
            assert [s.rows[0].reason for s in h.stages[1:]] == ["excavated", "excavated"]
            far = qy.history(_results.calculated(m, d), "u", 3.0, 0.5)
            values = [s.rows[0].value for s in far.stages]
            assert values[0] == 0.0 and values[1] > 0.0 and values[2] == values[1]


class TestTheSummary:
    def test_the_extremes_say_where(self):
        with tempfile.TemporaryDirectory() as d:
            view = qy.View(_results.calculated(_results.loaded_layers(), d), 0)
            s = qy.summary(view, quantities=["sigma_1", "u"])
            points = qy.all_points(view, "sigma_1").rows
            best = max(points, key=lambda r: r.value)
            got = next(e for e in s.extremes if e.quantity == "sigma_1" and e.at == "points")
            assert got.maximum == best.value and got.max_where == (best.x, best.y)
            assert any(e.quantity == "sigma_1" and e.at == "nodes" for e in s.extremes)
            u = next(e for e in s.extremes if e.quantity == "u")
            assert u.at == "nodes" and u.maximum == s.max_displacement

    def test_equilibrium_and_the_boundaries(self):
        m = _results.loaded_layers()
        with tempfile.TemporaryDirectory() as d:
            view = qy.View(_results.calculated(m, d), 0)
            s = qy.summary(view, m, quantities=[])
            f = analysis.stage_load(translate.to_engine(m), 0)
            assert np.isclose(s.reactions[0], -f[0::2].sum(), atol=1e-6)
            assert np.isclose(s.reactions[1], -f[1::2].sum(), rtol=1e-12)
            assert np.isclose(s.reactions[1], 2000.0 + 18.0 * 4 * 20 + 24.0 * 6 * 20, rtol=1e-9)
            assert [b for b, _x, _y in s.reactions_by_boundary] == ["ext"]
            assert np.isclose(sum(y for _b, _x, y in s.reactions_by_boundary), s.reactions[1],
                              rtol=1e-14)
            owner = qy.boundary_of_nodes(m)
            ends = [n for n, (x, y) in enumerate(view.mesh.nodes) if y == -4.0 and x in (0.0, 20.0)]
            assert ends and all(owner[n] == "ext" for n in ends)
