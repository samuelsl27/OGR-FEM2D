# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.8 (spec 003, T3) — the input of the mesher and its validation (RF-1;
docs/malla/entrada.md).

Invariants protected:

* **a valid input passes untouched**: a square with a circular excavation
  of four arcs, a slope of two layers and an axisymmetric quarter annulus
  have no problem, and validate() hands the same object back;
* **every rule catches what it is for, and says where**: for each rule of
  geometry.RULES there is an input that breaks it, and the problem reported
  names that rule and the point, region, segment or setting at fault. The
  table of cases covers RULES exactly, so a rule added without its case, or
  a case for a rule that no longer exists, fails here;
* **a segment meets another only at a shared end point** (Shewchuk 2002a,
  §1): a point of one ring in the middle of a segment of another (a T
  junction) is refused, a shared point is not; an arc is checked as an arc,
  not as its chord;
* **the arcs count where the region is**: the area of a region is exact with
  arcs bulging out (the excavation, pi) and in (a square minus the circular
  segment), and a point between an inward arc and its chord is outside the
  region, one just beyond it is inside;
* **an arc is a minor arc**: a centre on the chord (half a circle) is
  refused, 179 degrees is accepted; in axisymmetry an arc that reaches x < 0
  is refused although its end points are on x >= 0;
* **no setting does nothing** (rule 7): a uniform size given to a graded
  mesh, or the graded node count to a uniform one, or to a graded one whose
  segments all have their divisions forced, is refused;
* **the segments of a valid input** come out once each, in the order of the
  rings, with their attributes and the rings that use them, and the graded
  nodes go to the excavation, or to the outer boundary when there is none;
* **all problems at once**.
"""
from __future__ import annotations

import math
from dataclasses import replace

from ogr_fem2d.mesh import geometry as g

S = g.MeshSettings(boundary_nodes=40)
O = g.Arc((0.0, 0.0))

# Square of 20 m with a circular excavation of radius 1, in four arcs.
TUNNEL_POINTS = ((-10.0, -10.0), (10.0, -10.0), (10.0, 10.0), (-10.0, 10.0),
                 (1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0))
ROCK = g.Region((0, 1, 2, 3), holes=((4, 7, 6, 5),), material=0)
EXCAVATION = g.Region((4, 5, 6, 7), material=1)
ARCS = tuple(g.SegmentSpec(a, b, arc=O, excavation=True)
             for a, b in ((4, 5), (5, 6), (6, 7), (7, 4)))
TUNNEL = g.MeshInput("plane_strain", TUNNEL_POINTS, (ROCK, EXCAVATION), ARCS, S)

# A slope of two layers: the contact 6-3-2 is shared, point by point.
SLOPE = g.MeshInput(
    "plane_strain",
    ((0.0, 0.0), (40.0, 0.0), (40.0, 10.0), (25.0, 10.0), (15.0, 20.0), (0.0, 20.0),
     (0.0, 10.0)),
    (g.Region((0, 1, 2, 3, 6)), g.Region((6, 3, 4, 5), material=1)),
    (), g.MeshSettings(boundary_nodes=12))

# Axisymmetric quarter annulus 1 <= R <= 21 about the origin (a spherical cavity).
CAVITY = g.MeshInput(
    "axisymmetric", ((0.0, 1.0), (0.0, 21.0), (21.0, 0.0), (1.0, 0.0)),
    (g.Region((3, 2, 1, 0)),),
    (g.SegmentSpec(2, 1, arc=O), g.SegmentSpec(0, 3, arc=O, excavation=True)), S)

# A 2 x 2 square whose right side is an arc bulging INTO it, about (2.5, 1).
DENT = g.MeshInput(
    "plane_strain", ((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)),
    (g.Region((0, 1, 2, 3)),), (g.SegmentSpec(1, 2, arc=g.Arc((2.5, 1.0))),),
    g.MeshSettings(boundary_nodes=8))       # the arc, of 127 degrees, needs 3 (D14)


def rules_of(m: g.MeshInput) -> set[str]:
    return {p.rule for p in g.problems(m)}


def where_of(m: g.MeshInput, rule: str) -> list[str]:
    return [p.where for p in g.problems(m) if p.rule == rule]


def with_points(m, *extra):
    return replace(m, points=m.points + tuple(extra))


def with_settings(m, **kw):
    return replace(m, settings=replace(m.settings, **kw))


# ------------------------------------------------------ one case per rule
def _t_junction():
    """Two squares side by side; the right one has a point (6) in the middle
    of the left one's side 1-2, which the left one does not have."""
    pts = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (2.0, 0.0), (2.0, 1.0),
           (1.0, 0.5))
    return g.MeshInput("plane_strain", pts,
                       (g.Region((0, 1, 2, 3)), g.Region((1, 4, 5, 2, 6))), (),
                       g.MeshSettings(boundary_nodes=8))


