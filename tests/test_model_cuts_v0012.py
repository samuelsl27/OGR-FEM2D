# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.12 (spec 006, T3) — the cuts between boundaries (RF-2; spec 004,
D15).

Invariants protected:

* **every vertex a cut puts is on both segments**: on the line, or on the
  circle of an arc within the model's tolerance, and in both boundaries;
  straight with straight, straight with an arc and arc with arc;
* **a T puts the end into the other boundary**, exactly the end (not a
  point next to it); a meeting at a vertex both have puts nothing;
* **an arc cut stays an arc**: both halves about the same centre;
* **the regions after the cuts are the drawing's**: a line across the model
  splits it into the two regions it should, and the model is valid once each
  has its material;
* **a stretch in common is refused**, naming both; the same side in two
  boundaries is not a stretch in common;
* **the response says what went in**, and a boundary that meets nothing
  gives the model back as it was.
"""
from __future__ import annotations

import math
from dataclasses import replace

import _models
from ogr_fem2d.mesh import geometry as g
from ogr_fem2d.model import cuts, edit, regions
from ogr_fem2d.model import model as md

SQUARE = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))
TOL = 1e-12


def _square() -> md.Model:
    m = edit.add_boundary(md.Model(), md.EXTERNAL, SQUARE)
    return replace(m, materials=(md.Material("a", E=1.0, nu=0.2), md.Material("b", E=2.0, nu=0.2)))


def _on_line(p, a, b) -> bool:
    return abs(g._cross(a, b, p)) <= TOL * 100.0


def _on_circle(p, c, r) -> bool:
    return abs(math.dist(p, c) - r) <= TOL * 10.0


def _refused(fn, rule: str, *words: str):
    try:
        fn()
    except md.ModelError as err:
        p = err.problems[0]
        assert p.rule == rule, (p.rule, str(err))
        for w in words:
            assert w in f"{p.where} {p.message}", (w, str(err))
    else:
        raise AssertionError(f"accepted; expected {rule!r}")


class TestStraight:
    def test_a_line_across_the_model_makes_two_regions(self):
        m = edit.add_boundary(_square(), md.MATERIAL, ((0.0, 3.0), (10.0, 3.0)))
        out = cuts.cut(m, "mat1")
        assert len(out.added) == 2
        assert set(out.added) == {("ext1", (10.0, 3.0)), ("ext1", (0.0, 3.0))}
        ext = out.model.boundary("ext1")
        assert (0.0, 3.0) in ext.vertices and (10.0, 3.0) in ext.vertices
        assert out.model.boundary("mat1").vertices == ((0.0, 3.0), (10.0, 3.0))
        done = replace(out.model, assignments=(md.Assignment((5.0, 1.0), "a", (False,)),
                                               md.Assignment((5.0, 6.0), "b", (False,))))
        assert md.problems(done) == []
        geo = regions.build(done)
        assert sorted(regions.region_area(geo, r) for r in range(len(geo.regions))) == [30.0, 70.0]
        # without the cuts, the same drawing meets the external away from its vertices
        assert "crossing" in {p.rule for p in md.problems(replace(m, assignments=done.assignments))}

    def test_two_lines_crossing(self):
        m = edit.add_boundary(_square(), md.MATERIAL, ((2.0, 5.0), (8.0, 4.0)))
        m = edit.add_boundary(m, md.MATERIAL, ((5.0, 1.0), (4.0, 9.0)))
        out = cuts.cut(m, "mat2")
        (b1, p), (b2, q) = out.added
        assert p == q and {b1, b2} == {"mat1", "mat2"}
        assert _on_line(p, (2.0, 5.0), (8.0, 4.0)) and _on_line(p, (5.0, 1.0), (4.0, 9.0))
        assert p in out.model.boundary("mat1").vertices and p in out.model.boundary("mat2").vertices

    def test_through_a_vertex_puts_only_the_t(self):
        m = edit.add_boundary(_square(), md.MATERIAL, ((2.0, 5.0), (5.0, 5.0), (8.0, 5.0)))
        m = edit.add_boundary(m, md.MATERIAL, ((5.0, 2.0), (5.0, 8.0)))
        out = cuts.cut(m, "mat2")
        assert out.added == (("mat2", (5.0, 5.0)),)
        assert out.model.boundary("mat1") == m.boundary("mat1")
        # ends on vertices of the external: nothing at all
        diag = edit.add_boundary(_square(), md.MATERIAL, ((0.0, 0.0), (10.0, 10.0)))
        assert cuts.cut(diag, "mat1") == cuts.Cut(diag, ())

    def test_meets_nothing(self):
        m = edit.add_boundary(_square(), md.MATERIAL, ((2.0, 2.0), (3.0, 3.0)))
        assert cuts.cut(m, "mat1") == cuts.Cut(m, ())


class TestArcs:
    def test_a_line_across_a_hole(self):
        m = edit.add_boundary(_models.tunnel(), md.STAGE, ((-10.0, 0.5), (10.0, 0.5)))
        out = cuts.cut(m, "stg1")
        hole = out.model.boundary("hole")
        new = [p for b, p in out.added if b == "hole"]
        assert len(new) == 2
        for p in new:
            assert _on_circle(p, (0.0, 0.0), 1.0) and abs(p[1] - 0.5) <= TOL
            assert p in out.model.boundary("stg1").vertices
        assert len(hole.vertices) == 6 and all(s.arc == (0.0, 0.0) for s in hole.segments)
        assert len(hole.segments) == 6
        assert {p for b, p in out.added if b == "ext"} == {(-10.0, 0.5), (10.0, 0.5)}

    def test_two_circles(self):
        # equal radii, and unequal (the chord of the meeting is not halfway)
        for cx, r in ((1.5, 1.0), (1.2, 0.5)):
            m = _models.tunnel()
            second = tuple((cx + x, y) for x, y in ((r, 0.0), (0.0, r), (-r, 0.0), (0.0, -r)))
            m = edit.add_boundary(m, md.EXCAVATION, second,
                                  segments=tuple(md.SegmentAttr(k, (cx, 0.0)) for k in range(4)))
            out = cuts.cut(m, "exc1")
            pts = {p for _, p in out.added}
            assert len(pts) == 2 and len(out.added) == 4
            x = (1.0 - r * r + cx * cx) / (2.0 * cx)
            for p in pts:
                assert _on_circle(p, (0.0, 0.0), 1.0) and _on_circle(p, (cx, 0.0), r)
                assert abs(p[0] - x) <= TOL
            for bid, centre in (("hole", (0.0, 0.0)), ("exc1", (cx, 0.0))):
                assert all(s.arc == centre for s in out.model.boundary(bid).segments)


class TestRefused:
    def test_a_stretch_in_common(self):
        m = edit.add_boundary(_square(), md.MATERIAL, ((2.0, 0.0), (6.0, 0.0)))
        _refused(lambda: cuts.cut(m, "mat1"), "overlap", "'mat1'", "'ext1'")
        arc = edit.add_boundary(_models.tunnel(), md.MATERIAL, ((1.0, 0.0), (0.6, 0.8)),
                                segments=(md.SegmentAttr(0, (0.0, 0.0)),))
        _refused(lambda: cuts.cut(arc, "mat1"), "overlap", "'hole'")

    def test_the_same_side_is_not_a_stretch_in_common(self):
        m = edit.add_boundary(_square(), md.MATERIAL, ((0.0, 0.0), (10.0, 0.0)))
        assert cuts.cut(m, "mat1") == cuts.Cut(m, ())

    def test_a_divided_side_is_not_split(self):
        m = edit.set_divisions(_square(), "ext1", 3, 12)
        m = edit.add_boundary(m, md.MATERIAL, ((0.0, 3.0), (10.0, 3.0)))
        _refused(lambda: cuts.cut(m, "mat1"), "divisions_vertex", "'ext1'", "12 forced")
