# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.1 (spec 001, T6) — the radial mesh of six-node triangles covers the
quarter annulus it says, with its curved edges where the circles are, and no
element is degenerate.

Invariants protected, for the two outer radii of the spec (21 m and 100 m,
D3 bis):

* **area, exactly**: the area of the mesh integrated element by element with
  the quadrature of the T6 (the integrand det J is of degree 2 in the area
  coordinates, so the rule of Table 9.2 integrates it exactly) equals, to
  rounding, the area of the region its boundary encloses. That region is the
  quarter annulus with every arc replaced by the parabola through the three
  nodes of its edge, and its area is closed-form: by Archimedes' quadrature
  of the parabola, the parabolic segment over a chord is 4/3 of the triangle
  of the chord and the point whose tangent is parallel to it, which for the
  quadratic edge is its mid-side node. Against the circular segment
  R^2 (alpha - sin alpha)/2 this gives the exact gap to pi (b^2 - a^2)/4. A
  mid-side node off the circle, or an element missing or counted twice,
  breaks it;
* **the circles are followed**: that gap falls as dtheta^4 (16 times per
  halving of dtheta), the order of a parabola through three points of an arc;
* **no degenerate element**: det J > 0 at the six nodes and the three
  integration points of every element (det J is quadratic, these are the
  points the engine evaluates), and the B matrix builds;
* **the boundary sets**: hole nodes at r = a and outer ones at r = b to
  rounding; the axis nodes EXACTLY on the axes (the rollers act there); the
  sets in the order the docstring says;
* **conformity**: every interior edge is shared by exactly two elements
  with the same three nodes, every boundary edge belongs to one element and
  lies on one of the four boundaries, and every node is used;