def _arc_through_a_contact():
    """A 2 x 2 square split at x = 1.6; the right side is an arc bulging in
    to x = 1.382, through the contact 4-5."""
    pts = ((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0), (1.6, 0.0), (1.6, 2.0))
    return g.MeshInput("plane_strain", pts,
                       (g.Region((0, 4, 5, 3)), g.Region((4, 1, 2, 5), material=1)),
                       (g.SegmentSpec(1, 2, arc=g.Arc((2.5, 1.0))),),
                       g.MeshSettings(boundary_nodes=8))


def _hole_outside():
    pts = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (5.0, 5.0), (5.0, 6.0), (6.0, 5.0))
    return g.MeshInput("plane_strain", pts, (g.Region((0, 1, 2, 3), holes=((4, 5, 6),)),),
                       (), g.MeshSettings(boundary_nodes=8))


CASES = {
    "analysis": (replace(TUNNEL, analysis="plane_stress"), "model"),
    "points": (replace(TUNNEL, points=((math.nan, -10.0),) + TUNNEL_POINTS[1:]), "point 0"),
    "duplicate_point": (with_points(TUNNEL, (10.0, -10.0)), "point 8"),
    "left_of_axis": (replace(TUNNEL, analysis="axisymmetric"), "point 0"),
    "no_region": (replace(TUNNEL, regions=()), "model"),
    "ring": (replace(TUNNEL, regions=(ROCK, g.Region((4, 5)))), "region 1, outline"),
    "material": (replace(TUNNEL, regions=(ROCK, replace(EXCAVATION, material=-1))), "region 1"),
    "shared_edge": (replace(TUNNEL, regions=(ROCK, EXCAVATION, EXCAVATION)), "segment 4-5"),
    "unknown_segment": (replace(TUNNEL, segments=ARCS + (g.SegmentSpec(0, 2),)), "segment 0-2"),
    "segment_twice": (replace(TUNNEL, segments=ARCS + (g.SegmentSpec(0, 1), g.SegmentSpec(1, 0))),
                      "segment 1-0"),
    "divisions": (replace(TUNNEL, segments=ARCS + (g.SegmentSpec(0, 1, divisions=0),)),
                  "segment 0-1"),
    "arc": (replace(TUNNEL, segments=(g.SegmentSpec(4, 5, arc=g.Arc((0.5, 0.0))),) + ARCS[1:]),
            "segment 4-5"),
    "orientation": (replace(TUNNEL, regions=(replace(ROCK, outline=(0, 3, 2, 1)), EXCAVATION)),
                    "region 0, outline"),
    "crossing": (_t_junction(), "segments 1-2 and 2-6"),
    "arc_crossing": (_arc_through_a_contact(), "segments 4-5 and 1-2"),
    "hole": (_hole_outside(), "region 0, hole 0"),
    "overlap": (replace(with_points(TUNNEL, (5.0, 5.0), (6.0, 5.0), (6.0, 6.0), (5.0, 6.0)),
                        regions=(ROCK, EXCAVATION, g.Region((8, 9, 10, 11)))),
                "region 2 and region 0"),
    "loose_point": (with_points(TUNNEL, (50.0, 50.0)), "point 8"),
    "element_kind": (with_settings(TUNNEL, nodes_per_element=4), "settings"),
    "mesh_kind": (with_settings(TUNNEL, kind="radial"), "settings"),
    "quality_bound": (with_settings(TUNNEL, quality_bound=1.2), "settings"),
    "graded_nodes": (with_settings(TUNNEL, boundary_nodes=3), "settings"),
    "max_size": (with_settings(TUNNEL, max_size=-1.0), "settings"),
    "uniform_size": (with_settings(TUNNEL, kind="uniform", boundary_nodes=None), "settings"),
    "window": (with_settings(TUNNEL, windows=(g.Window(((0.0, 0.0), (1.0, 1.0)), 0.5),)),
               "window 0"),
}


