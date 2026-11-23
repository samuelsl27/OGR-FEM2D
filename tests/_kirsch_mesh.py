# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The circular hole of case 005 with the general mesh of spec 003, built for
the engine, and the comparisons of the case and of its identity (not a test
file: the runner only collects test_*.py).

The model (validacion/casos/005-kirsch-malla-general/caso.md): a square of
half-side L = 100 m with a hole of radius a = 1 m at its centre, in four
arcs, the hole being a region of its own (the excavation); the whole model,
no symmetry; six-node triangles of the graded mesh, B = sqrt(2), with a
window |x|, |y| <= 3 a of size h around the hole and 4 ceil(pi / 2h) nodes
on the hole (at least 36, D15), so that its pieces are no longer than h.
Decided by the owner on 2026-11-23: the graded mesh alone, with the hole's
nodes as the only control, does not converge to 0.5 % (its elements grow in
proportion to the distance to the hole, whatever the hole's divisions; the
study is in the changelog v0.0.8, T15). E = 10 000 MPa, nu = 0.2. Every integration
point starts at the field stress; one stage with the excavation's elements
inactive and nothing else acting, so the hole is left free:

* **the case**: hydrostatic 30 MPa of compression (sigma_zz included), the
  outer square fixed in both directions;
* **the identity**: the field sigma_1 along x, sigma_2 along y, and on the
  outer square, its corners and mid-side nodes, the displacement the
  excavation causes in the infinite medium (``engine_displacement`` of
  spec 003's closed forms). Its exact solution is Kirsch's: what it
  measures is the discretization alone.

The comparisons, at the worst point (D12): sigma_theta at every integration
point on r = a (the rule of the six-node triangle in plane strain puts one
at the middle of each side, on the circle) and u_r at every node on r = a,
corners and mid-side nodes, each relative to the value of Kirsch at that
point (8.113)-(8.116) and ``kirsch_induced_displacement``.

Signs: the engine is tension-positive with u along +x, +y; Kirsch's forms
are compression-positive with u_r inward. The conversion is here, in one
place (``tests/_hole.py`` does it for case 001).
"""
from __future__ import annotations

import math

from _kirsch import closed
from ogr_fem2d.engine import analysis
from ogr_fem2d.engine import initial_stress as ini
from ogr_fem2d.engine import model as em
from ogr_fem2d.engine.reference.elastic import Elastic
from ogr_fem2d.mesh import geometry as g
from ogr_fem2d.mesh import mesher

A, HALF = closed.A, 100.0
WINDOW = 3.0 * A
E, NU, P0 = closed.E, closed.NU, closed.P0

#: the hole's arcs, in the direction of the rock's hole (clockwise)
HOLE = ("segment 4-7", "segment 7-6", "segment 6-5", "segment 5-4")
OUTER = ("segment 0-1", "segment 1-2", "segment 2-3", "segment 3-0")


def hole_nodes(h: float) -> int:
    """4 ceil(pi a / 2h), at least 36: pieces of the hole no longer than h
    along the arc."""
    return max(36, 4 * math.ceil(math.pi * A / (2.0 * h)))


def geometry(h: float, max_size: float | None = None, half: float = HALF) -> g.MeshInput:
    pts = ((-half, -half), (half, -half), (half, half), (-half, half),
           (A, 0.0), (0.0, A), (-A, 0.0), (0.0, -A))
    rock = g.Region((0, 1, 2, 3), holes=((4, 7, 6, 5),), material=0)
    hole = g.Region((4, 5, 6, 7), material=1)
    arcs = tuple(g.SegmentSpec(a, b, arc=g.Arc((0.0, 0.0)), excavation=True)
                 for a, b in ((4, 5), (5, 6), (6, 7), (7, 4)))
    w = WINDOW
    window = g.Window(((-w, -w), (w, -w), (w, w), (-w, w)), h)
    return g.MeshInput("plane_strain", pts, (rock, hole), arcs,
                       g.MeshSettings(boundary_nodes=hole_nodes(h), max_size=max_size,
                                      windows=(window,)))


def _nodes_of(mesh, names) -> list[int]:
    out = []
    for name in names:
        b = mesh.boundary(name)
        out += list(b.nodes) + list(b.mids)
    return sorted(set(out))


def _model(mesh, s1, s2, sz, stage) -> em.EngineModel:
    law = Elastic(E, NU)
    base = em.EngineModel("plane_strain", mesh.nodes, mesh.elements,
                          (em.Material(law), em.Material(law)), mesh.element_material,
                          (stage,))
    field = ini.constant_field(base, s1, s2, sz, 0.0)
    return em.EngineModel(base.analysis, base.nodes, base.elements, base.materials,
                          base.element_material, base.stages, field)


def _active(mesh):
    return tuple(r == 0 for r in mesh.element_region)


def run_case(mesh):
    """The case: hydrostatic P0, the outer square fixed."""
    restraints = tuple(em.Restraint(n, True, True) for n in _nodes_of(mesh, OUTER))
    stage = em.Stage(active=_active(mesh), restraints=restraints, tolerance=1e-10,
                     max_iterations=5)
    model = _model(mesh, P0, P0, P0, stage)
    return model, analysis.run(model)[0]


def run_identity(mesh, s1, s2):
    """The identity: sigma_1 along x, sigma_2 along y (compression
    positive), the induced displacement imposed on the outer square."""
    imposed = []
    for n in _nodes_of(mesh, OUTER):
        ux, uy = closed.engine_displacement(*mesh.nodes[n], s1, s2)
        imposed += [em.ImposedDisplacement(n, 0, ux), em.ImposedDisplacement(n, 1, uy)]
    stage = em.Stage(active=_active(mesh), imposed=tuple(imposed), tolerance=1e-10,
                     max_iterations=5)
    # sigma_zz plays no part in the plane of an elastic analysis
    model = _model(mesh, max(s1, s2), min(s1, s2), 0.5 * (s1 + s2), stage)
    if s1 < s2:
        raise ValueError("sigma_1 along x is the larger one here")
    return model, analysis.run(model)[0]


def worst_errors(mesh, model, outcome, s1, s2) -> dict:
    """The worst relative error of sigma_theta at the integration points on
    r = a and of u_r at the nodes on r = a, against Kirsch, with where."""
    points = ini.integration_point_coordinates(model)
    sig = []
    for (x, y), stress in zip(points, outcome.stresses):
        r = math.hypot(x, y)
        if stress is None or abs(r - A) > 1e-9 * A:
            continue
        theta = math.atan2(y, x)
        c, s = x / r, y / r
        sxx, syy, _szz, txy = stress
        sigma_t = -(sxx * s * s + syy * c * c - 2.0 * txy * s * c)
        want = closed.kirsch_stress(A, theta, s1, s2)[1]
        sig.append((sigma_t / want - 1.0, (x, y)))
    ur = []
    for n in _nodes_of(mesh, HOLE):
        x, y = mesh.nodes[n]
        r, theta = math.hypot(x, y), math.atan2(y, x)
        got = -(outcome.displacement[2 * n] * x + outcome.displacement[2 * n + 1] * y) / r
        want = closed.kirsch_induced_displacement(r, theta, s1, s2)[0]
        ur.append((got / want - 1.0, (x, y)))
    worst_s = max(sig, key=lambda t: abs(t[0]))
    worst_u = max(ur, key=lambda t: abs(t[0]))
    return {"sigma_theta": worst_s[0], "sigma_theta_at": worst_s[1], "n_sigma": len(sig),
            "u_r": worst_u[0], "u_r_at": worst_u[1], "n_u": len(ur)}