* **grading**: dr_(i+1) / dr_i = growth, r_0 = a and r_n = b.
"""
from __future__ import annotations

import math
from collections import Counter

from ogr_fem2d.engine.mesh_radial import graded_radii, quarter_annulus
from ogr_fem2d.engine.reference import element_t6 as t6

A = 1.0
MESHES = [(21.0, 8, 4, 1.25), (100.0, 14, 6, 1.3), (21.0, 3, 1, 1.0)]


def _xy(mesh, element):
    return [mesh.nodes[n] for n in element]


def _archimedes_area(a, b, n_theta):
    """Area enclosed by the mesh boundary, in closed form (see the header)."""
    alpha = 0.5 * math.pi / n_theta

    def parabolic_minus_circular(r):
        triangle = r * r * math.sin(alpha / 2) * (1.0 - math.cos(alpha / 2))
        return 4.0 / 3.0 * triangle - 0.5 * r * r * (alpha - math.sin(alpha))

    # The outer arc bounds the region from outside (its segments add), the
    # hole from inside (they subtract).
    return (0.25 * math.pi * (b * b - a * a)
            + n_theta * (parabolic_minus_circular(b)
                         - parabolic_minus_circular(a)))


def _quadrature_area(mesh):
    return sum(t6.area(_xy(mesh, e)) for e in mesh.elements)


class TestArea:
    def test_the_quadrature_gives_the_area_of_the_boundary(self):
        for b, nr, nt, growth in MESHES:
            mesh = quarter_annulus(A, b, nr, nt, growth)
            got, want = _quadrature_area(mesh), _archimedes_area(A, b, nt)
            assert abs(got - want) < 1e-13 * want, (b, nt, got, want)

    def test_the_gap_to_the_annulus_falls_as_dtheta_to_the_fourth(self):
        for b in (21.0, 100.0):
            exact = 0.25 * math.pi * (b * b - A * A)
            gaps = [exact - _quadrature_area(quarter_annulus(A, b, 4, nt, 1.2))
                    for nt in (2, 4, 8)]
            for coarse, fine in zip(gaps, gaps[1:]):
                order = math.log2(coarse / fine)
                assert 3.9 < order < 4.1, (b, gaps)


class TestElements:
    def test_no_element_is_degenerate(self):
        points = list(t6.NODES_L) + [l for l, _ in t6.GAUSS_POINTS]
        for b, nr, nt, growth in MESHES:
            mesh = quarter_annulus(A, b, nr, nt, growth)
            for number, element in enumerate(mesh.elements):
                xy = _xy(mesh, element)
                for l in points:
                    assert t6.jacobian(xy, *l)[1] > 0.0, (b, number, l)
                for l, _ in t6.GAUSS_POINTS:
                    t6.b_matrix(xy, *l)          # raises if det J <= 0

    def test_the_mesh_is_conforming_and_uses_every_node(self):
        for b, nr, nt, growth in MESHES:
            mesh = quarter_annulus(A, b, nr, nt, growth)
            edges = Counter()
            for e in mesh.elements:
                for c1, c2, m in ((e[0], e[1], e[3]), (e[1], e[2], e[4]),
                                  (e[2], e[0], e[5])):
                    edges[(min(c1, c2), max(c1, c2), m)] += 1
            # same corners always with the same mid-side node
            assert len({k[:2] for k in edges}) == len(edges)
            boundary = {k for k, n in edges.items() if n == 1}
            assert all(n in (1, 2) for n in edges.values())
            sets = [set(mesh.hole), set(mesh.outer), set(mesh.x_axis),
                    set(mesh.y_axis)]
            for edge in boundary:
                assert any(set(edge) <= s for s in sets), edge
            # boundary edges: n_theta on each arc, n_radial on each axis
            assert len(boundary) == 2 * nt + 2 * nr
            used = {n for e in mesh.elements for n in e}
            assert used == set(range(len(mesh.nodes)))
            assert len(mesh.nodes) == (2 * nr + 1) * (2 * nt + 1)
            assert len(mesh.elements) == 2 * nr * nt


class TestBoundarySets:
    def test_nodes_on_the_circles_and_on_the_axes(self):
        for b, nr, nt, growth in MESHES:
            mesh = quarter_annulus(A, b, nr, nt, growth)
            for n in mesh.hole:
                assert abs(math.hypot(*mesh.nodes[n]) - A) < 1e-15
            for n in mesh.outer:
                assert abs(math.hypot(*mesh.nodes[n]) - b) < 1e-13 * b
            assert all(mesh.nodes[n][1] == 0.0 for n in mesh.x_axis)
            assert all(mesh.nodes[n][0] == 0.0 for n in mesh.y_axis)
            # orders: theta increasing on the arcs, r increasing on the axes
            angles = [math.atan2(mesh.nodes[n][1], mesh.nodes[n][0])
                      for n in mesh.hole]
            assert angles == sorted(angles) and len(angles) == 2 * nt + 1
            xs = [mesh.nodes[n][0] for n in mesh.x_axis]
            ys = [mesh.nodes[n][1] for n in mesh.y_axis]
            assert xs == sorted(xs) and ys == sorted(ys)
            assert xs[0] == A and ys[-1] == b

    def test_every_mid_side_node_is_the_polar_mean_of_its_corners(self):
        # The construction: each node is the image of its (r, theta) point,
        # and in (r, theta) every element is straight, so the mid-side node
        # has the mean r and the mean theta of its two corners. On the arcs
        # that is the circle; on the radial edges, the middle of the segment.
        for b, nr, nt, growth in MESHES:
            mesh = quarter_annulus(A, b, nr, nt, growth)
            polar = [(math.hypot(x, y), math.atan2(y, x)) for x, y in mesh.nodes]
            for e in mesh.elements:
                for c1, c2, m in ((e[0], e[1], e[3]), (e[1], e[2], e[4]),
                                  (e[2], e[0], e[5])):
                    r_mean = 0.5 * (polar[c1][0] + polar[c2][0])
                    t_mean = 0.5 * (polar[c1][1] + polar[c2][1])
                    assert abs(polar[m][0] - r_mean) < 1e-13 * b, (b, e)
                    assert abs(polar[m][1] - t_mean) < 1e-14, (b, e)


class TestGrading:
    def test_geometric_growth_between_a_and_b(self):
        for growth in (1.0, 1.15, 1.4, 0.9):
            r = graded_radii(A, 100.0, 12, growth)
            assert r[0] == A and r[-1] == 100.0 and len(r) == 13
            sizes = [r2 - r1 for r1, r2 in zip(r, r[1:])]
            for s1, s2 in zip(sizes, sizes[1:]):
                assert abs(s2 / s1 - growth) < 1e-10, (growth, s1, s2)

    def test_bad_parameters_are_refused(self):
        for args in ((A, A, 3, 1.0), (A, 21.0, 0, 1.0), (A, 21.0, 3, 0.0),
                     (0.0, 21.0, 3, 1.0)):
            try:
                graded_radii(*args)
            except ValueError:
                continue
            raise AssertionError(f"accepted {args}")