class TestValidInputs:
    def test_they_have_no_problem_and_come_back_untouched(self):
        uniform = with_settings(TUNNEL, kind="uniform", boundary_nodes=None, size=0.5,
                                windows=(g.Window(((-2.0, -2.0), (2.0, -2.0), (2.0, 2.0),
                                                   (-2.0, 2.0)), 0.1),))
        for m in (TUNNEL, SLOPE, CAVITY, DENT, uniform):
            assert g.problems(m) == [], g.problems(m)
            assert g.validate(m) is m

    def test_the_areas_count_the_arcs_out_and_in(self):
        assert math.isclose(g.region_area(TUNNEL, 0), 400.0 - math.pi, rel_tol=1e-13)
        assert math.isclose(g.region_area(TUNNEL, 1), math.pi, rel_tol=1e-13)
        assert math.isclose(g.region_area(CAVITY, 0), math.pi * (21.0 ** 2 - 1.0) / 4.0,
                            rel_tol=1e-13)
        assert math.isclose(g.region_area(SLOPE, 0), 400.0, rel_tol=1e-15)
        # trapezoid between y = 10 (0 to 25) and y = 20 (0 to 15)
        assert math.isclose(g.region_area(SLOPE, 1), 0.5 * (25.0 + 15.0) * 10.0, rel_tol=1e-15)
        r = math.sqrt(1.25)                      # the dent: chord 2 at 0.5 from the centre
        theta = 2.0 * math.asin(1.0 / r)
        assert math.isclose(g.region_area(DENT, 0),
                            4.0 - 0.5 * r * r * (theta - math.sin(theta)), rel_tol=1e-13)

    def test_a_point_behind_an_inward_arc_is_outside(self):
        # the dent reaches x = 2.5 - sqrt(1.25) = 1.382
        assert "loose_point" in rules_of(with_points(DENT, (1.8, 1.0)))
        assert g.problems(with_points(DENT, (1.2, 1.0))) == []


class TestEveryRule:
    def test_the_cases_cover_the_rules_exactly(self):
        assert set(CASES) == set(g.RULES)

    def test_each_case_is_caught_and_says_where(self):
        for rule, (m, where) in CASES.items():
            found = where_of(m, rule)
            assert found, (rule, g.problems(m))
            assert any(where in w for w in found), (rule, found)

    def test_validate_raises_with_every_problem(self):
        m = with_settings(with_points(TUNNEL, (50.0, 50.0)), quality_bound=1.0,
                          nodes_per_element=8)
        try:
            g.validate(m)
        except g.MeshInputError as e:
            assert {p.rule for p in e.problems} == {"loose_point", "quality_bound",
                                                    "element_kind"}, e.problems
        else:
            raise AssertionError("not refused")


class TestSegmentsMeetOnlyAtSharedPoints:
    def test_a_shared_point_is_fine_a_t_junction_is_not(self):
        assert g.problems(SLOPE) == []
        broken = replace(SLOPE, regions=(g.Region((0, 1, 2, 6)), SLOPE.regions[1]))
        assert "crossing" in rules_of(broken)        # 3 sits on 2-6 unshared

    def test_a_region_given_twice(self):
        # two rings on every segment, the same way round: without the check of
        # the direction nothing else would see it (the overlap test skips the
        # sides two regions share)
        twice = replace(SLOPE, regions=SLOPE.regions + (SLOPE.regions[1],))
        assert any("the same way" in p.message for p in g.problems(twice)
                   if p.rule == "shared_edge"), g.problems(twice)

    def test_two_segments_that_cross(self):
        bow = replace(SLOPE, regions=(g.Region((0, 1, 6, 2)),))   # a bow tie
        assert "crossing" in rules_of(bow)

    def test_an_arc_is_checked_as_an_arc(self):
        # the chord of 1-2 is x = 2, far from the contact x = 1.6; the arc is not
        assert "arc_crossing" in rules_of(_arc_through_a_contact())
        straight = replace(_arc_through_a_contact(), segments=())
        assert g.problems(straight) == []


