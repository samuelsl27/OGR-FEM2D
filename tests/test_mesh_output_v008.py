# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.8 (spec 003, T9) — the output of the mesher and its translation into
the engine's input (RF-15; ogr_fem2d/mesh/mesher.py), on the core's mesh of
the square with a circular excavation, three- and six-node.

Invariants protected:

* **every piece of a boundary is a side, and the map says which**: for each
  piece u-v of a chain, every (element, k) given has corners k and k + 1 equal
  to {u, v}; a piece on the excavation's circle has two (rock and
  excavation), one on the outer square one; a chain with a piece that is not
  a side is refused (RF-3); with six-node elements the piece's mid-side node
  is the one of T5, on the circle;
* **the engine takes it**: to_engine gives an EngineModel that the engine's
  own validation accepts, with the material of every element where the mesh
  says, and refuses a material index that does not exist;
* **the map is usable for loads**: a uniform pressure on the hole, put on
  the rock's sides of the map with the excavation inactive, is a closed
  contour, so its resultant is zero (the reactions add up to zero) and the
  wall moves outward.
"""
from __future__ import annotations

import math

from ogr_fem2d.engine import analysis
from ogr_fem2d.engine import model as em
from ogr_fem2d.engine.reference.elastic import Elastic
from ogr_fem2d.mesh import mesher, quadratic as q
from test_mesh_quadratic_v008 import _core_tunnel

ROCK, VOID = em.Material(Elastic(1000.0, 0.25)), em.Material(Elastic(1.0, 0.25))


def _tunnel_mesh(six: bool) -> mesher.Mesh:
    nodes, tris, arcs = _core_tunnel()
    region = tuple(1 if sum(math.hypot(*nodes[i]) for i in t) / 3 < 1.0 else 0 for t in tris)
    elements = tris
    if six:
        quad = q.promote(nodes, tris, arcs)
        nodes, elements = quad.nodes, quad.elements
    corners = list(range(len(_core_tunnel()[0])))
    pts = _core_tunnel()[0]
    hole = sorted((i for i in corners if abs(math.hypot(*pts[i]) - 1.0) < 1e-12),
                  key=lambda i: math.atan2(pts[i][1], pts[i][0]))
    bottom = sorted((i for i in corners if pts[i][1] == -10.0), key=lambda i: pts[i][0])
    chains = [("hole", hole + hole[:1]), ("bottom", bottom)]
    boundaries = mesher.boundary_map(elements, chains)
    return mesher.Mesh("plane_strain", tuple(nodes), tuple(tuple(e) for e in elements),
                       region, tuple(1 - r for r in region), boundaries)   # rock: region 0, material 1


class TestTheMap:
    def test_every_piece_is_a_side_and_says_which(self):
        for six in (False, True):
            mesh = _tunnel_mesh(six)
            for name, per_piece in (("hole", 2), ("bottom", 1)):
                b = mesh.boundary(name)
                assert len(b.sides) == len(b.nodes) - 1
                for (u, v), found in zip(zip(b.nodes, b.nodes[1:]), b.sides):
                    assert len(found) == per_piece, (name, u, v, found)
                    for e, k in found:
                        el = mesh.elements[e]
                        assert {el[k], el[(k + 1) % 3]} == {u, v}
                    if name == "hole":
                        assert sorted(mesh.element_region[e] for e, _k in found) == [0, 1]

    def test_six_node_mid_side_nodes_are_those_of_t5(self):
        nodes, tris, arcs = _core_tunnel()
        quad = q.promote(nodes, tris, arcs)
        b = _tunnel_mesh(True).boundary("hole")
        for (u, v), mid in zip(zip(b.nodes, b.nodes[1:]), b.mids):
            assert mid == quad.mid_of[q.edge_key(u, v)]
            assert abs(math.hypot(*quad.nodes[mid]) - 1.0) <= 4e-16

    def test_a_piece_that_is_not_a_side_is_refused(self):
        nodes, tris, _ = _core_tunnel()
        corner = [i for i, p in enumerate(nodes) if p == (-10.0, -10.0)][0]
        far = [i for i, p in enumerate(nodes) if p == (10.0, 10.0)][0]
        try:
            mesher.boundary_map(tris, [("diagonal", [corner, far])])
        except mesher.BoundaryError as e:
            assert "RF-3" in str(e)
        else:
            raise AssertionError("not refused")


class TestToTheEngine:
    def test_valid_with_the_materials_where_the_mesh_says(self):
        mesh = _tunnel_mesh(True)
        stage = em.Stage(active=(True,) * len(mesh.elements))
        model = mesher.to_engine(mesh, (VOID, ROCK), (stage,))
        assert model.element_material == mesh.element_material != mesh.element_region
        assert model.nodes == mesh.nodes and model.elements == mesh.elements
        try:
            mesher.to_engine(mesh, (VOID,), (stage,))         # material 1 missing
        except em.InputError as e:
            assert "element_material" in {p.rule for p in e.problems}
        else:
            raise AssertionError("not refused")

    def test_a_pressure_on_the_hole_is_a_closed_contour(self):
        for six in (False, True):
            mesh = _tunnel_mesh(six)
            p = 2.0
            loads = []
            for found in mesh.boundary("hole").sides:
                for e, k in found:
                    if mesh.element_region[e] == 0:            # the rock's side
                        loads.append(em.EdgeLoad(e, k, (-p, 0.0), (-p, 0.0), normal=True))
            fixed = sorted({i for i, x in enumerate(mesh.nodes)
                            if max(abs(x[0]), abs(x[1])) == 10.0})
            stage = em.Stage(active=tuple(r == 0 for r in mesh.element_region),
                             restraints=tuple(em.Restraint(n, True, True) for n in fixed),
                             edge_loads=tuple(loads), tolerance=1e-12)
            out = analysis.run(mesher.to_engine(mesh, (VOID, ROCK), (stage,)))[0]
            rx = sum(r[0] for r in out.reactions.values())
            ry = sum(r[1] for r in out.reactions.values())
            assert abs(rx) <= 1e-9 * p * 2 * math.pi and abs(ry) <= 1e-9 * p * 2 * math.pi, (rx, ry)
            for n in mesh.boundary("hole").nodes:
                x, y = mesh.nodes[n]
                ur = (out.displacement[2 * n] * x + out.displacement[2 * n + 1] * y)
                assert ur > 0.0, (n, ur)
