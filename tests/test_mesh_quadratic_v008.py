# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.8 (spec 003, T5) — from three-node to six-node triangles (RF-10, D4;
ogr_fem2d/mesh/quadratic.py), on three-node meshes that already exist: the
structured rectangle of spec 002, the quarter annulus of spec 001 split into
three-node triangles, and the core's generator on the square with a hole.

Invariants protected:

* **one mid-side node per side, shared**: a mesh of V corners and E sides
  ends with V + E nodes; every side has one mid-side node, used by both of
  its elements; the corners keep their numbers and coordinates;
* **where it goes**: in the middle of a straight side; on the circle, in the
  middle of the arc, on a side that is a piece of an arc (|x - c| = R to
  rounding, at the same distance from both corners); and in the place of
  element_t6's node order (corners, then sides 0-1, 1-2, 2-0);
* **the area, by Archimedes**: the six-node mesh, integrated by the
  engine's own element (element_t6.area, exact for det J of degree 2),
  covers the straight mesh plus 2/3 chord x sagitta for every boundary side
  on an arc, added where the arc bulges out of the domain and taken away
  where it bulges in; a straight mesh keeps its area exactly;
* **the same mesh gives the same nodes** (D11).
"""
from __future__ import annotations

import math

from ogr_core.fem.generator import generate_mesh
from ogr_core.geometry.primitives import Polyline, Vertex
from ogr_core.geometry.regions import MaterialRegion

from ogr_fem2d.engine import mesh_radial, mesh_structured
from ogr_fem2d.engine.reference import element_t6
from ogr_fem2d.mesh import quadratic as q

ORIGIN = (0.0, 0.0)


def _sides(triangles):
    out = []
    for t in triangles:
        for k in range(3):
            key = q.edge_key(t[k], t[(k + 1) % 3])
            if key not in out:
                out.append(key)
    return out


def _straight_area(nodes, triangles):
    return sum(0.5 * ((nodes[b][0] - nodes[a][0]) * (nodes[c][1] - nodes[a][1])
                      - (nodes[c][0] - nodes[a][0]) * (nodes[b][1] - nodes[a][1]))
               for a, b, c in triangles)


def _t6_area(mesh):
    return sum(element_t6.area([mesh.nodes[n] for n in e]) for e in mesh.elements)


def _annulus():
    """The quarter annulus of spec 001, 1 <= r <= 5, in three-node triangles,
    with its circumferential sides as arcs about the origin."""
    m = mesh_radial.quarter_annulus(1.0, 5.0, 4, 6, growth=1.3, nodes_per_element=3)
    arcs = {}
    for key in _sides(m.elements):
        a, b = m.nodes[key[0]], m.nodes[key[1]]
        if abs(math.hypot(*a) - math.hypot(*b)) <= 1e-12 * math.hypot(*a):
            arcs[key] = ORIGIN
    return m, arcs


def _ring(pts, ccw=True):
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts)))
    if (area > 0) != ccw:
        pts = pts[::-1]
    return Polyline(vertices=[Vertex(x, y) for x, y in pts], closed=True)


def _core_tunnel():
    """The core's generator on a 20 m square with a hole of radius 1 (40
    chords on the circle), and the region of the hole; its sides with both
    ends on the circle are arcs about the origin."""
    hole = [(math.cos(2 * math.pi * k / 40), math.sin(2 * math.pi * k / 40)) for k in range(40)]
    rock = MaterialRegion(polygon=_ring([(-10, -10), (10, -10), (10, 10), (-10, 10)]),
                          material_id="rock", holes=[_ring(hole, ccw=False)])
    exc = MaterialRegion(polygon=_ring(hole), material_id="exc")
    mesh = generate_mesh([rock, exc], target_size=1.0)
    nodes = [(n.x, n.y) for n in mesh.nodes]
    tris = [e.nodes for e in mesh.elements]
    on = {i for i, p in enumerate(nodes) if abs(math.hypot(*p) - 1.0) <= 1e-12}
    arcs = {key: ORIGIN for key in _sides(tris) if key[0] in on and key[1] in on
            and math.dist(nodes[key[0]], nodes[key[1]]) < 0.2}
    return nodes, tris, arcs


class TestOneMidSideNodePerSide:
    def test_counts_sharing_and_corners(self):
        rect = mesh_structured.rectangle([0.0, 1.0, 2.5, 4.0], [0.0, 0.5, 2.0], nodes_per_element=3)
        nodes, tris, arcs = _core_tunnel()
        for corners, triangles, a in ((rect.nodes, rect.elements, {}), (nodes, tris, arcs)):
            mesh = q.promote(corners, triangles, a)
            sides = _sides(triangles)
            assert len(mesh.nodes) == len(corners) + len(sides)
            assert mesh.nodes[:len(corners)] == tuple(corners)
            assert sorted(mesh.mid_of) == sorted(sides)
            uses = {}
            for e in mesh.elements:
                for m in e[3:]:
                    uses[m] = uses.get(m, 0) + 1
            boundary = sum(1 for k in sides if sum(1 for t in triangles
                                                   if set(k) <= set(t)) == 1)
            assert sorted(uses.values()).count(1) == boundary
            assert set(uses.values()) <= {1, 2}
            for t, e in zip(triangles, mesh.elements):
                assert e[:3] == tuple(t)


class TestWhereItGoes:
    def test_straight_sides_in_the_middle_in_element_t6_order(self):
        rect = mesh_structured.rectangle([0.0, 1.0, 2.5], [0.0, 0.5, 2.0], nodes_per_element=3)
        mesh = q.promote(rect.nodes, rect.elements)
        for e in mesh.elements:
            for k in range(3):
                a, b = mesh.nodes[e[k]], mesh.nodes[e[(k + 1) % 3]]
                assert mesh.nodes[e[3 + k]] == (0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]))

    def test_on_the_circle_in_the_middle_of_the_arc(self):
        for nodes, tris, arcs in (_annulus()[0].nodes, _annulus()[0].elements, _annulus()[1]), \
                _core_tunnel():
            mesh = q.promote(nodes, tris, arcs)
            assert arcs
            for key in arcs:
                a, b = nodes[key[0]], nodes[key[1]]
                m = mesh.nodes[mesh.mid_of[key]]
                r = math.hypot(*a)
                # c + r d/|d|: about four roundings, and one more to measure it:
                # six units of roundoff, 6 x 2^-53
                assert abs(math.hypot(*m) - r) <= 6 * 2.0 ** -53 * r, (key, m)
                assert abs(math.dist(m, a) - math.dist(m, b)) <= 1e-14 * r
                chord_mid = (0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]))
                assert math.hypot(*m) > math.hypot(*chord_mid)       # the minor arc


class TestAreaByArchimedes:
    def test_straight_mesh_keeps_its_area(self):
        rect = mesh_structured.rectangle([0.0, 1.0, 2.5, 4.0], [0.0, 0.5, 2.0], nodes_per_element=3)
        mesh = q.promote(rect.nodes, rect.elements)
        assert math.isclose(_t6_area(mesh), 8.0, rel_tol=1e-14)

    def test_the_arcs_add_or_take_two_thirds_chord_by_sagitta(self):
        m, arcs = _annulus()
        mesh = q.promote(m.nodes, m.elements, arcs)
        expected = _straight_area(m.nodes, m.elements)
        boundary = [k for k in arcs if sum(1 for t in m.elements if set(k) <= set(t)) == 1]
        assert boundary
        for key in boundary:
            a, b = m.nodes[key[0]], m.nodes[key[1]]
            r = math.hypot(*a)
            chord = math.dist(a, b)
            sagitta = r - math.sqrt(r * r - chord * chord / 4.0)
            outward = r > 3.0                      # the outer arc bulges out, the hole's in
            expected += (1 if outward else -1) * 2.0 / 3.0 * chord * sagitta
        assert math.isclose(_t6_area(mesh), expected, rel_tol=1e-13), (_t6_area(mesh), expected)
        # and it is near the true quarter annulus, closer than the straight mesh
        true = math.pi * (25.0 - 1.0) / 4.0
        assert abs(_t6_area(mesh) - true) < abs(_straight_area(m.nodes, m.elements) - true) / 10


class TestDeterminism:
    def test_the_same_mesh_gives_the_same_nodes(self):
        nodes, tris, arcs = _core_tunnel()
        assert q.promote(nodes, tris, arcs) == q.promote(list(nodes), list(tris), dict(arcs))
