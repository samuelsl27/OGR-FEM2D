# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.8 (spec 003, T11-T12, the parts that do not wait for the core) — what
FEM2D hands to the quality triangulation (ogr_fem2d/mesh/pslg.py) and the
size bound (ogr_fem2d/mesh/sizing.py).

Invariants protected:

* **the PSLG is the discretization**: its vertices are the nodes of step 1;
  its segments are the pieces between consecutive nodes, each labelled with
  the segment it belongs to, so the pieces of an arc keep the arc's centre;
* **a seed strictly inside each region**: in the rock and not in the
  excavation, in the excavation, in each layer of a slope, in a square
  dented by an arc, and in a sliver a thousandth of its length thick,
  checked with plain geometry (the circle, the layer heights), with its
  material; a hole nobody fills gets a point inside it, one that a region
  fills does not;
* **D13**: on a mesh whose generator put nodes on the chords of a circle
  (the core's generator does), the vertices strictly inside a chord go
  radially onto the circle, the chord ends stay, the moved ones are named,
  and the six-node mesh made with the pieces as arcs is still one to one;
* **the size bound** (Shewchuk 2002a, p. 11): the global one (h of a uniform
  mesh, max_size of a graded one, none) and, inside a window of either
  orientation or on its outline, the smaller of the two; overlapping windows
  give the smallest; its floor is positive.
"""
from __future__ import annotations

import math
from dataclasses import replace

from ogr_core.fem.generator import generate_mesh
from ogr_core.geometry.regions import MaterialRegion

from ogr_fem2d.mesh import checks, discretize, geometry as g, pslg, quadratic as q, sizing
from test_mesh_input_v008 import DENT, ROCK, SLOPE, TUNNEL
from test_mesh_quadratic_v008 import _ring


class TestThePSLG:
    def test_it_is_the_discretization(self):
        disc = discretize.discretize(TUNNEL)
        p = pslg.build(TUNNEL, disc)
        assert p.vertices == disc.points
        assert len(p.segments) == sum(ds.divisions for ds in disc.segments)
        segs = g.segments(TUNNEL)
        for ds in disc.segments:
            label = segs.index(ds.segment)
            mine = [(u, v) for u, v, lab in p.segments if lab == label]
            assert mine == list(zip(ds.nodes, ds.nodes[1:]))
        assert p.arcs == {4: (0.0, 0.0), 5: (0.0, 0.0), 6: (0.0, 0.0), 7: (0.0, 0.0)}

    def test_a_ring_is_a_closed_chain_of_pieces_in_its_direction(self):
        # the excavation's outline runs its arcs the other way round from the
        # rock's hole, which met them first
        disc = discretize.discretize(TUNNEL)
        pieces = {(u, v) for u, v, _lab in pslg.build(TUNNEL, disc).segments}
        for ring in (TUNNEL.regions[0].outline, TUNNEL.regions[0].holes[0],
                     TUNNEL.regions[1].outline):
            chain = pslg._ring_chain(TUNNEL, disc, ring)
            assert chain[0] == ring[0]
            for u, v in zip(chain, chain[1:] + chain[:1]):
                assert (u, v) in pieces or (v, u) in pieces, (ring, u, v)
            # and in the ring's direction: same sign of area as the ring
            pts = disc.points
            area = sum(pts[chain[k]][0] * pts[chain[(k + 1) % len(chain)]][1]
                       - pts[chain[(k + 1) % len(chain)]][0] * pts[chain[k]][1]
                       for k in range(len(chain)))
            ring_area = sum(pts[ring[k]][0] * pts[ring[(k + 1) % len(ring)]][1]
                            - pts[ring[(k + 1) % len(ring)]][0] * pts[ring[k]][1]
                            for k in range(len(ring)))
            assert area * ring_area > 0


class TestSeeds:
    def test_inside_each_region_with_its_material(self):
        p = pslg.build(TUNNEL, discretize.discretize(TUNNEL))
        (rock, r0, m0), (exc, r1, m1) = p.seeds
        assert (r0, m0, r1, m1) == (0, 0, 1, 1)
        assert math.hypot(*rock) > 1.0 and max(abs(rock[0]), abs(rock[1])) < 10.0
        assert math.hypot(*exc) < math.cos(math.pi / 20)    # inside the 40-gon of the chords
        assert p.voids == ()

    def test_layers_a_dent_and_a_sliver(self):
        (low, _, _), (up, _, _) = pslg.build(SLOPE, discretize.discretize(SLOPE)).seeds
        assert 0.0 < low[1] < 10.0 and 10.0 < up[1] < 20.0
        (dent, _, _), = pslg.build(DENT, discretize.discretize(DENT)).seeds
        assert g._inside_region(dent, DENT.regions[0], DENT.points, g._arcs(DENT))
        sliver = g.MeshInput("plane_strain", ((0.0, 0.0), (10.0, 0.0), (10.0, 1e-3), (0.0, 1e-3)),
                             (g.Region((0, 1, 2, 3)),), (), g.MeshSettings(boundary_nodes=4))
        (s, _, _), = pslg.build(sliver, discretize.discretize(sliver)).seeds
        assert 0.0 < s[0] < 10.0 and 0.0 < s[1] < 1e-3

    def test_a_void_gets_a_point_a_filled_hole_does_not(self):
        void = replace(TUNNEL, regions=(ROCK,))
        p = pslg.build(void, discretize.discretize(void))
        assert len(p.voids) == 1 and math.hypot(*p.voids[0]) < 1.0
        assert len(p.seeds) == 1


def _polygon_hole_mesh(n: int = 8, h: float = 0.1):
    """The core's generator on a 6 m square with a hole of n chords of the
    unit circle: it puts nodes on the chords."""
    octagon = [(math.cos(2 * math.pi * k / n), math.sin(2 * math.pi * k / n)) for k in range(n)]
    # the zeros of the axes exact (cos(pi/2) is 6e-17); the rest unrounded
    octagon = [(0.0 if abs(x) < 1e-15 else x, 0.0 if abs(y) < 1e-15 else y) for x, y in octagon]
    rock = MaterialRegion(polygon=_ring([(-3, -3), (3, -3), (3, 3), (-3, 3)]),
                          material_id="rock", holes=[_ring(octagon, ccw=False)])
    mesh = generate_mesh([rock], target_size=h)
    nodes = [(p.x, p.y) for p in mesh.nodes]
    tris = [e.nodes for e in mesh.elements]
    ends = [min(range(len(nodes)), key=lambda i: math.dist(nodes[i], v)) for v in octagon]
    chains = []
    for k in range(n):
        a, b = nodes[ends[k]], nodes[ends[(k + 1) % n]]
        on = [i for i, p in enumerate(nodes)
              if abs((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])) < 1e-12
              and min(a[0], b[0]) - 1e-12 <= p[0] <= max(a[0], b[0]) + 1e-12
              and min(a[1], b[1]) - 1e-12 <= p[1] <= max(a[1], b[1]) + 1e-12]
        on.sort(key=lambda i: math.dist(nodes[i], a))
        chains.append(on)
    return nodes, tris, chains


class TestD13:
    def test_the_vertices_on_the_chords_go_onto_the_circle(self):
        nodes, tris, chains = _polygon_hole_mesh(8, 0.1)
        inner = [v for c in chains for v in c[1:-1]]
        assert len(inner) > 40                         # the generator did put nodes on them
        moved_points, moved = pslg.onto_arcs(nodes, {0: chains}, {0: (0.0, 0.0)})
        assert moved == tuple(sorted(inner))
        for c in chains:
            for v in c:
                assert abs(math.hypot(*moved_points[v]) - 1.0) <= 4e-16, v
            assert moved_points[c[0]] == nodes[c[0]] and moved_points[c[-1]] == nodes[c[-1]]
        untouched = set(range(len(nodes))) - set(inner)
        assert all(moved_points[i] == nodes[i] for i in untouched)

    def test_a_sagitta_near_the_element_size_folds_elements_and_is_caught(self):
        # FOUND in T12 (changelog v0.0.8): moving the vertices of a chord out to
        # its arc by up to the sagitta, 1 - cos(22.5 deg) = 0.076 for 8 chords,
        # turns over the thin elements against the chord when the elements
        # are about that size (h = 0.1); RF-13 refuses the mesh. With 16
        # chords (sagitta 0.019) the same h gives a valid mesh, three- and
        # six-node. What to do about it is the owner's decision (D14).
        for n, folded in ((8, True), (16, False)):
            nodes, tris, chains = _polygon_hole_mesh(n, 0.1)
            moved_points, moved = pslg.onto_arcs(nodes, {0: chains}, {0: (0.0, 0.0)})
            assert moved
            arcs = {q.edge_key(u, v): (0.0, 0.0) for c in chains for u, v in zip(c, c[1:])}
            quad = q.promote(moved_points, tris, arcs)
            bad3 = checks.element_problems(moved_points, tris, "plane_strain")
            bad6 = checks.element_problems(quad.nodes, quad.elements, "plane_strain")
            assert bool(bad3) == folded and bool(bad6) == folded, (n, len(bad3), len(bad6))


class TestSizeBound:
    def test_global_windows_and_floor(self):
        square = ((-2.0, -2.0), (2.0, -2.0), (2.0, 2.0), (-2.0, 2.0))
        cw = tuple(reversed(((1.0, 1.0), (3.0, 1.0), (3.0, 3.0), (1.0, 3.0))))
        uniform = replace(TUNNEL, settings=replace(
            TUNNEL.settings, kind="uniform", boundary_nodes=None, size=0.5,
            windows=(g.Window(square, 0.1), g.Window(cw, 0.05))))
        b = sizing.size_bound(uniform)
        assert b(8.0, 8.0) == 0.5 and b(0.0, 0.0) == 0.1 and b(1.5, 1.5) == 0.05
        # on a window's outline, every side (the crossing rule alone would leave
        # the right and top sides out)
        for x, y in ((-2.0, 0.0), (2.0, 0.0), (0.0, 2.0), (0.0, -2.0), (2.0, 2.0)):
            assert b(x, y) <= 0.1, (x, y)
        assert b(2.5, 2.5) == 0.05 and b.floor == 0.05
        graded = replace(TUNNEL, settings=replace(TUNNEL.settings, windows=(g.Window(square, 0.1),)))
        gb = sizing.size_bound(graded)
        assert gb(8.0, 8.0) == math.inf and gb(0.0, 0.0) == 0.1 and gb.floor == 0.1
        capped = sizing.size_bound(replace(TUNNEL, settings=replace(TUNNEL.settings, max_size=2.0)))
        assert capped(8.0, 8.0) == 2.0 and sizing.size_bound(TUNNEL).floor is None
        by_n = sizing.size_bound(replace(TUNNEL, settings=replace(
            TUNNEL.settings, kind="uniform", boundary_nodes=None, elements=500)))
        assert math.isclose(by_n(0.0, 0.0), math.sqrt(4 * 400.0 / (math.sqrt(3) * 500)),
                            rel_tol=1e-14)


class TestWindowCorners:
    """D9 with the core's evaluation of the size bound (2026-11-23): the
    corners of a window inside the domain are loose vertices of the PSLG."""

    def test_inside_in_outside_on_a_segment_or_repeated_out(self):
        windows = (
            g.Window(((5.0, 5.0), (5.4, 5.0), (5.4, 5.4), (5.0, 5.4)), 0.05),   # all inside
            g.Window(((8.0, 8.0), (12.0, 8.0), (12.0, 12.0), (8.0, 12.0)), 0.5),  # half out
            g.Window(((-10.0, 0.0), (-9.0, 0.0), (-9.0, 1.0)), 0.5),              # one on the side
            g.Window(((5.0, 5.0), (5.4, 5.0), (5.2, 5.6)), 0.05),                 # repeats two
            g.Window(((0.0, 0.0), (0.2, 0.0), (0.0, 0.2)), 0.05),                 # in the excavation
        )
        m = replace(TUNNEL, settings=replace(TUNNEL.settings, windows=windows))
        disc = discretize.discretize(m)
        p = pslg.build(m, disc)
        extra = p.vertices[len(disc.points):]
        assert extra == ((5.0, 5.0), (5.4, 5.0), (5.4, 5.4), (5.0, 5.4), (8.0, 8.0),
                         (-9.0, 0.0), (-9.0, 1.0), (5.2, 5.6), (0.0, 0.0), (0.2, 0.0),
                         (0.0, 0.2)), extra

    def test_no_window_no_extra_vertex(self):
        disc = discretize.discretize(TUNNEL)
        assert pslg.build(TUNNEL, disc).vertices == disc.points
