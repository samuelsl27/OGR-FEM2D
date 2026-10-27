# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.2 (spec 002, T9) — stages and excavation by deactivating elements
(analysis.run; RF-8 and RF-9).

Invariants protected:

* **deactivating is excavating** (Zienkiewicz and Taylor 2000, Eq. 2.13b):
  a quarter annulus 0.5 <= r <= 5.5 under a hydrostatic field, its inner
  face held by the pressure of that field in a first stage (which is then
  in equilibrium and is not solved), and its inner ring 0.5 <= r <= 1
  deactivated in a second, ends where the annulus 1 <= r <= 5.5, with the
  same nodes, ends when its hole is opened in one stage (what spec 001 did
  with a mesh without the hole), to rounding: displacements and stresses,
  with three- and six-node triangles;
* **an excavated layer** (an open cut): removing the top 0.5 m of a
  laterally confined column in its gravitational field unloads the rest by
  gamma t, uniformly, so the column rises by gamma t y / M (M the
  constrained modulus) at height y, and its stresses become the
  gravitational field of the shorter column. Exact for both elements (the
  change is linear);
* **what leaves the system**: the nodes of the removed elements that touch
  no active element keep the displacement they had (non-zero, after a stage
  that moved them) and are listed; the stresses of the removed elements are
  None, the others are there; the elements of each stage are in the
  result; the reactions are those of the mesh without the ring, node by
  node, although the stage numbers its nodes on its own;
* **the self weight leaves with its elements**: the reaction at the bottom
  after the cut is the weight of what is left.
