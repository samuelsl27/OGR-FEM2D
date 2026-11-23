# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.8 (spec 003, T4b; D14 and D15) — every arc in pieces that turn at most
10 degrees.

Sources: Delaunay refinement with curved input assumes that the tangent of
every curve turns at most pi/3, "achieved by splitting curves in a
preprocessing step" (Pav and Walkington, Delaunay refinement by corner
lopping, def. 4, p. 4, after Boivin and Ollivier-Gooch 2002), and it is
proved to terminate only for an angle bound that depends on that turn
(corollary 3, p. 13): with pieces of 10 degrees, for B > 1.76. The owner
chose 10 degrees on 2026-11-23 (D15; it was 60 under D14).

Invariants protected:

* **no piece of an arc turns more than 10 degrees**, whatever the mesh asks
  for: an arc that takes no graded nodes, the excavation with the fewest
  nodes allowed, a uniform size larger than the arc, an arc of 127 degrees;
  the turn measured as the angle between consecutive nodes seen from the
  centre, not with the code's own function;
* **the edges**: an arc of exactly 10 degrees is one piece, even written with
  coordinates rounded so that its angle comes out a hair above (rounding does
  not add one); 10.1 degrees is two, a quarter circle nine, 179 degrees
  eighteen, 20 two and 20.1 three;
* **what is refused**: forced divisions below the minimum (the rule
  "divisions", saying 10 degrees), and graded nodes below the sum of the
  minimums (the rule "graded_nodes"); the minimum itself is accepted;
* **the share keeps the minimums** and still adds up exactly.
"""
from __future__ import annotations

import math
from dataclasses import replace

from ogr_fem2d.mesh import discretize as d
from ogr_fem2d.mesh import geometry as g
from test_mesh_input_v008 import CAVITY, DENT, TUNNEL

TEN = math.radians(10.0)


def _turns(disc):
    """The angle, seen from the centre, of every piece of every arc."""
    out = []
    for ds in disc.segments:
        if ds.segment.arc is None:
            continue
        c = ds.segment.arc.centre
        pts = [disc.points[i] for i in ds.nodes]
        for p, q in zip(pts, pts[1:]):
            u = (p[0] - c[0], p[1] - c[1])
            v = (q[0] - c[0], q[1] - c[1])
            out.append(abs(math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1])))
    return out


def _arc_to(end):
    """An arc of the unit circle from (1, 0) to ``end``, closed by two
    straight sides through a point far outside; uniform size 100."""
    pts = ((1.0, 0.0), end, (-1.5, -1.5))
    return g.MeshInput("plane_strain", pts, (g.Region((2, 0, 1)),),
                       (g.SegmentSpec(0, 1, arc=g.Arc((0.0, 0.0))),),
                       g.MeshSettings(kind="uniform", size=100.0))


def _arc_of(degrees: float):
    t = math.radians(degrees)
    return _arc_to((math.cos(t), math.sin(t)))


class TestNoPieceTurnsMoreThan10:
    def test_whatever_the_mesh_asks(self):
        cases = [
            CAVITY,                                                      # outer arc: no nodes
            replace(TUNNEL, settings=replace(TUNNEL.settings, boundary_nodes=36)),
            replace(TUNNEL, settings=replace(TUNNEL.settings, kind="uniform",
                                             boundary_nodes=None, size=100.0)),
            DENT,                                                        # 127 degrees
        ]
        for m in cases:
            turns = _turns(d.discretize(m))
            assert turns and max(turns) <= TEN + 1e-12, (max(turns), m.settings)


class TestTheEdges:
    def test_10_10_1_90_179_20_20_1(self):
        for degrees, pieces in ((10.0, 1), (10.1, 2), (90.0, 9), (179.0, 18), (20.0, 2),
                                (20.1, 3)):
            m = _arc_of(degrees)
            assert g.problems(m) == [], (degrees, g.problems(m))
            arc = [ds for ds in d.discretize(m).segments if ds.segment.arc is not None][0]
            assert arc.divisions == pieces, (degrees, arc.divisions)

    def test_a_10_degree_arc_written_with_rounded_coordinates_is_one_piece(self):
        # (cos 10, sin 10) to 12 decimals: theta comes out 1.0000000000006 x pi/18
        m = _arc_to((0.984807753012, 0.173648177667))
        assert g.problems(m) == [], g.problems(m)
        assert g.arc_angle(m, m.segments[0]) > TEN
        assert g.minimum_divisions(m, m.segments[0]) == 1


class TestRefused:
    def test_forced_divisions_below_the_minimum(self):
        quarter = replace(TUNNEL, segments=(replace(TUNNEL.segments[0], divisions=8),)
                          + TUNNEL.segments[1:])
        found = [p for p in g.problems(quarter) if p.rule == "divisions"]
        assert found and "10 degrees" in found[0].message, g.problems(quarter)
        ok = replace(TUNNEL, segments=(replace(TUNNEL.segments[0], divisions=9),)
                     + TUNNEL.segments[1:])
        assert g.problems(ok) == []

    def test_graded_nodes_below_the_sum_of_the_minimums(self):
        assert "graded_nodes" in {p.rule for p in g.problems(
            replace(TUNNEL, settings=replace(TUNNEL.settings, boundary_nodes=35)))}


class TestTheShareKeepsTheMinimums:
    def test_minimums_and_exact_sum(self):
        assert d.share_out(8, [1.0, 1.0, 1.0, 1.0], [2, 2, 2, 2]) == [2, 2, 2, 2]
        assert d.share_out(9, [1.0, 1.0, 1.0, 1.0], [2, 2, 2, 2]) == [3, 2, 2, 2]
        # a short arc that needs 3 next to long straight sides
        got = d.share_out(10, [0.5, 10.0, 10.0], [3, 1, 1])
        assert got[0] >= 3 and sum(got) == 10, got
        for total in range(7, 80):
            got = d.share_out(total, [0.2, 3.0, 7.0, 1.0], [3, 1, 2, 1])
            assert sum(got) == total and all(n >= k for n, k in zip(got, [3, 1, 2, 1])), got
