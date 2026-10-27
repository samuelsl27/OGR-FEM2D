# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.2 (spec 002, T10) — the structured test meshes: the graded rectangle
(mesh_structured.py) and the quarter annulus of three-node triangles
(mesh_radial.py).

Identities, no source needed:

* **grading**: the lines start and end where asked and consecutive gaps
  grow by the factor given, upwards or downwards;
* **the rectangle is covered exactly once**: the areas of the elements add
  up to its area (exact quadrature on straight sides), every element is
  anticlockwise with det J > 0 at its nodes and integration points, every
  inner side is shared by exactly two elements with the same mid-side node
  (a conforming mesh) and every other side lies on the boundary; every node
  is used; a mid-side node is the midpoint of its straight side (off it, the
  area and a linear field would still come out exact, and the element
  would be distorted for everything else);
* **the boundary**: the node lists of each side are its nodes, in order;
  the element sides listed on a side lie on it, in order, and add up to
  its length;
* **diagonals**: "up" and "down" cut every cell one way, "alternate" in a
  checkerboard;
* **through the analysis**: a graded block, alternate diagonals, pulled on
  its top through the listed sides by a uniform traction ends in the exact
  uniform stress, with three and six nodes;
* **the quarter annulus of three-node triangles** has the nodes of the
  six-node one and four times its elements, each anticlockwise and
  conforming; its area is that of the polygons through corners and
  mid-side nodes of the six-node mesh, and its gap to the annulus falls as
  dtheta^2 (chords instead of arcs).
