# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.8 (spec 003, T7) — the patch test on generated meshes, through the
engine: a mesh made by the mesher is a mesh the engine can use.

Source: Zienkiewicz and Taylor (2000), §9.7, theorem 3, pp. 213-214, Eqs.
(9.23)-(9.25): every isoparametric element reproduces a linear field exactly,
because the shape functions add up to one, curved or not; and §5.2.2, p. 115:
in axisymmetry u = a r, v = b z is the field of constant strain.

Invariants protected: with the displacement of a linear field imposed on the
boundary nodes (corners and mid-side nodes) and nothing else acting, the
engine gives that field at every interior node and the stress of Hooke's law
at every integration point, constant:

* plane strain, three-node triangles of the core's generator on the square
  with a circular hole (both regions), and the same promoted to six-node
  triangles with the hole's sides on the circle (T5);
* axisymmetry, a quarter annulus 1 <= r <= 3 by the core's generator,
  three- and six-node, its arcs curved, with nodes on the axis.

A six-node mesh whose mid-side nodes are not shared, or are put on the wrong
sides, fails it.
"""
from __future__ import annotations

import math

from ogr_core.fem.generator import generate_mesh
from ogr_core.geometry.regions import MaterialRegion

from ogr_fem2d.engine import analysis
from ogr_fem2d.engine import model as m
from ogr_fem2d.engine.reference.elastic import Elastic
from ogr_fem2d.mesh import checks, quadratic as q
from test_mesh_quadratic_v008 import _core_tunnel, _ring

E, NU = 1000.0, 0.25
LAM = E * NU / ((1 + NU) * (1 - 2 * NU))
G = E / (2 * (1 + NU))


def _boundary_nodes(nodes, elements):
    topo = checks.topology(nodes, elements)
    out = {i for key in topo.boundary for i in key}
    if len(elements[0]) == 6:
        mid_of = {}
        for e in elements:
            for k in range(3):
                mid_of[q.edge_key(e[k], e[(k + 1) % 3])] = e[3 + k]
        out |= {mid_of[key] for key in topo.boundary}
    return sorted(out)


def _solve(nodes, elements, kind, field):
    held = _boundary_nodes(nodes, elements)
    imposed = []
    for n in held:
        u, v = field(*nodes[n])
        imposed += [m.ImposedDisplacement(n, 0, u), m.ImposedDisplacement(n, 1, v)]
    stage = m.Stage(active=(True,) * len(elements), imposed=tuple(imposed), tolerance=1e-12)
    model = m.EngineModel(kind, tuple(nodes), tuple(tuple(e) for e in elements),
                          (m.Material(Elastic(E, NU)),), (0,) * len(elements), (stage,))
    return analysis.run(model)[0], held


def _assert_field(nodes, out, held, field, stress):
    scale = max(abs(c) for p in nodes for c in field(*p))
    interior = [n for n in range(len(nodes)) if n not in set(held)]
    assert interior
    for n in range(len(nodes)):
        u, v = field(*nodes[n])
        assert abs(out.displacement[2 * n] - u) <= 1e-10 * scale, (n, out.displacement[2 * n], u)
        assert abs(out.displacement[2 * n + 1] - v) <= 1e-10 * scale, n
    for s in out.stresses:
        for got, want in zip(s, stress):
            assert abs(got - want) <= 1e-9 * max(abs(x) for x in stress), (s, stress)


# plane strain: u = 1e-3 (1 + 2x - y), v = 1e-3 (-0.5 + 0.5 x + 3y)
def _plane(x, y):
    return 1e-3 * (1.0 + 2.0 * x - y), 1e-3 * (-0.5 + 0.5 * x + 3.0 * y)


EX, EY, GXY = 2e-3, 3e-3, 1e-3 * (-1.0 + 0.5)
PLANE_STRESS = (LAM * (EX + EY) + 2 * G * EX, LAM * (EX + EY) + 2 * G * EY,
                LAM * (EX + EY), G * GXY)


# axisymmetry: u = a r, v = b z + c (the only constant strain field)
A_R, B_Z = 2e-3, -1e-3


def _axi(r, z):
    return A_R * r, B_Z * z + 1e-3


AXI_STRESS = (LAM * (2 * A_R + B_Z) + 2 * G * A_R, LAM * (2 * A_R + B_Z) + 2 * G * B_Z,
              LAM * (2 * A_R + B_Z) + 2 * G * A_R, 0.0)


def _quarter_annulus():
    """The core's generator on the quarter annulus 1 <= r <= 3 (16 chords per
    arc); the arcs' sides, about the origin."""
    inner = [(math.cos(math.pi / 2 * k / 16), math.sin(math.pi / 2 * k / 16)) for k in range(17)]
    inner[0], inner[-1] = (1.0, 0.0), (0.0, 1.0)      # cos(pi/2) is 6e-17, not 0: the axis exactly
    outer = [(3 * x, 3 * y) for x, y in inner]
    poly = outer + inner[::-1]
    mesh = generate_mesh([MaterialRegion(polygon=_ring(poly), material_id="a")], target_size=0.4)
    nodes = [(n.x, n.y) for n in mesh.nodes]
    tris = [e.nodes for e in mesh.elements]
    arcs = {}
    for t in tris:
        for k in range(3):
            i, j = t[k], t[(k + 1) % 3]
            ri, rj = math.hypot(*nodes[i]), math.hypot(*nodes[j])
            for r in (1.0, 3.0):
                if abs(ri - r) < 1e-12 and abs(rj - r) < 1e-12 and math.dist(nodes[i], nodes[j]) < 0.4:
                    arcs[q.edge_key(i, j)] = (0.0, 0.0)
    return nodes, tris, arcs


class TestPlaneStrain:
    def test_three_node_triangles_of_the_generator(self):
        nodes, tris, _ = _core_tunnel()
        out, held = _solve(nodes, tris, "plane_strain", _plane)
        _assert_field(nodes, out, held, _plane, PLANE_STRESS)

    def test_six_node_triangles_with_curved_sides(self):
        nodes, tris, arcs = _core_tunnel()
        mesh = q.promote(nodes, tris, arcs)
        out, held = _solve(mesh.nodes, mesh.elements, "plane_strain", _plane)
        _assert_field(mesh.nodes, out, held, _plane, PLANE_STRESS)


class TestAxisymmetry:
    def test_three_and_six_node_curved(self):
        nodes, tris, arcs = _quarter_annulus()
        assert any(p[0] == 0.0 for p in nodes)               # nodes on the axis
        out, held = _solve(nodes, tris, "axisymmetric", _axi)
        _assert_field(nodes, out, held, _axi, AXI_STRESS)
        mesh = q.promote(nodes, tris, arcs)
        assert arcs
        out, held = _solve(mesh.nodes, mesh.elements, "axisymmetric", _axi)
        _assert_field(mesh.nodes, out, held, _axi, AXI_STRESS)
