# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.9 (spec 004, T2) — from the boundaries of a model to its regions (RF-1,
D15).

Invariants protected:

* **the regions fill the external boundary** (identity): the areas of the
  regions, arcs and holes included, add up to the area inside the external
  boundary, in a tunnel with arcs, two strata split by an open material
  boundary, an excavation split by an open stage boundary, a lens (a closed
  material boundary that touches nothing: a hole of the region around it)
  and a circle tangent to a straight line at a shared vertex;
* **Euler** (identity): V - E + F = 1 + C, the faces counting the outside
  one and C the groups of boundaries that touch;
* **the order is canonical**: points in the order of the boundaries; every
  ring starting at its smallest index, the outline anticlockwise and the
  holes clockwise; the regions sorted by their outline. Building twice gives
  the same geometry, and the order of the regions does not depend on the
  order of the assignments;
* **every geometric rule catches its case and names the culprit**: the
  table covers regions.RULES exactly;
* **at a vertex the next side is taken by its tangent, and a tie by its
  curvature**: the tangent circle comes out with the areas of the identity;
  ordering by the chord instead breaks them.
"""
from __future__ import annotations

import math
from dataclasses import replace

import _models
from ogr_fem2d.model import model as md
from ogr_fem2d.model import regions

B = md.Boundary
T = _models.tunnel()
L = _models.layers()


def _stage_split():
    """A tunnel whose excavation is split by an open stage boundary along
    its horizontal diameter: three regions."""
    t = T
    hole = replace(t.boundaries[1])
    split = B("split", md.STAGE, ((-1.0, 0.0), (1.0, 0.0)), False, name="Fase")
    return replace(t, boundaries=(t.boundaries[0], hole, split),
                   assignments=(t.assignments[0], md.Assignment((0.0, 0.5), "rock", (True,)),
                                md.Assignment((0.0, -0.5), "rock", (True,))))


def _lens():
    """A lens with a smaller lens inside it, neither touching anything: the
    inner one is a hole of the outer one, not of the rock."""
    lens = B("lens", md.MATERIAL, ((2.0, 2.0), (4.0, 2.0), (4.0, 4.0), (2.0, 4.0)), True)
    inner = B("inner", md.MATERIAL, ((2.5, 2.5), (3.5, 2.5), (3.5, 3.5), (2.5, 3.5)), True)
    return replace(T, boundaries=T.boundaries + (lens, inner),
                   assignments=T.assignments + (md.Assignment((2.2, 2.2), "rock", (False,)),
                                                md.Assignment((3.0, 3.0), "rock", (False,))))


def _touching():
    """A circle on a line, as _tangent, with a triangle inside the circle
    that touches it at the point of tangency: at (0, 0) six sides leave, and
    their order by the tangent is not their order by the chord (the arcs
    turn 150 degrees: their chords leave at 75 and 105 degrees, the
    triangle's sides at 45 and 135)."""
    s, c = 0.5, 1.0 + math.sqrt(3.0) / 2.0          # (sin 150, 1 - cos 150)
    ext = B("ext", md.EXTERNAL, ((-5.0, -5.0), (5.0, -5.0), (5.0, 0.0), (5.0, 5.0), (-5.0, 5.0),
                                 (-5.0, 0.0)), True)
    line = B("line", md.MATERIAL, ((-5.0, 0.0), (0.0, 0.0), (5.0, 0.0)), False)
    circle = B("circle", md.MATERIAL, ((0.0, 0.0), (s, c), (-s, c)), True,
               tuple(md.SegmentAttr(k, (0.0, 1.0)) for k in range(3)))
    tri = B("tri", md.MATERIAL, ((0.0, 0.0), (0.3, 0.3), (-0.3, 0.3)), True)
    return md.Model(boundaries=(ext, line, circle, tri), materials=(md.Material("m"),),
                    assignments=(md.Assignment((0.0, -2.5), "m", (False,)),
                                 md.Assignment((3.0, 3.0), "m", (False,)),
                                 md.Assignment((0.0, 1.0), "m", (False,)),
                                 md.Assignment((0.0, 0.2), "m", (False,))))


def _tangent():
    """A square split by a horizontal line through (0, 0), and a circle of
    radius 1 centred at (0, 1) that touches the line at (0, 0), where the
    arc and the line leave with the same tangent."""
    ext = B("ext", md.EXTERNAL, ((-5.0, -5.0), (5.0, -5.0), (5.0, 0.0), (5.0, 5.0), (-5.0, 5.0),
                                 (-5.0, 0.0)), True)
    line = B("line", md.MATERIAL, ((-5.0, 0.0), (0.0, 0.0), (5.0, 0.0)), False)
    circle = B("circle", md.MATERIAL, ((0.0, 0.0), (1.0, 1.0), (0.0, 2.0), (-1.0, 1.0)), True,
               tuple(md.SegmentAttr(k, (0.0, 1.0)) for k in range(4)))
    return md.Model(boundaries=(ext, line, circle), materials=(md.Material("m"),),
                    assignments=(md.Assignment((0.0, -2.5), "m", (False,)),
                                 md.Assignment((3.0, 3.0), "m", (False,)),
                                 md.Assignment((0.0, 1.0), "m", (False,))))


MODELS = {"tunnel": (T, 400.0), "layers": (L, 200.0), "stage split": (_stage_split(), 400.0),
          "lens": (_lens(), 400.0), "tangent": (_tangent(), 100.0),
          "touching": (_touching(), 100.0)}


def _components(geo):
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            x = parent[x]
        return x

    for s in geo.segments:
        parent[find(s.a)] = find(s.b)
    return len({find(p) for p in range(len(geo.points))})


class TestTheIdentities:
    def test_the_regions_fill_the_external_boundary(self):
        for name, (m, area) in MODELS.items():
            geo = regions.build(m)
            total = sum(regions.region_area(geo, r) for r in range(len(geo.regions)))
            assert abs(total - area) <= 1e-12 * area, (name, total)
            assert all(regions.region_area(geo, r) > 0.0 for r in range(len(geo.regions))), name

    def test_euler(self):
        for name, (m, _area) in MODELS.items():
            geo = regions.build(m)
            v, e, f = len(geo.points), len(geo.segments), len(geo.regions) + 1
            assert v - e + f == 1 + _components(geo), name

    def test_the_numbers_of_regions(self):
        counts = {name: len(regions.build(m).regions) for name, (m, _a) in MODELS.items()}
        assert counts == {"tunnel": 2, "layers": 2, "stage split": 3, "lens": 2 + 2, "tangent": 3,
                          "touching": 4}

    def test_the_tangent_circle_has_its_areas(self):
        geo = regions.build(_tangent())
        areas = sorted(regions.region_area(geo, r) for r in range(3))
        assert abs(areas[0] - math.pi) < 1e-12 and abs(areas[1] - (50.0 - math.pi)) < 1e-12
        assert abs(areas[2] - 50.0) < 1e-12


class TestTheCanonicalOrder:
    def test_the_tunnel(self):
        geo = regions.build(T)
        assert geo.points[:4] == T.boundaries[0].vertices
        assert [(r.outline, r.holes) for r in geo.regions] == [
            ((0, 1, 2, 3), ((4, 7, 6, 5),)), ((4, 5, 6, 7), ())]
        assert [r.assignment for r in geo.regions] == [0, 1]
        assert [s.excavation for s in geo.segments] == [False] * 4 + [True] * 4

    def test_twice_the_same_and_the_assignments_do_not_order_the_regions(self):
        for _name, (m, _a) in MODELS.items():
            assert regions.build(m) == regions.build(m)
            flipped = replace(m, assignments=m.assignments[::-1])
            a, b = regions.build(m), regions.build(flipped)
            assert [(r.outline, r.holes) for r in a.regions] == [(r.outline, r.holes) for r in b.regions]

    def test_rings_start_at_their_smallest_index_and_turn_the_right_way(self):
        from ogr_fem2d.mesh import geometry as g
        for _name, (m, _a) in MODELS.items():
            geo = regions.build(m)
            arcs = regions._arcs(geo.points, geo.segments)
            outlines = [r.outline for r in geo.regions]
            assert outlines == sorted(outlines)
            for r in geo.regions:
                assert list(r.holes) == sorted(r.holes)
                for ring in (r.outline,) + r.holes:
                    assert len(set(ring)) == len(ring), ring      # a mesher ring repeats no point
                assert r.outline[0] == min(r.outline)
                assert g._ring_area(r.outline, geo.points, arcs) > 0.0
                for h in r.holes:
                    assert h[0] == min(h) and g._ring_area(h, geo.points, arcs) < 0.0

    def test_a_shared_side_is_one_segment(self):
        geo = regions.build(_stage_split())
        diameter = [s for s in geo.segments if len(s.origin) == 1 and s.origin[0][0] == "split"]
        assert len(diameter) == 1
        assert len(geo.segments) == 4 + 4 + 1


def _ext(*vertices):
    return B("ext", md.EXTERNAL, vertices, True)


SQ = _ext((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))
M = (md.Material("m"),)
A = (md.Assignment((5.0, 5.0), "m", (False,)),)

CASES = {
    "arc": (replace(T, boundaries=(T.boundaries[0], replace(
        T.boundaries[1], segments=(md.SegmentAttr(0, (0.1, 0.0)),)))), "boundary 'hole'"),
    "segment_conflict": (replace(T, boundaries=T.boundaries + (
        B("chord", md.MATERIAL, ((1.0, 0.0), (0.0, 1.0)), False),)), "boundary 'chord'"),
    "crossing": (md.Model(boundaries=(SQ, B("cut", md.MATERIAL, ((-1.0, 5.0), (11.0, 5.0)), False)),
                          materials=M, assignments=A), "boundary 'cut'"),
    "dangling": (md.Model(boundaries=(SQ, B("tail", md.MATERIAL, ((0.0, 0.0), (5.0, 5.0)), False)),
                          materials=M, assignments=A), "boundary 'tail'"),
    "outside_external": (md.Model(boundaries=(SQ, B("far", md.MATERIAL, ((20.0, 0.0), (30.0, 0.0),
                                                                          (30.0, 10.0)), True)),
                                  materials=M, assignments=A), "model"),
    "region_unassigned": (replace(T, assignments=T.assignments[:1]), "the region with outline"),
    "region_twice": (replace(T, assignments=T.assignments + (md.Assignment((7.0, 7.0), "rock",
                                                                             (False,)),)),
                     "the region with outline"),
    "assignment_outside": (replace(T, assignments=T.assignments + (md.Assignment((50.0, 0.0), "rock",
                                                                                   (False,)),)),
                           "assignment at (50.0, 0.0)"),
}


class TestEveryRule:
    def test_the_table_covers_the_rules(self):
        assert set(CASES) == set(regions.RULES)

    def test_each_rule_catches_its_case_and_names_the_culprit(self):
        for rule, (m, where) in CASES.items():
            found = [p for p in md.problems(m) if p.rule == rule]
            assert found, (rule, md.problems(m))
            assert any(where in p.where for p in found), (rule, found)

    def test_a_shared_vertex_is_not_a_crossing(self):
        m = md.Model(boundaries=(_ext((0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (10.0, 10.0), (0.0, 10.0),
                                      (0.0, 5.0)),
                                 B("cut", md.MATERIAL, ((0.0, 5.0), (10.0, 5.0)), False)),
                     materials=M, assignments=(md.Assignment((5.0, 2.0), "m", (False,)),
                                               md.Assignment((5.0, 8.0), "m", (False,))))
        assert md.problems(m) == []

    def test_a_vertex_on_a_side_is_a_crossing(self):
        m = md.Model(boundaries=(SQ, B("cut", md.MATERIAL, ((0.0, 5.0), (10.0, 5.0)), False)),
                     materials=M, assignments=A)
        assert "crossing" in [p.rule for p in md.problems(m)]

    def test_a_ring_of_the_external_inside_the_model(self):
        inner = B("ext2", md.MATERIAL, ((2.0, 2.0), (4.0, 2.0), (4.0, 4.0)), True)
        m = md.Model(boundaries=(replace(SQ, kind=md.MATERIAL, id="outer"), replace(inner, kind=md.EXTERNAL)),
                     materials=M, assignments=(md.Assignment((3.5, 2.5), "m", (False,)),
                                               md.Assignment((8.0, 8.0), "m", (False,))))
        assert "outside_external" in [p.rule for p in md.problems(m)]

    def test_a_material_boundary_outside_the_external_one(self):
        side = B("side", md.MATERIAL, ((10.0, 0.0), (20.0, 0.0), (20.0, 10.0), (10.0, 10.0)), True)
        m = md.Model(boundaries=(SQ, side), materials=M,
                     assignments=(md.Assignment((5.0, 5.0), "m", (False,)),
                                  md.Assignment((15.0, 5.0), "m", (False,))))
        found = [p for p in md.problems(m) if p.rule == "outside_external"]
        # its own sides, on the outside; the side it shares, inside the model
        assert any(p.where == "segment 0 of boundary 'side'" and "outside of the model" in p.message
                   for p in found), found
        assert any("segment 1 of boundary 'ext'" in p.where and "inside the model" in p.message
                   for p in found), found

    def test_the_regions_are_sorted_whatever_order_they_are_found_in(self):
        # with the circle first, the walks find the top region before the
        # bottom one, whose outline sorts first
        m = _tangent()
        m = replace(m, boundaries=(m.boundaries[2], m.boundaries[1], m.boundaries[0]))
        outlines = [r.outline for r in regions.build(m).regions]
        assert outlines == sorted(outlines) and len(outlines) == 3
