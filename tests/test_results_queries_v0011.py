# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.11 (spec 005, T9) — the queries along a line, at every node and at
every integration point (RF-11, RF-13; D9).

Invariants protected:

* **where the points are**: n points at equal distances along the whole of
  a polyline, both ends included, or its vertices, with the distance from
  the first;
* **a contact shows its jump** (D9): a point on the contact between two
  materials has one row per material for a stress, at the same distance,
  with different values; a displacement, continuous, one row;
* **no value is made up** (RF-10): a point outside the model and one in the
  excavation have their row with no value and the reason;
* **the values are the field's**: a displacement queried at a node is the
  nodal one (the finite-element field); a stress queried at a node is the
  recovered value there, and its quantity is that of the interpolated
  tensor;
* **every node and every point**: a displacement once per node; a stress
  once per node and material (two rows at the contact), none at a removed
  node; at the points, the engine's value, none at an excavated one.
"""
from __future__ import annotations

import tempfile

import numpy as np

import _results
from ogr_fem2d.model import conventions
from ogr_fem2d.results import quantities as qt
from ogr_fem2d.results import queries as qy
from ogr_fem2d.results import recovery as rc


class TestWhereThePointsAre:
    def test_n_points_and_the_vertices(self):
        points, d = qy.spread([(0.0, 0.0), (3.0, 4.0), (3.0, 9.0)], 5)
        assert d == [0.0, 2.5, 5.0, 7.5, 10.0] and points[-1] == (3.0, 9.0)
        assert np.allclose(points[1], (1.5, 2.0)) and np.allclose(points[3], (3.0, 6.5))
        points, d = qy.spread([(0.0, 0.0), (3.0, 4.0), (3.0, 9.0)], None)
        assert points == [(0.0, 0.0), (3.0, 4.0), (3.0, 9.0)] and d == [0.0, 5.0, 10.0]

    def test_a_bad_line_is_said(self):
        for vertices, n in (([(0.0, 0.0)], 3), ([(0.0, 0.0), (0.0, 0.0)], 3), ([(0, 0), (1, 1)], 1)):
            try:
                qy.spread(vertices, n)
            except ValueError:
                pass
            else:
                raise AssertionError((vertices, n))


class TestTheLine:
    def test_a_contact_shows_its_jump(self):
        with tempfile.TemporaryDirectory() as d:
            view = qy.View(_results.calculated(_results.loaded_layers(), d), 0)
            q = qy.line(view, "sigma_xx", [(5.0, -1.0), (5.0, -7.0)], 7)
            on = [r for r in q.rows if r.point == 3]
            assert len(on) == 2 and {r.material for r in on} == {0, 1}
            assert on[0].distance == on[1].distance == 3.0 and abs(on[0].value - on[1].value) > 1.0
            assert len(q.rows) == 8 and all(r.value is not None for r in q.rows)
            u = qy.line(view, "u_y", [(5.0, -1.0), (5.0, -7.0)], 7)
            assert len(u.rows) == 7 and all(r.source == qy.FE for r in u.rows)

    def test_outside_and_excavated(self):
        with tempfile.TemporaryDirectory() as d:
            view = qy.View(_results.calculated(_results.loaded_layers(), d), 0)
            q = qy.line(view, "sigma_1", [(5.0, -9.0), (5.0, -11.0)], 3)
            assert [r.reason for r in q.rows] == ["", "", "outside"] and q.rows[2].value is None
        with tempfile.TemporaryDirectory() as d:
            view = qy.View(_results.calculated(_results.excavated_tunnel(), d), 0)
            q = qy.line(view, "u", [(0.0, 0.0), (3.0, 0.0)], 4)
            assert q.rows[0].reason == "excavated" and q.rows[0].value is None
            assert all(r.value is not None for r in q.rows[2:])

    def test_the_values_are_the_fields(self):
        with tempfile.TemporaryDirectory() as d:
            results = _results.calculated(_results.loaded_layers(), d)
            view = qy.View(results, 0)
            mesh = results.mesh()
            corners = np.unique(mesh.elements[:, :3])            # an interior corner node
            node = int(corners[np.argmin(np.hypot(*(mesh.nodes[corners] - (10.3, -7.2)).T))])
            x, y = mesh.nodes[node]
            u = qy.line(view, "u_x", [(x, y), (x + 0.01, y)], None).rows[0]
            nodal = results.field(0, "displacement")
            # the shape functions at a node are 1 and 0 to rounding
            assert np.isclose(u.value, nodal[node, 0], rtol=1e-12, atol=1e-12 * np.abs(nodal).max())
            s = qy.line(view, "sigma_1", [(x, y), (x + 0.01, y)], None).rows[0]
            rec = view.recovered(qt.STRESS)
            e, a = s.element, list(mesh.elements[s.element]).index(node)
            assert np.isclose(s.value, qt.stress_quantity("sigma_1", rec.values[e, a]), rtol=1e-12)
            assert s.source == "spr"


class TestEveryNodeAndPoint:
    def test_every_node(self):
        with tempfile.TemporaryDirectory() as d:
            results = _results.calculated(_results.loaded_layers(), d)
            view = qy.View(results, 0)
            mesh = results.mesh()
            u = qy.all_nodes(view, "u")
            assert len(u.rows) == len(mesh.nodes)
            s = qy.all_nodes(view, "sigma_xx")
            contact = {i for i, (_x, y) in enumerate(mesh.nodes) if y == -4.0}
            twice = {r.point for r in s.rows if sum(1 for q in s.rows if q.point == r.point) == 2}
            assert twice == contact and len(s.rows) == len(mesh.nodes) + len(contact)
        with tempfile.TemporaryDirectory() as d:
            results = _results.calculated(_results.excavated_tunnel(), d)
            s = qy.all_nodes(qy.View(results, 0), "q")
            removed = set(results.field(0, "removed_nodes").tolist())
            assert removed and {r.point for r in s.rows if r.reason == "removed"} == removed

    def test_every_point_is_the_engines(self):
        with tempfile.TemporaryDirectory() as d:
            results = _results.calculated(_results.excavated_tunnel(), d)
            q = qy.all_points(qy.View(results, 0), "sigma_1")
            engine = results.field(0, "stress")
            want = qt.stress_quantity("sigma_1", conventions.user_stress(engine))
            for r in q.rows:
                if r.value is None:
                    assert r.reason == "excavated" and np.isnan(engine[r.point]).all()
                else:
                    assert r.value == float(want[r.point]) and r.source == qy.POINT
            try:
                qy.all_points(qy.View(results, 0), "u")
            except ValueError:
                pass
            else:
                raise AssertionError("a displacement at the points")
