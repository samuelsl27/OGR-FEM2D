# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.8 (spec 003, T11 and T13) — the core's quality triangulation
(``ogr_core.fem.refine``, OGR-Core 0.2.5, asked for in D2; with arcs since
0.2.6, D14) fed with FEM2D's PSLG, checked from FEM2D against the sources.

Written while the pin was 0.2.3, against the core's tree with ``--dev-core``
(they then returned at once, and a test made sure that could not outlive the
pin); since the pin is 0.2.5 (v0.0.8, T14) they run in every run, and the
guard is gone. The pin is 0.2.6 since the same day.

Invariants protected (Shewchuk 2002a; pages of the preprint):

* **the size bound** (§3.1, p. 11; T11): with a uniform h, and with a graded
  mesh's max_size, no side is longer than the bound; a window (D9), whose
  corners enter as loose vertices, gets triangles no longer than its size,
  and the corners are what makes it seen; every option moves the mesh;
* **the quality bound** (§2, p. 5; theorem 4, p. 16; T13): circumradius over
  shortest side at most B = sqrt(2) in every triangle of a domain whose
  input angles are all at least 60 degrees;
* **Delaunay** (p. 9): no vertex strictly inside the circumcircle of a
  triangle, in a convex domain (the square with the excavation meshed);
* **grading** (theorem 8, pp. 22-23): with B = 1/(2 sin 15 deg) and input
  angles above 60 degrees, every vertex is at least lfs(v)/(D_S + 1) from its
  nearest neighbour, lfs by brute force from its definition (p. 11). The core
  warns that its concentric shells (§6.2) are outside that proof: this is a
  check of the bound on these meshes, not the theorem;
* **small input angles** (theorem 12, p. 35): a wedge of 5 degrees is meshed
  (it terminates) and every triangle keeps circumradius over shortest side
  at most 1/(sqrt(2) sin(phi/2)); the notes give phi;
* **the map**: the vertex i of the PSLG is the node i of the mesh, and each
  piece's vertex list runs from its u to its v along sides of the mesh;
* **the arcs are split on the arc** (D14; Pav and Walkington, corollaries 1
  and 2, p. 7): on a fine uniform mesh the core adds vertices to the pieces
  of the excavation's arcs, and every one of them is on its circle (to 1e-12
  of the radius) and between the ends of its piece. Until 0.2.6 they were on
  the chords: the test that said so was written to fail then, and did not,
  because it only counted them; it is this one now;
* **the notes say whether the termination was proved** with arcs (D15, rule
  12): the largest turn of a piece (10 degrees) and the bound of corollary 3
  (p. 13), recomputed here from the source's formulas, B > 1.76; with the
  default B = sqrt(2) not met, with B = 1.77 met; without arcs, nothing.
