# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.11 (spec 005, T10) — the query on a boundary of the model, or at a
distance from it (RF-12; D12).

Invariants protected:

* **on the geometry, arcs included**: the points of a query on the circle of
  a tunnel are on the circle, at the arc length from its first vertex;
* **at a distance**: inside and outside a circle give the concentric
  circles; inside a hole that is excavated there is no value, outside there
  is; outside the external boundary, no value either;
* **the side of an open boundary and its vertex**: left and right of its
  direction; at a corner, along the bisector of the two normals (an own
  rule, D12);
* **the signed area** of a closed boundary with arcs, which says which side
  is inside, is that of the region (a circle of four arcs: pi r^2);
* **the default is on the boundary**, and a distance asks for its side.
"""
from __future__ import annotations

import math
import tempfile

import numpy as np

import _results
from ogr_fem2d.model import model as md
from ogr_fem2d.results import queries as qy


class TestTheGeometry:
    def test_on_the_circle(self):
        hole = _results.excavated_tunnel().boundary("hole")
        points, d = qy.boundary_points(hole, 3)
        assert len(points) == 12
        assert np.allclose([math.hypot(x, y) for x, y in points], 1.0, rtol=0, atol=1e-15)
        assert np.allclose(d, [k * math.pi / 6.0 for k in range(12)], rtol=1e-14)
        assert math.isclose(qy.signed_area(hole), math.pi, rel_tol=1e-14)

    def test_inside_and_outside_a_circle(self):
        hole = _results.excavated_tunnel().boundary("hole")
        for side, r in ((qy.INSIDE, 0.9), (qy.OUTSIDE, 1.1)):
            points, _ = qy.boundary_points(hole, 2, 0.1, side)
            assert np.allclose([math.hypot(x, y) for x, y in points], r, atol=1e-14), side
        clockwise = md.Boundary("h", md.EXCAVATION, hole.vertices[::-1], True,
                                tuple(md.SegmentAttr(k, (0.0, 0.0)) for k in range(4)))
        assert math.isclose(qy.signed_area(clockwise), -math.pi, rel_tol=1e-14)
        points, _ = qy.boundary_points(clockwise, 2, 0.1, qy.INSIDE)
        assert np.allclose([math.hypot(x, y) for x, y in points], 0.9, atol=1e-14)

    def test_the_side_and_the_corner_of_an_open_boundary(self):
        b = md.Boundary("c", md.MATERIAL, ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0)), False)
        points, d = qy.boundary_points(b, None, 0.2, qy.LEFT)
        s = 0.2 / math.sqrt(2.0)
        assert np.allclose(points, [(0.0, 0.2), (1.0 - s, s), (0.8, 1.0)], atol=1e-15)
        assert d == [0.0, 1.0, 2.0]
        points, _ = qy.boundary_points(b, None, 0.2, qy.RIGHT)
        assert np.allclose(points, [(0.0, -0.2), (1.0 + s, -s), (1.2, 1.0)], atol=1e-15)

    def test_the_default_and_the_side_asked_for(self):
        hole = _results.excavated_tunnel().boundary("hole")
        assert qy.boundary_points(hole)[0] == list(hole.vertices)
        for side in (None, qy.LEFT):
            try:
                qy.boundary_points(hole, 2, 0.1, side)
            except ValueError:
                pass
            else:
                raise AssertionError(side)


class TestTheQuery:
    def test_inside_the_hole_nothing_outside_the_rock(self):
        m = _results.excavated_tunnel()
        with tempfile.TemporaryDirectory() as d:
            view = qy.View(_results.calculated(m, d), 0)
            inside = qy.on_boundary(view, "sigma_1", m, "hole", 2, 0.05, qy.INSIDE)
            assert all(r.value is None and r.reason == "excavated" for r in inside.rows)
            outside = qy.on_boundary(view, "sigma_1", m, "hole", 2, 0.05, qy.OUTSIDE)
            assert all(r.value is not None for r in outside.rows) and outside.what == "boundary"
            on = qy.on_boundary(view, "sigma_1", m, "hole")
            assert len(on.rows) == 4 and all(r.value is not None for r in on.rows)
            beyond = qy.on_boundary(view, "u", m, "ext", None, 0.5, qy.OUTSIDE)
            assert all(r.reason == "outside" for r in beyond.rows)
