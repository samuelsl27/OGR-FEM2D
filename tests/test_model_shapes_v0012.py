# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.12 (spec 006, T4) — arcs and circles as the segments of a boundary
(RF-3, D10).

Invariants protected:

* **the circle through three points is theirs**: three points of a known
  circle give its centre; three on one line, or two the same, are refused;
* **an arc goes the way asked**: through the middle point, or anticlockwise
  or clockwise about its centre; every vertex it puts is on its circle, and
  between its ends;
* **half a circle or more is two segments**, split at its middle (the
  segment keeps the minor arc: spec 003, D4); less is one;
* **a circle is four arcs of 90°** whose vertices are exact at the default
  start (the hole of case 005), and whose area, through the model's own
  region areas, is pi r^2;
* **a boundary drawn with lines and arcs is valid** as the model asks, also
  when an arc closes it on its first vertex.
"""
from __future__ import annotations

import math

import _models
from ogr_fem2d.model import edit, regions, shapes
from ogr_fem2d.model import model as md

C, R = (2.0, 3.0), 5.0
TOL = 1e-12


def _at(deg: float):
    t = math.radians(deg)
    return (C[0] + R * math.cos(t), C[1] + R * math.sin(t))


def _angle(p) -> float:
    return math.degrees(math.atan2(p[1] - C[1], p[0] - C[0])) % 360.0


def _refused(fn, *words):
    try:
        fn()
    except md.ModelError as err:
        assert err.problems[0].rule == "arc", str(err)
        for w in words:
            assert w in str(err), (w, str(err))
    else:
        raise AssertionError("accepted")


class TestThreePoints:
    def test_the_circle_of_the_three(self):
        piece = shapes.arc_three_points(_at(10.0), _at(60.0), _at(100.0))
        assert math.dist(piece.centre, C) <= TOL * 10
        assert piece.vertices == (_at(100.0),)

    def test_the_way_through_the_middle_point(self):
        # from 0 deg to 270 deg: through 200 deg it is 270 deg anticlockwise, split
        piece = shapes.arc_three_points(_at(0.0), _at(200.0), _at(270.0))
        mid, end = piece.vertices
        assert end == _at(270.0) and abs(_angle(mid) - 135.0) <= 1e-9
        assert abs(math.dist(mid, C) - R) <= TOL * 10
        # through 300 deg it is 90 deg clockwise, one segment
        piece = shapes.arc_three_points(_at(0.0), _at(300.0), _at(270.0))
        assert piece.vertices == (_at(270.0),)

    def test_refused(self):
        _refused(lambda: shapes.arc_three_points((0, 0), (1, 1), (2, 2)), "one line")
        _refused(lambda: shapes.arc_three_points((0, 0), (0, 0), (2, 2)), "the same")


class TestAboutACentre:
    def test_the_way_asked(self):
        a, b = _at(0.0), _at(90.0)
        assert shapes.arc_by_centre(a, C, b, anticlockwise=True).vertices == (b,)
        mid, end = shapes.arc_by_centre(a, C, b, anticlockwise=False).vertices
        assert end == b and abs(_angle(mid) - 225.0) <= 1e-9

    def test_by_angle(self):
        assert len(shapes.arc_by_angle(_at(0.0), C, 179.0).vertices) == 1
        mid, end = shapes.arc_by_angle(_at(0.0), C, 180.0).vertices
        assert abs(_angle(mid) - 90.0) <= 1e-9 and abs(_angle(end) - 180.0) <= 1e-9
        mid, end = shapes.arc_by_angle(_at(30.0), C, -300.0).vertices
        assert abs(_angle(mid) - 240.0) <= 1e-9 and abs(_angle(end) - 90.0) <= 1e-9
        for p in (mid, end):
            assert abs(math.dist(p, C) - R) <= TOL * 10

    def test_refused(self):
        _refused(lambda: shapes.arc_by_centre(_at(0.0), C, (C[0], C[1] + 2 * R)), "not on one circle")
        _refused(lambda: shapes.arc_by_angle(_at(0.0), C, 360.0), "between 0 and 360")
        _refused(lambda: shapes.arc_by_angle(C, C, 90.0), "radius is zero")


class TestCircles:
    def test_four_arcs_exact_at_the_default_start(self):
        vertices, segments = shapes.circle((0.0, 0.0), 1.0)
        hole = _models.tunnel().boundary("hole")
        assert vertices == hole.vertices and segments == hole.segments

    def test_its_area_is_pi_r2(self):
        for start in (0.0, 17.0):
            vertices, segments = shapes.circle(C, R, start)
            got = [_angle(v) for v in vertices]
            assert all(abs(a - (start + 90.0 * k)) <= 1e-9 for k, a in enumerate(got)), got
            m = edit.add_boundary(md.Model(), md.EXTERNAL, vertices, segments=segments)
            m = md.Model(boundaries=m.boundaries, materials=(md.Material("a"),),
                         assignments=(md.Assignment(C, "a", (False,)),))
            assert md.problems(m) == []
            geo = regions.build(m)
            assert abs(regions.region_area(geo, 0) - math.pi * R * R) <= 1e-9 * R * R

    def test_through_a_point(self):
        p = _at(40.0)
        vertices, _ = shapes.circle_through(C, p)
        assert vertices[0] == p
        assert all(abs(math.dist(v, C) - R) <= TOL * 10 for v in vertices)
        assert abs(_angle(vertices[1]) - 130.0) <= 1e-9


class TestDrawn:
    def test_lines_and_an_arc_closing_on_the_first_vertex(self):
        # a tunnel profile: a floor, two walls and a vault of half a circle
        d = (shapes.Drawn.start((-1.0, 0.0)).line_to((-1.0, -1.0)).line_to((1.0, -1.0))
             .line_to((1.0, 0.0)).arc_to(shapes.arc_by_centre((1.0, 0.0), (0.0, 0.0), (-1.0, 0.0))))
        assert d.closed and d.vertices[-1] == (0.0, 1.0)
        assert [s.index for s in d.segments] == [3, 4]
        m = edit.add_boundary(md.Model(), md.EXTERNAL, d.vertices, closed=d.closed,
                              segments=d.segments)
        m = md.Model(boundaries=m.boundaries, materials=(md.Material("a"),),
                     assignments=(md.Assignment((0.0, 0.0), "a", (False,)),))
        assert md.problems(m) == []
        geo = regions.build(m)
        assert abs(regions.region_area(geo, 0) - (2.0 + 0.5 * math.pi)) <= 1e-12

    def test_an_open_arc(self):
        d = shapes.Drawn.start(_at(0.0)).arc_to(shapes.arc_by_angle(_at(0.0), C, 90.0))
        assert not d.closed and d.segments == (md.SegmentAttr(0, d.segments[0].arc),)
        m = edit.add_boundary(md.Model(), md.MATERIAL, d.vertices, segments=d.segments)
        assert m.boundaries[0].n_segments == 1