"""
from __future__ import annotations

import math
from dataclasses import replace

from ogr_core.fem import refine

from ogr_fem2d.mesh import discretize, geometry as g, pslg, sizing
from ogr_fem2d.mesh.quadratic import edge_key
from test_mesh_input_v008 import TUNNEL


def _mesh(m: g.MeshInput, max_ratio=None, with_corners=True):
    disc = discretize.discretize(m)
    p = pslg.build(m, disc)
    if not with_corners:
        p = replace(p, vertices=disc.points)
    bound = sizing.size_bound(m)
    size = bound if (bound.global_size is not None or bound.windows) else None
    kwargs = {} if max_ratio is None else {"max_ratio": max_ratio}
    return p, refine.quality_triangulation(p, size=size, **kwargs)


def _xy(mesh, i):
    n = mesh.nodes[i]
    return (n.x, n.y)


def _sides(mesh, e):
    pts = [_xy(mesh, i) for i in e.nodes]
    return [math.dist(pts[k], pts[(k + 1) % 3]) for k in range(3)]


def _ratio(mesh, e):
    """Circumradius over shortest side."""
    a, b, c = (_xy(mesh, i) for i in e.nodes)
    la, lb, lc = math.dist(b, c), math.dist(a, c), math.dist(a, b)
    area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
    return la * lb * lc / (4.0 * area) / min(la, lb, lc)


def _uniform(h):
    return replace(TUNNEL, settings=replace(TUNNEL.settings, kind="uniform",
                                            boundary_nodes=None, size=h))


WINDOW = g.Window(((5.0, 5.0), (5.4, 5.0), (5.4, 5.4), (5.0, 5.4)), 0.05)


class TestSizeBound:
    def test_uniform_h_and_graded_max_size(self):
        for m, bound in ((_uniform(0.5), 0.5),
                         (replace(TUNNEL, settings=replace(TUNNEL.settings, max_size=2.0)), 2.0)):
            _p, r = _mesh(m)
            longest = max(max(_sides(r.mesh, e)) for e in r.mesh.elements)
            assert longest <= bound * (1.0 + 1e-12), (bound, longest)

    def test_a_window_is_seen_through_its_corners(self):
        m = replace(TUNNEL, settings=replace(TUNNEL.settings, boundary_nodes=36, windows=(WINDOW,)))
        for corners, seen in ((True, True), (False, False)):
            _p, r = _mesh(m, with_corners=corners)
            inside = [e for e in r.mesh.elements
                      if 5.0 <= e.centroid(r.mesh)[0] <= 5.4 and 5.0 <= e.centroid(r.mesh)[1] <= 5.4]
            assert bool(inside) == seen, (corners, len(inside))
            if seen:
                assert len(inside) > 20
                assert max(max(_sides(r.mesh, e)) for e in inside) <= 0.05 * (1 + 1e-12)

    def test_every_option_moves_the_mesh(self):
        base = replace(TUNNEL, settings=replace(TUNNEL.settings, boundary_nodes=36))
        counts = [len(_mesh(m)[1].mesh.elements) for m in (
            base, replace(base, settings=replace(base.settings, max_size=2.0)),
            replace(base, settings=replace(base.settings, windows=(WINDOW,))))]
        assert counts[0] < counts[1] and counts[0] < counts[2], counts


class TestQuality:
    def test_theorem_4_every_ratio_at_most_b(self):
        for m in (TUNNEL, _uniform(1.0)):
            _p, r = _mesh(m)
            worst = max(_ratio(r.mesh, e) for e in r.mesh.elements)
            assert worst <= math.sqrt(2.0) * (1 + 1e-12), worst

    def test_delaunay_in_a_convex_domain(self):
        _p, r = _mesh(replace(TUNNEL, settings=replace(TUNNEL.settings, boundary_nodes=36)))
        pts = [_xy(r.mesh, i) for i in range(len(r.mesh.nodes))]
        for e in r.mesh.elements:
            a, b, c = (pts[i] for i in e.nodes)
            d = 2.0 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
            ux = ((a[0] ** 2 + a[1] ** 2) * (b[1] - c[1]) + (b[0] ** 2 + b[1] ** 2) * (c[1] - a[1])
                  + (c[0] ** 2 + c[1] ** 2) * (a[1] - b[1])) / d
            uy = ((a[0] ** 2 + a[1] ** 2) * (c[0] - b[0]) + (b[0] ** 2 + b[1] ** 2) * (a[0] - c[0])
                  + (c[0] ** 2 + c[1] ** 2) * (b[0] - a[0])) / d
            rr = math.dist((ux, uy), a)
            for k, q in enumerate(pts):
                if k not in e.nodes:
                    assert math.dist((ux, uy), q) >= rr * (1 - 1e-9), (e.nodes, k)

    def test_theorem_8_grading_checked_on_these_meshes(self):
        b = 1.0 / (2.0 * math.sin(math.radians(15.0)))
        d_s = (1.0 + math.sqrt(2.0)) * b / (b - math.sqrt(2.0))       # alpha_min = 90 deg here
        assert abs(d_s - 9.01) < 0.01
        m = replace(TUNNEL, settings=replace(TUNNEL.settings, boundary_nodes=36))
        p, r = _mesh(m, max_ratio=b)
        verts = list(p.vertices)
        segs = [(u, v) for u, v, _lab in p.segments]

        def to_seg(x, s):
            a, c = verts[s[0]], verts[s[1]]
            dx, dy = c[0] - a[0], c[1] - a[1]
            t = max(0.0, min(1.0, ((x[0] - a[0]) * dx + (x[1] - a[1]) * dy) / (dx * dx + dy * dy)))
            return math.dist(x, (a[0] + t * dx, a[1] + t * dy))

        features = [("v", i) for i in range(len(verts))] + [("s", s) for s in segs]

        def incident(f, h):
            if f[0] == "v" and h[0] == "v":
                return f[1] == h[1]
            if f[0] == "v":
                return f[1] in h[1]
            if h[0] == "v":
                return h[1] in f[1]
            return bool(set(f[1]) & set(h[1]))

        def lfs(x):
            dist = [math.dist(x, verts[f[1]]) if f[0] == "v" else to_seg(x, f[1]) for f in features]
            best = math.inf
            for i in range(len(features)):
                for j in range(i + 1, len(features)):
                    if not incident(features[i], features[j]):
                        best = min(best, max(dist[i], dist[j]))
            return best

        pts = [_xy(r.mesh, i) for i in range(len(r.mesh.nodes))]
        for i, x in enumerate(pts):
            nearest = min(math.dist(x, y) for k, y in enumerate(pts) if k != i)
            assert nearest >= lfs(x) / (d_s + 1.0) * (1 - 1e-12), (i, nearest, lfs(x))

    def test_theorem_12_a_wedge_of_5_degrees(self):
        phi = math.radians(5.0)
        wedge = g.MeshInput("plane_strain", ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0 * math.tan(phi))),
                            (g.Region((0, 1, 2)),), (), g.MeshSettings(kind="uniform", size=1.0))
        _p, r = _mesh(wedge)
        bound = 1.0 / (math.sqrt(2.0) * math.sin(phi / 2.0))
        worst = max(_ratio(r.mesh, e) for e in r.mesh.elements)
        assert worst <= bound * (1 + 1e-12), (worst, bound)
        assert abs(r.notes["min_input_angle"] - 5.0) < 1e-9, r.notes["min_input_angle"]
        assert math.isclose(r.notes["theorem_12_bound"], bound, rel_tol=1e-12)


class TestTheMap:
    def test_vertex_i_is_node_i_and_pieces_run_along_sides(self):
        p, r = _mesh(replace(TUNNEL, settings=replace(TUNNEL.settings, windows=(WINDOW,))))
        for i, v in enumerate(p.vertices):
            assert _xy(r.mesh, i) == v, i
        sides = {edge_key(*pair) for e in r.mesh.elements
                 for pair in ((e.nodes[0], e.nodes[1]), (e.nodes[1], e.nodes[2]),
                              (e.nodes[2], e.nodes[0]))}
        for (u, v, label), chain, lab in zip(p.segments, r.segment_vertices, r.segment_labels):
            assert lab == label and chain[0] == u and chain[-1] == v
            assert all(edge_key(a, b) in sides for a, b in zip(chain, chain[1:]))


def _corollary_3(tau):
    """B of Pav and Walkington's corollary 3 (p. 13), from the source: the
    angle bound kappa < arcsin(1/(2 mu sqrt 2)) and arcsin(1/(2 zeta eta)),
    eta = (1 + tan(tau/2)) / (1 - tan(tau/2)), mu = 1 / (1 - tan(tau/2))
    (p. 6), zeta = sqrt 2 sin(tau/2) / (sqrt(1 + sin tau) - 1) (p. 8); B =
    1 / (2 sin kappa) (Shewchuk 2002a, p. 5)."""
    t = math.tan(tau / 2.0)
    eta, mu = (1.0 + t) / (1.0 - t), 1.0 / (1.0 - t)
    zeta = math.sqrt(2.0) * math.sin(tau / 2.0) / (math.sqrt(1.0 + math.sin(tau)) - 1.0)
    kappa = min(math.asin(1.0 / (2.0 * mu * math.sqrt(2.0))),
                math.asin(1.0 / (2.0 * zeta * eta)))
    return 1.0 / (2.0 * math.sin(kappa))


#: pieces of 10 degrees (0.17 m) against elements of 0.05 m: the core has to
#: split the pieces of the arcs to keep the size bound
FINE = replace(_uniform(0.05), segments=tuple(replace(sp, divisions=9) for sp in TUNNEL.segments))


class TestArcsOnTheArc:
    def test_every_vertex_added_on_an_arc_is_on_its_circle(self):
        p, r = _mesh(FINE)
        added = 0
        for (u, v, label), chain in zip(p.segments, r.segment_vertices):
            if label not in p.arcs:
                continue
            c = p.arcs[label]
            a, b = p.vertices[u], p.vertices[v]
            radius = math.dist(a, c)
            ua = (a[0] - c[0], a[1] - c[1])
            vb = (b[0] - c[0], b[1] - c[1])
            turn = ua[0] * vb[1] - ua[1] * vb[0]
            for i in chain[1:-1]:
                x = _xy(r.mesh, i)
                added += 1
                assert abs(math.dist(x, c) - radius) <= 1e-12 * radius, (label, i)
                w = (x[0] - c[0], x[1] - c[1])
                # between the ends, seen from the centre
                assert (ua[0] * w[1] - ua[1] * w[0]) * turn > 0, (label, i)
                assert (w[0] * vb[1] - w[1] * vb[0]) * turn > 0, (label, i)
        assert added > 100, added

    def test_the_notes_say_whether_the_termination_was_proved(self):
        bound = _corollary_3(math.radians(10.0))
        assert abs(bound - 1.76) < 0.005, bound
        tenths = replace(TUNNEL, settings=replace(TUNNEL.settings, boundary_nodes=36))
        p, r = _mesh(tenths)
        n = r.notes
        assert n["arc_pieces"] == sum(1 for _u, _v, lab in p.segments if lab in p.arcs) == 36
        assert abs(n["arc_turn"] - 10.0) < 1e-9, n["arc_turn"]
        assert math.isclose(n["arc_bound"]["ratio"], bound, rel_tol=1e-9), n["arc_bound"]
        assert n["arc_bound"]["met"] is False and n["arc_unproven"] is not None
        _p, r = _mesh(tenths, max_ratio=1.77)
        assert r.notes["arc_bound"]["met"] is True
        square = g.MeshInput("plane_strain", ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
                             (g.Region((0, 1, 2, 3)),), (), g.MeshSettings(kind="uniform", size=0.5))
        _p, r = _mesh(square)
        assert (r.notes["arc_pieces"], r.notes["arc_bound"], r.notes["arc_unproven"]) == (0, None, None)
