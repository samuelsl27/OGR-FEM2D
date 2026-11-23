# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.9 (spec 004, T5; a finding in the mesher of spec 003) — a hole filled
by several regions is not a void.

The PSLG took for a void (a hole no region fills, where the core meshes
nothing) every hole whose ring was not the outline of one region. An
excavation split in two by a stage boundary (top heading and bench) fills
the hole of the rock with two regions, and the core then refused the seed of
one of them as "in a void". A hole is now a void when it holds no seed.

Invariants protected:

* **a hole filled by two regions is meshed**, with arcs and without them:
  every region gets elements, and the elements of each cover its area, to
  the difference between the parabolic sides of the six-node triangles and
  the circle (1e-7 of the model's area);
* **a hole that nothing fills is still a void**: no element inside it;
* **a hole filled by one region** is meshed as before.
"""
from __future__ import annotations

import math

from ogr_fem2d.mesh import geometry as g
from ogr_fem2d.mesh import mesher

O = g.Arc((0.0, 0.0))
PTS = ((-10.0, -10.0), (10.0, -10.0), (10.0, 10.0), (-10.0, 10.0),
       (1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0))
ARCS = tuple(g.SegmentSpec(a, b, arc=O, excavation=True) for a, b in ((4, 5), (5, 6), (6, 7), (7, 4)))
ROCK = g.Region((0, 1, 2, 3), holes=((4, 7, 6, 5),), material=0)


def _shoelace_t6(xy):
    # the area of a quadratic triangle: the integral of x dy round its three
    # parabolic sides, each exact by Simpson's rule
    total = 0.0
    for a, m, b in ((0, 3, 1), (1, 4, 2), (2, 5, 0)):
        (x0, y0), (x1, y1), (x2, y2) = xy[a], xy[m], xy[b]
        # x(t), y(t) quadratic through the three nodes, t in [0, 1]; x y' is cubic
        def f(t):
            l0, l1, l2 = (1 - t) * (1 - 2 * t), 4 * t * (1 - t), t * (2 * t - 1)
            d0, d1, d2 = 4 * t - 3, 4 - 8 * t, 4 * t - 1
            return (x0 * l0 + x1 * l1 + x2 * l2) * (y0 * d0 + y1 * d1 + y2 * d2)
        total += (f(0.0) + 4.0 * f(0.5) + f(1.0)) / 6.0
    return total


def _mesh(regions, segs=ARCS, pts=PTS):
    return mesher.mesh(g.MeshInput("plane_strain", pts, regions, segs,
                                   g.MeshSettings(boundary_nodes=48)))


class TestASplitHole:
    def test_two_halves_of_a_circle(self):
        regions = (ROCK, g.Region((4, 5, 6), material=1), g.Region((4, 6, 7), material=2))
        mesh = _mesh(regions)
        m = g.MeshInput("plane_strain", PTS, regions, ARCS, g.MeshSettings(boundary_nodes=48))
        for r in range(3):
            got = sum(_shoelace_t6([mesh.nodes[n] for n in el])
                      for el, rr in zip(mesh.elements, mesh.element_region) if rr == r)
            want = g.region_area(m, r)
            assert abs(got - want) < 1e-7 * 400.0, (r, got, want)

    def test_two_halves_of_a_square(self):
        pts = ((-10.0, -10.0), (10.0, -10.0), (10.0, 10.0), (-10.0, 10.0), (1.0, -1.0), (1.0, 0.0),
               (1.0, 1.0), (-1.0, 1.0), (-1.0, 0.0), (-1.0, -1.0))
        rock = g.Region((0, 1, 2, 3), holes=((4, 9, 8, 7, 6, 5),), material=0)
        regions = (rock, g.Region((5, 6, 7, 8), material=1), g.Region((4, 5, 8, 9), material=2))
        segs = tuple(g.SegmentSpec(a, b, excavation=True)
                     for a, b in ((4, 5), (5, 6), (6, 7), (7, 8), (8, 9), (9, 4)))
        mesh = _mesh(regions, segs, pts)
        assert {r: sum(1 for x in mesh.element_region if x == r) > 0 for r in range(3)} == {
            0: True, 1: True, 2: True}

    def test_an_empty_hole_is_still_a_void(self):
        mesh = _mesh((ROCK,))
        for el in mesh.elements:
            cx = sum(mesh.nodes[n][0] for n in el[:3]) / 3.0
            cy = sum(mesh.nodes[n][1] for n in el[:3]) / 3.0
            assert math.hypot(cx, cy) > 0.9

    def test_a_hole_filled_by_one_region(self):
        mesh = _mesh((ROCK, g.Region((4, 5, 6, 7), material=1)))
        assert sum(1 for r in mesh.element_region if r == 1) > 0