class TestArcs:
    def test_half_a_circle_is_refused_179_degrees_is_not(self):
        def lens(half_angle_deg):
            t = math.radians(half_angle_deg)
            pts = ((math.cos(t), -math.sin(t)), (math.cos(t), math.sin(t)), (-2.0, 0.0))
            # chord at x = cos t; the minor arc about the origin bulges to the
            # right, away from the third point (with the third point on the
            # right, its sides would cut the arc: that is a crossing)
            return g.MeshInput("plane_strain", pts, (g.Region((0, 1, 2)),),
                               (g.SegmentSpec(0, 1, arc=O),), g.MeshSettings(boundary_nodes=5))
        assert "arc" in rules_of(lens(90.0))
        assert g.problems(lens(89.5)) == []

    def test_an_arc_that_reaches_left_of_the_axis(self):
        pts = ((0.0, -1.0), (2.0, -1.0), (2.0, 1.0), (0.0, 1.0))
        m = g.MeshInput("axisymmetric", pts, (g.Region((0, 1, 2, 3)),),
                        (g.SegmentSpec(3, 0, arc=g.Arc((1.0, 0.0))),),
                        g.MeshSettings(boundary_nodes=6))
        assert where_of(m, "left_of_axis") == ["segment 0-3"], g.problems(m)
        assert g.problems(replace(m, analysis="plane_strain")) == []


class TestNoSettingDoesNothing:
    def test_a_uniform_size_on_a_graded_mesh(self):
        assert "uniform_size" in rules_of(with_settings(TUNNEL, size=1.0))
        assert "uniform_size" in rules_of(with_settings(TUNNEL, elements=100))

    def test_graded_settings_on_a_uniform_mesh(self):
        assert "graded_nodes" in rules_of(with_settings(TUNNEL, kind="uniform", size=1.0))
        assert "max_size" in rules_of(with_settings(TUNNEL, kind="uniform", size=1.0,
                                                    boundary_nodes=None, max_size=2.0))

    def test_boundary_nodes_when_every_target_is_forced(self):
        forced = replace(TUNNEL, segments=tuple(replace(s, divisions=8) for s in ARCS))
        assert "graded_nodes" in rules_of(forced)
        assert g.problems(with_settings(forced, boundary_nodes=None)) == []

    def test_boundary_nodes_are_needed_otherwise(self):
        assert "graded_nodes" in rules_of(with_settings(TUNNEL, boundary_nodes=None))
        # four arcs of 90 degrees need two pieces each (D14): 8 nodes, not 7
        assert "graded_nodes" in rules_of(with_settings(TUNNEL, boundary_nodes=7))
        assert g.problems(with_settings(TUNNEL, boundary_nodes=8)) == []


class TestSegments:
    def test_once_each_in_ring_order_with_attributes(self):
        segs = g.segments(TUNNEL)
        assert [(s.a, s.b) for s in segs] == [(0, 1), (1, 2), (2, 3), (3, 0),
                                              (4, 7), (7, 6), (6, 5), (5, 4)]
        assert [s.outer for s in segs] == [True] * 4 + [False] * 4
        assert all(s.arc == O and s.excavation for s in segs[4:])
        assert segs[4].rings == ((0, 1), (1, 0))

    def test_the_graded_nodes_go_to_the_excavation_or_the_outer_boundary(self):
        assert [(s.a, s.b) for s in g.graded_targets(g.segments(TUNNEL))] == \
            [(4, 7), (7, 6), (6, 5), (5, 4)]
        targets = g.graded_targets(g.segments(SLOPE))
        assert [(s.a, s.b) for s in targets] == [(0, 1), (1, 2), (2, 3), (6, 0), (3, 4),
                                                 (4, 5), (5, 6)]

    def test_the_same_input_gives_the_same_segments(self):
        assert g.segments(TUNNEL) == g.segments(replace(TUNNEL))
