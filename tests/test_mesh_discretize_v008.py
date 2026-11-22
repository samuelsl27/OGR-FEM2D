# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.8 (spec 003, T4) — step 1 of the mesher: the nodes of every segment
(RF-2, D5, D10; ogr_fem2d/mesh/discretize.py).

Invariants protected:

* **the nodes are where the geometry is**: on a straight segment they are
  equally spaced along it; on an arc they are ON the circle (|x - c| = R to
  rounding) and at equal angles of the minor arc, the side of the chord away
  from the centre; on the axis of an axisymmetric model, x is exactly 0;
* **the ends are shared**: a segment runs from its input point a to its
  input point b, so two segments that meet use the same node, and the new
  nodes are added after the input points, Σ(n - 1) of them;
* **the graded share adds up**: the excavation (or the outer boundary)
  receives exactly ``boundary_nodes`` divisions, at least one per segment,
  in proportion to the length (four equal arcs: a quarter each), ties to the
  first segment; the forced divisions are kept and stay out of the share;
  every other segment enters with its ends only;
* **the uniform size is a bound and the fewest divisions that keep it**:
  every piece is no longer than h and one division fewer would break it; h
  from N elements is that of N equilateral triangles over the area;
* **every option moves the nodes** (rule 7): boundary_nodes, a forced
  division, the size and the number of elements;
