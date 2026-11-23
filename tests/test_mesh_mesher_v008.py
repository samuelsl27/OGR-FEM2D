# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.8 (spec 003, T12) — the mesher in two steps, from a geometry to the
input of the engine (``mesher.mesh``), with the core's quality triangulation
of OGR-Core 0.2.6.

Sources: Shewchuk (2002a), §1 and §3.1 (every segment is a union of edges;
the refinement may split a segment, D10) and theorem 4 (p. 16); Pav and
Walkington, corollaries 1 and 2 (p. 7: the pieces of an arc split on the
arc) and corollary 3 (p. 13, D15); Zienkiewicz and Taylor (2000), §9.2 and
§9.7, theorem 3 (the jacobian, the patch test); Archimedes (the area of a
parabolic segment, 2/3 chord x sagitta).

Invariants protected:

* **RF-3**: every segment of the geometry is a boundary of the mesh, its
  corners from its a to its b along sides of the mesh, holding every node
  of step 1 in order (the point i of step 1 is the node i of the mesh); the
  sides of one element are exactly the pieces of the outer segments; every
  node added by the refinement is on its segment (on the straight segment
  exactly, or on the circle of its arc) and the notes list it;
* **the arcs**: every corner of an arc's boundary on its circle, and with
  six-node triangles the mid-side node of every piece on it too, at the
  middle of the arc; the area of the mesh is that of the polygon of the
  corners (three-node) plus or minus 2/3 chord x sagitta for every curved
  side (six-node), and it is nearer the exact area than the polygon's;
* **regions and materials**: the centroid of every element is inside its
  region, and the element carries the region's material;
* **the axis** of an axisymmetric mesh: its nodes keep x = 0 exactly;
* **the patch test** (Z&T §9.7) through the engine, plane strain and
  axisymmetry, six-node triangles with curved sides made by the mesher;
* **the quality bound** (theorem 4): with B = sqrt(2) and input angles of 60
  degrees or more, no triangle above B, smallest angle >= 20.7 degrees, and
  the summary says so (RF-12);
* **RF-11**: the same input twice gives the same mesh, bit for bit;
* **rule 12**: the notes carry every setting and default (B and its angle,
  the sizes, the divisions of step 1, the largest turn of an arc); with
  arcs, whether the termination was proved (Pav and Walkington's bound,
  B > 1.76 with pieces of 10 degrees: no with sqrt 2, yes with 1.77);
  without arcs, None;
* **rule 7**: every setting moves the mesh;
* **the safety net of D14 (a)**: a valid ring thinner than the sagitta of
  its pieces, which the core refuses with pieces of 10 degrees, is meshed
  with twice the divisions on both its circles, and the notes say so; an
  element rejected by its jacobian with a side on an arc makes the mesher
  try again with twice the divisions on its circle (the rejection forced by
  hand: none of the meshes tried folds, with B up to 1000), at most
  MAX_ARC_RETRIES times, then the error of RF-13; a rejected element with
  no side on an arc is the error at once;