"""
from __future__ import annotations

import math

import _blocks
from ogr_fem2d.engine import analysis
from ogr_fem2d.engine import initial_stress as ini
from ogr_fem2d.engine import model as m
from ogr_fem2d.engine.mesh_radial import quarter_annulus
from ogr_fem2d.engine.reference.elastic import Elastic

E, NU, P0 = 10000.0, 0.2, 30.0
ROCK = m.Material(Elastic(E, NU))


def annulus(a, n_radial, six, b=5.5, n_theta=4):
    mesh = quarter_annulus(a, b, n_radial, n_theta, 1.0, 6 if six else 3)
    return mesh, [tuple(e) for e in mesh.elements]


def restraints(mesh):
    out = [m.Restraint(n, False, True) for n in mesh.x_axis if n not in mesh.outer]
    out += [m.Restraint(n, True, False) for n in mesh.y_axis if n not in mesh.outer]
    out += [m.Restraint(n, True, True) for n in mesh.outer]
    return tuple(out)


def inner_faces(mesh, elements, radius):
    """(element, side) of every side lying on r = radius."""
    out = []
    for e, element in enumerate(elements):
        for side in range(3):
            a, c = mesh.nodes[element[side]], mesh.nodes[element[(side + 1) % 3]]
            if abs(math.hypot(*a) - radius) < 1e-12 and abs(math.hypot(*c) - radius) < 1e-12:
                out.append((e, side))
    return out


def ring_model(six):
    """0.5 <= r <= 5.5 in 10 rings: stage 0 held, stage 1 without r < 1."""
    mesh, elements = annulus(0.5, 10, six)
    hold = tuple(m.EdgeLoad(e, side, (-P0, 0.0), (-P0, 0.0), normal=True)
                 for e, side in inner_faces(mesh, elements, 0.5))
    inner = tuple(all(math.hypot(*mesh.nodes[n]) <= 1.0 + 1e-12 for n in el[:3])
                  for el in elements)
    s0 = m.Stage(active=(True,) * len(elements), restraints=restraints(mesh), edge_loads=hold,
                 tolerance=1e-12)
    s1 = m.Stage(active=tuple(not x for x in inner), restraints=restraints(mesh), tolerance=1e-12)
    model = m.EngineModel(m.PLANE_STRAIN, tuple(map(tuple, mesh.nodes)), tuple(elements),
                          (ROCK,), (0,) * len(elements), (s0, s1))
    field = ini.constant_field(model, P0, P0, P0, 0.0)
    return mesh, elements, inner, m.EngineModel(model.analysis, model.nodes, model.elements,
                                                model.materials, model.element_material,
                                                model.stages, field)


def hole_model(six):
    """1 <= r <= 5.5 in 9 rings, the hole opened in one stage."""
    mesh, elements = annulus(1.0, 9, six)
    s = m.Stage(active=(True,) * len(elements), restraints=restraints(mesh), tolerance=1e-12)
    model = m.EngineModel(m.PLANE_STRAIN, tuple(map(tuple, mesh.nodes)), tuple(elements),
                          (ROCK,), (0,) * len(elements), (s,))
    field = ini.constant_field(model, P0, P0, P0, 0.0)
    return mesh, elements, m.EngineModel(model.analysis, model.nodes, model.elements,
                                         model.materials, model.element_material, model.stages,
                                         field)


class TestDeactivatingIsExcavating:

    def test_the_inner_ring_removed_equals_the_mesh_without_it(self):
        for six in (False, True):
            mesh_a, elements_a, inner, model_a = ring_model(six)
            mesh_b, elements_b, model_b = hole_model(six)
            held, dug = analysis.run(model_a)
            ref = analysis.run(model_b)[0]
            assert not held.solved and dug.solved
            # the same node of both meshes: by position
            where = {(round(x, 9), round(y, 9)): n for n, (x, y) in enumerate(mesh_a.nodes)}
            scale = max(abs(u) for u in ref.displacement)
            for n, (x, y) in enumerate(mesh_b.nodes):
                k = where[(round(x, 9), round(y, 9))]
                for c in (0, 1):
                    assert abs(dug.displacement[2 * k + c] - ref.displacement[2 * n + c]) \
                        < 1e-12 * scale, (six, n)
            # the stresses of the elements that stay, in the same order
            kept = [s for s in dug.stresses if s is not None]
            assert len(kept) == len(ref.stresses)
            assert max(abs(a - b) for s, t in zip(kept, ref.stresses)
                       for a, b in zip(s, t)) < 1e-11 * P0, six
            # what left: the nodes of the ring strictly inside r = 1
            gone = {n for n, xy in enumerate(mesh_a.nodes) if math.hypot(*xy) < 1.0 - 1e-12}
            assert set(dug.removed_nodes) == gone
            assert all(dug.displacement[2 * n] == held.displacement[2 * n] for n in gone)
            assert dug.active == tuple(not x for x in inner)
            # the reactions, node by node (the removed nodes are the first
            # of the numbering, so the stage's own numbers differ)
            assert min(gone) == 0
            for n, (rx, ry) in ref.reactions.items():
                k = where[tuple(round(c, 9) for c in mesh_b.nodes[n])]
                assert max(abs(rx - dug.reactions[k][0]), abs(ry - dug.reactions[k][1])) \
                    < 1e-11 * P0, (six, n)
            per = 3 if six else 1
            assert all((dug.stresses[g] is None) == inner[g // per] for g in range(len(dug.stresses)))


STRATUM = ini.Stratum(-1.0, 0.025, NU / (1 - NU), NU / (1 - NU))   # at rest: no lateral strain


class TestAnOpenCut:

    def test_removing_the_top_layer(self):
        h, cut, gamma = 2.0, 0.5, STRATUM.unit_weight
        modulus = E * (1 - NU) / ((1 + NU) * (1 - 2 * NU))
        for six in (False, True):
            b = _blocks.block(six, nx=2, ny=4, w=1.0, h=h)
            right = [n for n, (x, _) in enumerate(b.nodes) if x == 1.0]
            rs = tuple([m.Restraint(n, True, n in b.bottom()) for n in b.left() + right]
                       + [m.Restraint(n, False, True) for n in b.bottom()
                          if n not in b.left() + right])
            top = tuple(sum(b.nodes[n][1] for n in e[:3]) / 3 > h - cut for e in b.elements)
            soil = m.Material(Elastic(E, NU), unit_weight=gamma)
            s0 = m.Stage(active=(True,) * len(b.elements), restraints=rs, tolerance=1e-12)
            s1 = m.Stage(active=tuple(not t for t in top), restraints=rs, tolerance=1e-12)
            model = m.EngineModel(m.PLANE_STRAIN, tuple(b.nodes), tuple(b.elements), (soil,),
                                  (0,) * len(b.elements), (s0, s1))
            field = ini.gravitational_field(model, h, [STRATUM])
            model = m.EngineModel(model.analysis, model.nodes, model.elements, model.materials,
                                  model.element_material, model.stages, field)
            before, after = analysis.run(model)
            assert not before.solved
            points = ini.integration_point_coordinates(model)
            for (x, y), s in zip(points, after.stresses):
                if s is None:
                    continue
                want = ini.gravitational(y, h - cut, [STRATUM], m.PLANE_STRAIN)
                assert max(abs(a - c) for a, c in zip(s, want)) < 1e-14, (six, y, s, want)
            for n, (x, y) in enumerate(b.nodes):
                if n in after.removed_nodes:
                    assert after.displacement[2 * n + 1] == 0.0
                    continue
                assert abs(after.displacement[2 * n + 1] - gamma * cut * y / modulus) < 1e-17
                assert abs(after.displacement[2 * n]) < 1e-17
            bottom = sum(after.reactions[n][1] for n in b.bottom())
            assert abs(bottom - gamma * (h - cut) * 1.0) < 1e-13, (six, bottom)

    def test_removed_nodes_keep_what_they_had(self):
        b = _blocks.block(False, nx=2, ny=4, w=1.0, h=2.0)
        rs = tuple([m.Restraint(n, True, False) for n in b.left()]
                   + [m.Restraint(n, n in b.left(), True) for n in b.bottom()])
        top = tuple(sum(b.nodes[n][1] for n in e[:3]) / 3 > 1.5 for e in b.elements)
        corner = b.at(2, 4)                                  # top right, removed later
        s0 = m.Stage(active=(True,) * len(b.elements), restraints=rs, tolerance=1e-12,
                     nodal_loads=(m.NodalLoad(corner, 0.5, -1.0),))
        s1 = m.Stage(active=tuple(not t for t in top), restraints=rs, tolerance=1e-12)
        model = m.EngineModel(m.PLANE_STRAIN, tuple(b.nodes), tuple(b.elements), (ROCK,),
                              (0,) * len(b.elements), (s0, s1))
        loaded, dug = analysis.run(model)
        assert corner in dug.removed_nodes
        assert abs(loaded.displacement[2 * corner + 1]) > 1e-6
        for n in dug.removed_nodes:
            assert dug.displacement[2 * n:2 * n + 2] == loaded.displacement[2 * n:2 * n + 2]