* **the same input gives the same points** (D11).
"""
from __future__ import annotations

import math
from dataclasses import replace

from ogr_fem2d.mesh import discretize as d
from ogr_fem2d.mesh import geometry as g
from test_mesh_input_v008 import CAVITY, SLOPE, TUNNEL


def _by_ends(disc):
    return {(ds.segment.a, ds.segment.b): ds for ds in disc.segments}


def _uniform(m, **kw):
    return replace(m, settings=replace(m.settings, kind="uniform", boundary_nodes=None, **kw))


class TestWhereTheNodesAre:
    def test_on_the_circle_at_equal_angles_on_the_minor_arc(self):
        disc = d.discretize(TUNNEL)
        for ds in disc.segments[4:]:                     # the four arcs, radius 1
            pts = [disc.points[i] for i in ds.nodes]
            for p in pts:
                assert abs(math.hypot(*p) - 1.0) <= 2e-16, p
            angles = [math.atan2(p[1], p[0]) for p in pts]
            steps = [(angles[k + 1] - angles[k] + math.pi) % (2 * math.pi) - math.pi
                     for k in range(len(angles) - 1)]
            assert max(steps) - min(steps) <= 1e-14, steps
            assert abs(sum(steps)) < math.pi           # the minor arc
            chord_mid = ((pts[0][0] + pts[-1][0]) / 2, (pts[0][1] + pts[-1][1]) / 2)
            for p in pts[1:-1]:                        # away from the centre
                assert math.hypot(*p) > math.hypot(*chord_mid)

    def test_equally_spaced_along_a_straight_segment(self):
        disc = d.discretize(_uniform(SLOPE, size=3.0))
        for ds in disc.segments:
            pts = [disc.points[i] for i in ds.nodes]
            gaps = [math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1)]
            assert max(gaps) - min(gaps) <= 1e-12 * max(gaps), gaps
            a, b = pts[0], pts[-1]
            for p in pts:
                assert abs((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])) \
                    <= 1e-12 * math.dist(a, b) ** 2

    def test_on_the_axis_x_is_exactly_zero(self):
        disc = d.discretize(_uniform(CAVITY, size=0.5))
        axis = [ds for ds in disc.segments if all(disc.points[i][0] == 0.0
                                                  for i in (ds.segment.a, ds.segment.b))]
        assert axis and all(disc.points[i][0] == 0.0 for ds in axis for i in ds.nodes)


class TestSharedEnds:
    def test_each_segment_runs_between_its_input_points(self):
        disc = d.discretize(TUNNEL)
        assert disc.points[:len(TUNNEL.points)] == TUNNEL.points
        for ds in disc.segments:
            assert (ds.nodes[0], ds.nodes[-1]) == (ds.segment.a, ds.segment.b)
        new = sum(ds.divisions - 1 for ds in disc.segments)
        assert len(disc.points) == len(TUNNEL.points) + new
        inner = [i for ds in disc.segments for i in ds.nodes[1:-1]]
        assert sorted(inner) == list(range(len(TUNNEL.points), len(disc.points)))


class TestGradedShare:
    def test_four_equal_arcs_take_a_quarter_each(self):
        disc = d.discretize(TUNNEL)                    # boundary_nodes = 40
        assert [ds.divisions for ds in disc.segments] == [1, 1, 1, 1, 10, 10, 10, 10]

    def test_the_share_adds_up_and_follows_the_length(self):
        assert d.share_out(10, [1.0, 1.0, 1.0, 1.0]) == [3, 3, 2, 2]     # ties to the first
        # ideal 1.67, 1.67, 0.33, 1.33: the one left goes to the first of the tie
        assert d.share_out(5, [5.0, 5.0, 1.0, 4.0]) == [2, 1, 1, 1]
        assert d.share_out(8, [5.0, 5.0, 1.0, 4.0]) == [3, 2, 1, 2]
        assert d.share_out(3, [10.0, 0.1, 0.1]) == [1, 1, 1]             # at least one each
        assert d.share_out(7, [3.0, 1.0]) == [5, 2]                      # 5.25 and 1.75
        # with a tiny segment (the minimum of one binds) and without (it does not
        # bind once the total passes 55, and the share must be within one)
        within_one = 0
        for lengths in ([0.3, 2.0, 5.5, 0.01, 1.2, 7.0, 0.5], [0.3, 2.0, 5.5, 1.2, 7.0, 0.5]):
            for total in range(len(lengths), 200):
                got = d.share_out(total, lengths)
                assert sum(got) == total and min(got) >= 1, (total, got)
                # a longer segment never gets fewer divisions than a shorter one
                for i in range(len(lengths)):
                    for j in range(len(lengths)):
                        if lengths[i] > lengths[j]:
                            assert got[i] >= got[j], (total, got)
                # where the minimum of one does not bind, within one of the
                # ideal share (with few divisions it binds: 8 for the first
                # lengths leaves 3 for the two long ones, ideally 6)
                ideal = [total * x / sum(lengths) for x in lengths]
                if min(ideal) >= 1.0:
                    assert all(abs(n - x) < 1.0 for n, x in zip(got, ideal)), (total, got)
                    within_one += 1
        assert within_one > 100, within_one             # the check above did run

    def test_without_excavation_the_outer_boundary_takes_it(self):
        disc = d.discretize(SLOPE)                     # boundary_nodes = 12
        by = _by_ends(disc)
        assert by[(2, 3)].divisions + by[(0, 1)].divisions + by[(1, 2)].divisions \
            + by[(6, 0)].divisions + by[(3, 4)].divisions + by[(4, 5)].divisions \
            + by[(5, 6)].divisions == 12
        assert by[(3, 6)].divisions == 1               # the contact between layers

    def test_forced_divisions_are_kept_and_left_out_of_the_share(self):
        forced = replace(TUNNEL, segments=(replace(TUNNEL.segments[0], divisions=4),)
                         + TUNNEL.segments[1:] + (g.SegmentSpec(0, 1, divisions=6),))
        disc = d.discretize(replace(forced, settings=replace(forced.settings, boundary_nodes=30)))
        by = _by_ends(disc)
        assert by[(4, 7)].divisions + by[(7, 6)].divisions + by[(6, 5)].divisions == 30
        assert by[(5, 4)].divisions == 4 and by[(0, 1)].divisions == 6


class TestUniformSize:
    def test_no_piece_longer_than_h_and_the_fewest_divisions(self):
        # lengths from the geometry, not from the code: the tunnel's sides are
        # 20 and its arcs pi/2; the slope's, the distances between its points
        h = 3.0
        cases = [(_uniform(TUNNEL, size=h), {(0, 1): 20.0, (4, 7): math.pi / 2})]
        slope = _uniform(SLOPE, size=h)
        cases.append((slope, {(s.a, s.b): math.dist(SLOPE.points[s.a], SLOPE.points[s.b])
                              for s in g.segments(SLOPE)}))
        for m, lengths in cases:
            got = {(s.a, s.b): n for s, n in d.divisions(m)}
            for key, length in lengths.items():
                n = got[key]
                assert length / n <= h and (n == 1 or length / (n - 1) > h), (key, n)
        assert {(s.a, s.b): n for s, n in d.divisions(slope)}[(0, 1)] == 14   # 40/3 = 13.3

    def test_an_arc_is_measured_along_the_arc(self):
        assert math.isclose(d.segment_length(TUNNEL, g.segments(TUNNEL)[4]), math.pi / 2,
                            rel_tol=1e-15)
        # pi/2 = 1.571 > 1.5 > sqrt(2), its chord: two divisions, not one
        got = {(s.a, s.b): n for s, n in d.divisions(_uniform(TUNNEL, size=1.5))}
        assert got[(4, 7)] == 2

    def test_forced_divisions_are_kept_in_a_uniform_mesh(self):
        forced = replace(TUNNEL, segments=TUNNEL.segments + (g.SegmentSpec(0, 1, divisions=3),))
        got = {(s.a, s.b): n for s, n in d.divisions(_uniform(forced, size=1.0))}
        assert got[(0, 1)] == 3 and got[(1, 2)] == 20

    def test_h_from_a_number_of_elements(self):
        m = _uniform(TUNNEL, elements=500)
        area = 400.0                                    # rock 400 - pi, excavation pi
        assert math.isclose(d.uniform_size(m), math.sqrt(4 * area / (math.sqrt(3) * 500)),
                            rel_tol=1e-14)
        assert d.discretize(m).size == d.uniform_size(m)


class TestEveryOptionMovesTheNodes:
    def test_rule_7(self):
        base = len(d.discretize(TUNNEL).points)
        more = replace(TUNNEL, settings=replace(TUNNEL.settings, boundary_nodes=80))
        assert len(d.discretize(more).points) == base + 40
        forced = replace(TUNNEL, segments=TUNNEL.segments + (g.SegmentSpec(0, 1, divisions=5),))
        assert len(d.discretize(forced).points) == base + 4
        a = len(d.discretize(_uniform(TUNNEL, size=2.0)).points)
        b = len(d.discretize(_uniform(TUNNEL, size=1.0)).points)
        c = len(d.discretize(_uniform(TUNNEL, elements=100)).points)
        e = len(d.discretize(_uniform(TUNNEL, elements=1000)).points)
        assert a < b and c < e


class TestDeterminism:
    def test_the_same_input_gives_the_same_points(self):
        assert d.discretize(TUNNEL) == d.discretize(replace(TUNNEL))


class TestOnlyAValidInput:
    def test_an_invalid_input_is_refused_before_dividing(self):
        broken = replace(TUNNEL, settings=replace(TUNNEL.settings, quality_bound=1.0))
        try:
            d.discretize(broken)
        except g.MeshInputError as e:
            assert [p.rule for p in e.problems] == ["quality_bound"]
        else:
            raise AssertionError("not refused")