* **errors, never a bad mesh**: too many triangles is the core's error.
"""
from __future__ import annotations

import math
from dataclasses import replace

from ogr_core.fem import refine

from ogr_fem2d.mesh import checks, discretize, mesher
from ogr_fem2d.mesh import geometry as g
from ogr_fem2d.mesh.quadratic import edge_key
from test_mesh_input_v008 import CAVITY, DENT, SLOPE, TUNNEL
from test_mesh_patch_v008 import AXI_STRESS, PLANE_STRESS, _assert_field, _axi, _plane, _solve
from test_mesh_refine_v008 import _corollary_3

ALL = {"tunnel": TUNNEL, "cavity": CAVITY, "dent": DENT, "slope": SLOPE}


def _set(m, **kw):
    return replace(m, settings=replace(m.settings, **kw))


def _three(m):
    return _set(m, nodes_per_element=3)


def _ring(t, boundary_nodes=36):
    """A ring 1 <= r <= 1 + t, each circle in four arcs; the inner one is the
    excavation (not meshed)."""
    o = g.Arc((0.0, 0.0))
    r2 = 1.0 + t
    pts = ((1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0), (r2, 0.0), (0.0, r2), (-r2, 0.0),
           (0.0, -r2))
    segs = tuple(g.SegmentSpec(a, b, arc=o, excavation=a < 4)
                 for a, b in ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4)))
    return g.MeshInput("plane_strain", pts, (g.Region((4, 5, 6, 7), ((0, 3, 2, 1),)),), segs,
                       g.MeshSettings(boundary_nodes=boundary_nodes))


def _shoelace(xy):
    return 0.5 * sum(xy[k][0] * xy[(k + 1) % len(xy)][1] - xy[(k + 1) % len(xy)][0] * xy[k][1]
                     for k in range(len(xy)))


def _ring_corners(m, mesh, ring):
    """The corners of a ring of the input, in its direction, from the
    boundaries of the mesh."""
    out = []
    for i, j in g._ring_edges(ring):
        try:
            b = mesh.boundary(f"segment {i}-{j}")
            nodes = list(b.nodes)
        except KeyError:
            nodes = list(reversed(mesh.boundary(f"segment {j}-{i}").nodes))
        out.extend(nodes[:-1])
    return [mesh.nodes[n] for n in out]


def _t3_area(nodes, e):
    a, b, c = (nodes[i] for i in e[:3])
    return 0.5 * ((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))


def _t6_area(nodes, e):
    """The area of a six-node triangle: det J / 2 integrated by the 3-point
    rule at the mid-sides, exact for det J of degree 2."""
    xy = [nodes[i] for i in e]
    total = 0.0
    for xi, eta in ((0.5, 0.0), (0.5, 0.5), (0.0, 0.5)):
        l1, l2, l3 = 1.0 - xi - eta, xi, eta
        # dN/dxi, dN/deta; corners (L1, L2, L3), then sides 0-1, 1-2, 2-0
        dn = [(-(4 * l1 - 1), -(4 * l1 - 1)), (4 * l2 - 1, 0.0), (0.0, 4 * l3 - 1),
              (4 * (l1 - l2), -4 * l2), (4 * l3, 4 * l2), (-4 * l3, 4 * (l1 - l3))]
        jx = sum(d[0] * p[0] for d, p in zip(dn, xy)), sum(d[1] * p[0] for d, p in zip(dn, xy))
        jy = sum(d[0] * p[1] for d, p in zip(dn, xy)), sum(d[1] * p[1] for d, p in zip(dn, xy))
        total += (jx[0] * jy[1] - jx[1] * jy[0]) / 6.0
    return total


class TestRF3EverySegmentIsABoundary:
    def test_chains_hold_step_1_and_run_along_sides(self):
        for name, m in ALL.items():
            disc = discretize.discretize(m)
            mesh = mesher.mesh(m)
            for i, p in enumerate(disc.points):
                assert mesh.nodes[i] == p, (name, i)
            sides = {}
            for e, el in enumerate(mesh.elements):
                for k in range(3):
                    sides.setdefault(edge_key(el[k], el[(k + 1) % 3]), []).append(e)
            outer = set()
            for ds in disc.segments:
                s = ds.segment
                b = mesh.boundary(f"segment {s.a}-{s.b}")
                assert b.nodes[0] == s.a and b.nodes[-1] == s.b, (name, s)
                pos = [b.nodes.index(n) for n in ds.nodes]
                assert pos == sorted(pos), (name, s)          # step 1, in order
                for u, v in zip(b.nodes, b.nodes[1:]):
                    assert edge_key(u, v) in sides, (name, s, u, v)
                    if s.outer:
                        outer.add(edge_key(u, v))
            single = {key for key, els in sides.items() if len(els) == 1}
            assert single == outer, name

    def test_added_nodes_are_on_their_segment_and_listed(self):
        for name, m in ALL.items():
            disc = discretize.discretize(m)
            mesh = mesher.mesh(m)
            listed = {a["segment"]: a["nodes"] for a in mesh.notes["added_on_segments"]}
            total = 0
            for ds in disc.segments:
                s = ds.segment
                key = f"segment {s.a}-{s.b}"
                chain = mesh.boundary(key).nodes
                new = tuple(n for n in chain if n not in ds.nodes)
                assert listed.get(key, ()) == new, (name, key)
                a, b = m.points[s.a], m.points[s.b]
                for n in new:
                    p = mesh.nodes[n]
                    if s.arc is None:
                        assert g._orient(a, b, p) == 0, (name, key, n)
                    else:
                        r = math.dist(a, s.arc.centre)
                        assert abs(math.dist(p, s.arc.centre) - r) <= 1e-12 * r, (name, key, n)
                total += len(new)
            assert total > 0, name


class TestTheArcs:
    def test_corners_and_mid_side_nodes_on_the_circle(self):
        for name in ("tunnel", "cavity", "dent"):
            m = ALL[name]
            mesh = mesher.mesh(m)
            mid = {}
            for el in mesh.elements:
                for k in range(3):
                    mid[edge_key(el[k], el[(k + 1) % 3])] = el[3 + k]
            for s in g.segments(m):
                if s.arc is None:
                    continue
                c = s.arc.centre
                r = math.dist(m.points[s.a], c)
                chain = mesh.boundary(f"segment {s.a}-{s.b}").nodes
                for u, v in zip(chain, chain[1:]):
                    for n in (u, v, mid[edge_key(u, v)]):
                        assert abs(math.dist(mesh.nodes[n], c) - r) <= 1e-12 * r, (name, n)
                    w = mesh.nodes[mid[edge_key(u, v)]]
                    assert abs(math.dist(w, mesh.nodes[u]) - math.dist(w, mesh.nodes[v])) \
                        <= 1e-12 * r, (name, u, v)

    def test_areas_polygon_and_archimedes(self):
        # region by region: the tunnel's rock (with the hole) and the dent
        for name in ("tunnel", "dent"):
            m = ALL[name]
            region = m.regions[0]
            exact = g.region_area(m, 0)
            t3 = mesher.mesh(_three(m))
            polygon = _shoelace(_ring_corners(m, t3, region.outline)) + sum(
                _shoelace(_ring_corners(m, t3, h)) for h in region.holes)
            a3 = sum(_t3_area(t3.nodes, e) for e, r in zip(t3.elements, t3.element_region)
                     if r == 0)
            assert math.isclose(a3, polygon, rel_tol=1e-12), (name, a3, polygon)
            assert abs(a3 - exact) > 1e-3, name                 # the arcs are seen
            t6 = mesher.mesh(m)
            mine = [e for e, r in zip(t6.elements, t6.element_region) if r == 0]
            a6 = sum(_t6_area(t6.nodes, e) for e in mine)
            # every curved side adds or takes the area of its parabolic
            # segment, 2/3 |chord x (w - m)|, w its mid-side node and m the
            # middle of the chord, as it bulges out of its element or into it
            straight, bulge = 0.0, 0.0
            for e in mine:
                straight += _t3_area(t6.nodes, e)
                for k in range(3):
                    a, b, w = (t6.nodes[i] for i in (e[k], e[(k + 1) % 3], e[3 + k]))
                    mid = (0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]))
                    cross = (b[0] - a[0]) * (w[1] - mid[1]) - (b[1] - a[1]) * (w[0] - mid[0])
                    bulge -= 2.0 / 3.0 * cross     # w to the right of a -> b: outward, adds
            assert math.isclose(a6, straight + bulge, rel_tol=1e-12), (name, a6, straight + bulge)
            assert abs(a6 - exact) < 0.01 * abs(straight - exact), (name, a6, straight, exact)


class TestRegionsAndMaterials:
    def test_every_element_in_its_region_with_its_material(self):
        # materials that are not the regions' indices: the rock 2, the
        # excavation 0
        swapped = replace(TUNNEL, regions=(replace(TUNNEL.regions[0], material=2),
                                           replace(TUNNEL.regions[1], material=0)))
        for name, m in (("tunnel", swapped), ("slope", SLOPE)):
            mesh = mesher.mesh(m)
            arcs = g._arcs(m)
            assert len(set(mesh.element_region)) == len(m.regions), name
            for e, el in enumerate(mesh.elements):
                xy = [mesh.nodes[i] for i in el[:3]]
                c = (sum(p[0] for p in xy) / 3.0, sum(p[1] for p in xy) / 3.0)
                r = mesh.element_region[e]
                assert g._inside_region(c, m.regions[r], m.points, arcs), (name, e)
                assert mesh.element_material[e] == m.regions[r].material, (name, e)


class TestTheAxis:
    def test_nodes_on_the_axis_keep_x_zero(self):
        mesh = mesher.mesh(CAVITY)
        axis = mesh.boundary("segment 1-0").nodes
        assert len(axis) > 2
        for el in mesh.elements:
            for k in range(3):
                if el[k] in axis and el[(k + 1) % 3] in axis:
                    assert mesh.nodes[el[3 + k]][0] == 0.0
        assert all(mesh.nodes[n][0] == 0.0 for n in axis)
        assert min(p[0] for p in mesh.nodes) == 0.0


class TestThePatchTest:
    def test_plane_strain_and_axisymmetry_six_node_curved(self):
        mesh = mesher.mesh(TUNNEL)
        out, held = _solve(mesh.nodes, mesh.elements, "plane_strain", _plane)
        _assert_field(mesh.nodes, out, held, _plane, PLANE_STRESS)
        mesh = mesher.mesh(CAVITY)
        out, held = _solve(mesh.nodes, mesh.elements, "axisymmetric", _axi)
        _assert_field(mesh.nodes, out, held, _axi, AXI_STRESS)


class TestQuality:
    def test_theorem_4_and_the_summary(self):
        for name in ("tunnel", "slope"):
            mesh = mesher.mesh(ALL[name])
            q = mesh.notes["quality"]
            assert q["above_bound"] == () and mesh.notes["above_ratio"] == (), name
            assert q["min_angle"]["worst"] >= mesh.notes["angle_guaranteed"] - 1e-9, name
            assert abs(mesh.notes["angle_guaranteed"] - 20.705) < 1e-3
            assert q["inverted"] == 0 and 0.0 < q["gradient"]["worst"] <= 1.0
            assert sum(q["min_angle"]["counts"]) == q["elements"] == len(mesh.elements)


class TestDeterminism:
    def test_the_same_input_twice(self):
        for name, m in ALL.items():
            a, b = mesher.mesh(m), mesher.mesh(m)
            assert (a.nodes, a.elements, a.element_material) == \
                (b.nodes, b.elements, b.element_material), name


class TestTheNotes:
    def test_every_setting_and_default(self):
        mesh = mesher.mesh(TUNNEL)
        n = mesh.notes
        assert (n["kind"], n["nodes_per_element"], n["quality_bound"], n["boundary_nodes"],
                n["max_size"], n["size"]) == ("graded", 6, math.sqrt(2.0), 40, None, None)
        assert abs(n["max_arc_turn"] - 10.0) < 1e-12
        disc = discretize.discretize(TUNNEL)
        assert n["divisions"] == tuple((f"segment {ds.segment.a}-{ds.segment.b}", ds.divisions)
                                       for ds in disc.segments)
        assert n["max_triangles"] == mesher.MAX_TRIANGLES and n["arc_retries"] == ()
        uni = mesher.mesh(_set(TUNNEL, kind="uniform", boundary_nodes=None, size=1.5))
        assert (uni.notes["size"], uni.notes["boundary_nodes"]) == (1.5, None)

    def test_whether_the_termination_with_arcs_was_proved(self):
        m = _set(TUNNEL, boundary_nodes=36)
        n = mesher.mesh(m).notes
        assert abs(n["arc_turn"] - 10.0) < 1e-9
        assert n["arc_termination_proven"] is False and n["arc_unproven"] is not None
        assert math.isclose(n["arc_bound"]["ratio"], _corollary_3(math.radians(10.0)),
                            rel_tol=1e-9)
        n = mesher.mesh(_set(m, quality_bound=1.77)).notes
        assert n["arc_termination_proven"] is True
        n = mesher.mesh(SLOPE).notes
        assert (n["arc_turn"], n["arc_termination_proven"], n["arc_unproven"]) == (None, None, None)


class TestEverySettingMovesTheMesh:
    def test_rule_7(self):
        base = TUNNEL
        variants = {
            "kind": _set(base, kind="uniform", boundary_nodes=None, size=2.0),
            "nodes_per_element": _three(base),
            "quality_bound": _set(base, quality_bound=2.0),
            "boundary_nodes": _set(base, boundary_nodes=48),
            "max_size": _set(base, max_size=2.0),
            "windows": _set(base, windows=(g.Window(((5.0, 5.0), (8.0, 5.0), (8.0, 8.0),
                                                     (5.0, 8.0)), 0.3),)),
        }
        ref = mesher.mesh(base)
        for key, m in variants.items():
            got = mesher.mesh(m)
            assert (got.nodes, got.elements) != (ref.nodes, ref.elements), key
        uniform = _set(base, kind="uniform", boundary_nodes=None, size=2.0)
        for key, m in {"size": _set(uniform, size=1.0),
                       "elements": _set(uniform, size=None, elements=400)}.items():
            assert mesher.mesh(m).elements != mesher.mesh(uniform).elements, key


class _Rejecting:
    """For as long as it is on, ``checks.indexed_element_problems`` rejects
    the first element that ``pick`` chooses, ``times`` times; restored on
    exit."""

    def __init__(self, pick, times):
        self.pick, self.times, self.calls = pick, times, 0

    def __enter__(self):
        self.real = checks.indexed_element_problems

        def fake(nodes, elements, analysis):
            self.calls += 1
            found = self.real(nodes, elements, analysis)
            if self.calls <= self.times:
                e = self.pick(nodes, elements)
                found = found + [(e, checks.Problem("jacobian", f"element {e}", "forced"))]
            return found

        checks.indexed_element_problems = fake
        return self

    def __exit__(self, *exc):
        checks.indexed_element_problems = self.real
        return False


def _on_the_hole(nodes, elements):
    """An element with a side on the hole of the tunnel (radius 1)."""
    for e, el in enumerate(elements):
        on = [abs(math.hypot(*nodes[i]) - 1.0) < 1e-9 for i in el[:3]]
        if sum(on) >= 2:
            return e
    raise AssertionError("no element on the hole")


def _far_from_arcs(nodes, elements):
    for e, el in enumerate(elements):
        if min(math.hypot(*nodes[i]) for i in el[:3]) > 5.0:
            return e
    raise AssertionError


class TestTheSafetyNet:
    def test_a_ring_thinner_than_the_sagitta(self):
        # sagitta of a 10 degree piece of radius 1.003: 0.0038 > 0.003
        m = _ring(0.003)
        assert g.problems(m) == []
        disc = discretize.discretize(m)
        try:
            refine.quality_triangulation(mesher.pslg.build(m, disc))
            raise AssertionError("the core took it")
        except refine.QualityMeshError as err:
            assert err.code == refine.M.REFINE_SEGMENT_IN_ARC
        mesh = mesher.mesh(m)
        (retry,) = mesh.notes["arc_retries"]
        assert retry["reason"] == refine.M.REFINE_SEGMENT_IN_ARC
        assert sorted(n for _s, n in retry["divisions"]) == [18] * 8
        assert mesh.notes["arc_turn"] < 5.0 + 1e-9
        assert mesher.mesh(_ring(0.01)).notes["arc_retries"] == ()

    def test_a_folded_element_on_an_arc_doubles_its_circle(self):
        with _Rejecting(_on_the_hole, 1) as fake:
            mesh = mesher.mesh(TUNNEL)
        assert fake.calls == 2 and checks.indexed_element_problems is fake.real
        (retry,) = mesh.notes["arc_retries"]
        assert retry["reason"] == "jacobian" and len(retry["elements"]) == 1
        hole = {"segment 4-7": 20, "segment 7-6": 20, "segment 6-5": 20, "segment 5-4": 20}
        assert dict(retry["divisions"]) == hole
        assert {k: v for k, v in mesh.notes["divisions"] if k in hole} == hole

    def test_at_most_max_arc_retries_then_rf_13(self):
        with _Rejecting(_on_the_hole, 99) as fake:
            try:
                mesher.mesh(TUNNEL)
                raise AssertionError("delivered")
            except checks.MeshError as err:
                assert any(p.message == "forced" for p in err.problems)
        assert fake.calls == mesher.MAX_ARC_RETRIES + 1

    def test_an_element_with_no_side_on_an_arc_is_the_error_at_once(self):
        with _Rejecting(_far_from_arcs, 99) as fake:
            try:
                mesher.mesh(TUNNEL)
                raise AssertionError("delivered")
            except checks.MeshError:
                pass
        assert fake.calls == 1


class TestErrors:
    def test_too_many_triangles_is_the_cores_error(self):
        keep = mesher.MAX_TRIANGLES
        mesher.MAX_TRIANGLES = 50
        try:
            mesher.mesh(TUNNEL)
            raise AssertionError("delivered")
        except refine.QualityMeshError as err:
            assert err.code == refine.M.REFINE_TOO_MANY_TRIANGLES
        finally:
            mesher.MAX_TRIANGLES = keep