"""
from __future__ import annotations

import math

from ogr_fem2d.engine import analysis
from ogr_fem2d.engine import model as m
from ogr_fem2d.engine.mesh_radial import quarter_annulus
from ogr_fem2d.engine.mesh_structured import graded, rectangle
from ogr_fem2d.engine.reference import element_t3 as t3
from ogr_fem2d.engine.reference import element_t6 as t6
from ogr_fem2d.engine.reference import quadrature as q
from ogr_fem2d.engine.reference import triangle
from ogr_fem2d.engine.reference.elastic import Elastic

XS = graded(0.0, 1.0, 3, 1.0) + graded(1.0, 5.0, 4, 1.4)[1:]
YS = graded(-3.0, 0.0, 4, 0.7)


def meshes():
    for n in (3, 6):
        for diagonal in ("up", "down", "alternate"):
            yield n, diagonal, rectangle(XS, YS, n, diagonal)


def shape_of(n):
    return t3 if n == 3 else t6


def corner_area(xy):
    (x1, y1), (x2, y2), (x3, y3) = xy[:3]
    return 0.5 * ((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))


class TestGrading:

    def test_ends_and_ratios(self):
        for start, end, n, growth in ((0.0, 1.0, 5, 1.3), (5.0, 1.0, 4, 0.8), (-3.0, 0.0, 1, 2.0)):
            lines = graded(start, end, n, growth)
            assert lines[0] == start and lines[-1] == end and len(lines) == n + 1
            gaps = [b - a for a, b in zip(lines, lines[1:])]
            for g1, g2 in zip(gaps, gaps[1:]):
                assert abs(g2 / g1 - growth) < 1e-12

    def test_bad_arguments(self):
        for args in ((0.0, 1.0, 0, 1.0), (0.0, 1.0, 3, 0.0), (1.0, 1.0, 3, 1.0)):
            try:
                graded(*args)
            except ValueError:
                continue
            raise AssertionError(f"graded{args} accepted")
        for args in (([0.0, 1.0], [0.0, 1.0], 4, "up"), ([0.0, 1.0], [0.0, 1.0], 3, "x"),
                     ([0.0, 1.0, 0.5], [0.0, 1.0], 3, "up")):
            try:
                rectangle(*args)
            except ValueError:
                continue
            raise AssertionError(f"rectangle{args} accepted")


class TestRectangle:

    def test_the_area_and_the_jacobians(self):
        width, height = XS[-1] - XS[0], YS[-1] - YS[0]
        for n, diagonal, mesh in meshes():
            shape = shape_of(n)
            rule = q.rule_for(n, q.PLANE_STRAIN)
            total = 0.0
            for element in mesh.elements:
                xy = [mesh.nodes[k] for k in element]
                assert corner_area(xy) > 0.0
                total += triangle.area(shape, xy, rule)
                for l in list(shape.NODES_L) + [p for p, _ in rule.points]:
                    assert triangle.jacobian(shape, xy, *l)[1] > 0.0
            assert abs(total - width * height) < 1e-13 * width * height, (n, diagonal)

    def test_it_is_conforming(self):
        for n, diagonal, mesh in meshes():
            sides = {}
            for element in mesh.elements:
                for k in range(3):
                    key = tuple(sorted((element[k], element[(k + 1) % 3])))
                    mid = element[k + 3] if n == 6 else None
                    sides.setdefault(key, []).append(mid)
            on_boundary = lambda p: (p[0] in (XS[0], XS[-1])) or (p[1] in (YS[0], YS[-1]))
            for (i, j), mids in sides.items():
                if len(mids) == 1:
                    pi, pj = mesh.nodes[i], mesh.nodes[j]
                    assert on_boundary(pi) and on_boundary(pj) and (
                        pi[0] == pj[0] in (XS[0], XS[-1]) or pi[1] == pj[1] in (YS[0], YS[-1]))
                else:
                    assert len(mids) == 2 and mids[0] == mids[1], (n, diagonal, (i, j), mids)
            if n == 6:                 # mid-side nodes in the middle of straight sides
                for element in mesh.elements:
                    for k in range(3):
                        a, b = mesh.nodes[element[k]], mesh.nodes[element[(k + 1) % 3]]
                        mid = mesh.nodes[element[k + 3]]
                        assert max(abs(mid[0] - (a[0] + b[0]) / 2),
                                   abs(mid[1] - (a[1] + b[1]) / 2)) < 1e-15
            used = {k for element in mesh.elements for k in element}
            assert used == set(range(len(mesh.nodes)))
            factor = 2 if n == 6 else 1
            assert len(mesh.nodes) == (factor * (len(XS) - 1) + 1) * (factor * (len(YS) - 1) + 1)

    def test_the_boundary(self):
        lengths = {"left": YS[-1] - YS[0], "right": YS[-1] - YS[0],
                   "bottom": XS[-1] - XS[0], "top": XS[-1] - XS[0]}
        coordinate = {"left": (0, XS[0]), "right": (0, XS[-1]),
                      "bottom": (1, YS[0]), "top": (1, YS[-1])}
        for n, _, mesh in meshes():
            for name, (axis, value) in coordinate.items():
                nodes = mesh.boundary[name]
                assert set(nodes) == {k for k, p in enumerate(mesh.nodes) if p[axis] == value}
                along = [mesh.nodes[k][1 - axis] for k in nodes]
                assert along == sorted(along)
                total, last = 0.0, -math.inf
                for e, side in mesh.boundary_sides[name]:
                    a = mesh.nodes[mesh.elements[e][side]]
                    b = mesh.nodes[mesh.elements[e][(side + 1) % 3]]
                    assert a[axis] == b[axis] == value
                    assert min(a[1 - axis], b[1 - axis]) > last
                    last = min(a[1 - axis], b[1 - axis])
                    total += math.dist(a, b)
                assert abs(total - lengths[name]) < 1e-13, (n, name)

    def test_the_diagonals(self):
        def leans(mesh, cell):
            """'up' or 'down' for the first triangle of cell number ``cell``."""
            a, b, c = (mesh.nodes[k] for k in mesh.elements[2 * cell][:3])
            # up: (bottom-left, bottom-right, top-right); down: (bl, br, top-left)
            return "up" if c[0] == b[0] else "down"
        for n in (3, 6):
            assert {leans(rectangle(XS, YS, n, "up"), c) for c in range(4)} == {"up"}
            assert {leans(rectangle(XS, YS, n, "down"), c) for c in range(4)} == {"down"}
            alt = rectangle(XS, YS, n, "alternate")
            assert [leans(alt, c) for c in range(3)] == ["up", "down", "up"]
            row = len(XS) - 1                       # first cell of the second row:
            assert leans(alt, row) == "down"        # (0 + 1) odd, whatever the row length


class TestThroughTheAnalysis:

    def test_a_pulled_graded_block(self):
        E, NU, t = 20000.0, 0.2, 1.5
        for n in (3, 6):
            mesh = rectangle(XS, YS, n, "alternate")
            restraints = ([m.Restraint(k, True, k == mesh.boundary["bottom"][0])
                           for k in mesh.boundary["left"]]
                          + [m.Restraint(k, False, True) for k in mesh.boundary["bottom"][1:]])
            pull = tuple(m.EdgeLoad(e, side, (0.0, t), (0.0, t))
                         for e, side in mesh.boundary_sides["top"])
            stage = m.Stage(active=(True,) * len(mesh.elements), restraints=tuple(restraints),
                            edge_loads=pull, tolerance=1e-12)
            model = m.EngineModel(m.PLANE_STRAIN, tuple(mesh.nodes), tuple(mesh.elements),
                                  (m.Material(Elastic(E, NU)),), (0,) * len(mesh.elements),
                                  (stage,))
            out = analysis.run(model)[0]
            for s in out.stresses:
                assert abs(s[1] - t) < 1e-11 and abs(s[0]) < 1e-11 and abs(s[3]) < 1e-11, (n, s)


class TestQuarterAnnulusOfThreeNodes:

    def test_same_nodes_four_times_the_elements(self):
        six = quarter_annulus(1.0, 3.0, 4, 3, 1.2)
        three = quarter_annulus(1.0, 3.0, 4, 3, 1.2, nodes_per_element=3)
        assert three.nodes == six.nodes and len(three.elements) == 4 * len(six.elements)
        assert all(len(e) == 3 for e in three.elements)
        assert all(corner_area([three.nodes[k] for k in e]) > 0.0 for e in three.elements)
        assert {k for e in three.elements for k in e} == set(range(len(three.nodes)))
        sides = {}
        for e in three.elements:
            for k in range(3):
                sides.setdefault(tuple(sorted((e[k], e[(k + 1) % 3]))), []).append(e)
        assert all(len(v) <= 2 for v in sides.values())
        # the area: the polygons through the corners and mid-side nodes
        hexagons = 0.0
        for n1, n2, n3, n4, n5, n6 in six.elements:
            ring = [six.nodes[k] for k in (n1, n4, n2, n5, n3, n6)]
            hexagons += 0.5 * sum(x1 * y2 - x2 * y1
                                  for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]))
        total = sum(corner_area([three.nodes[k] for k in e]) for e in three.elements)
        assert abs(total - hexagons) < 1e-13

    def test_the_gap_to_the_annulus_falls_as_dtheta_squared(self):
        exact = math.pi / 4 * (3.0 ** 2 - 1.0 ** 2)
        gaps = []
        for n_theta in (4, 8, 16):
            mesh = quarter_annulus(1.0, 3.0, 2, n_theta, 1.0, nodes_per_element=3)
            gaps.append(exact - sum(corner_area([mesh.nodes[k] for k in e])
                                    for e in mesh.elements))
        assert all(g > 0 for g in gaps)
        for g1, g2 in zip(gaps, gaps[1:]):
            assert 3.9 < g1 / g2 < 4.1, gaps
