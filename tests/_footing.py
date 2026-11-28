# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The strip footing of case 008 (ficha VER-STR-05; spec 007, D6), built for the
engine, in its two variants (not a test file: the runner only collects
test_*.py).

The model (validacion/casos/008-prandtl-zapata-tresca/caso.md): half of a
weightless medium by symmetry, 0 <= x <= W, -D <= y <= 0, y up, the surface
at y = 0; a strip of half-width b = 3 m; Tresca (Mohr-Coulomb with phi =
psi = 0), E = 250 MPa, nu = 0.2, c = 0.1 MPa; u = 0 on x = 0 and x = W, u = v
= 0 on y = -D.

* variant (a), ``rigid``: the surface nodes with 0 <= x <= b move down
  together (v imposed, in totals), free in x (smooth); one stage per
  settlement; the mean pressure of a stage is minus the sum of the vertical
  reactions of those nodes over b;
* variant (b), ``flexible``: a uniform pressure q on 0 <= x <= b (normal
  edge load), one stage per level, in totals.

Signs: the engine is tension-positive with y up (spec 001, D1); the case
gives pressures and settlements positive downward. The conversion is here,
in ``pressure`` and in the sign of the imposed v and of the edge load.

The mesh (case 008, esperado.json, "malla"): mesh_structured.rectangle on
lines with cells of h0 on 0 <= x <= b and geometric growth g beyond, to W;
in depth, geometric from h0 at the surface to D; alternate diagonals, as
case 004.

The solver settings of a stage come as a dict of engine Stage fields
(tolerance, max_iterations, steps, max_cuts, factors, automatic).
"""
from __future__ import annotations

import math

import _strip
from ogr_fem2d.engine import analysis
from ogr_fem2d.engine import model as m
from ogr_fem2d.engine.mesh_structured import rectangle
from ogr_fem2d.engine.reference.elastic import Elastic
from ogr_fem2d.engine.reference import solver
from ogr_fem2d.engine.reference.mohr_coulomb import MohrCoulomb

B = 3.0                                   # half-width of the strip, m
E, NU, C = 250.0, 0.2, 0.1                # MPa
P_LIM = (2.0 + math.pi) * C               # de Souza Neto et al. 2008, Eq. (7.178)
TRESCA = MohrCoulomb(E, NU, C, 0.0, 0.0)
#: the settings of the studies (esperado.json, "fases_de_los_estudios")
STUDY = dict(tolerance=1e-10, max_iterations=25, steps=5, max_cuts=8)


def mesh_for(w: float, d: float, h0: float, growth: float):
    xs = _strip.lines(0.0, B, h0, 1.0) + _strip.lines(B, w, h0, growth)[1:]
    zs = _strip.lines(0.0, d, h0, growth)
    return rectangle(xs, sorted(-z for z in zs), 6, "alternate")


def footing_nodes(mesh) -> list[int]:
    """The surface nodes under the strip, 0 <= x <= b."""
    return [n for n in mesh.boundary["top"] if mesh.nodes[n][0] <= B * (1 + 1e-12)]


def _restraints(mesh, free_top: set[int] = frozenset()) -> tuple[m.Restraint, ...]:
    held: dict[int, list[bool]] = {}

    def hold(nodes, x, y):
        for n in nodes:
            flags = held.setdefault(n, [False, False])
            flags[0], flags[1] = flags[0] or x, flags[1] or y

    hold(mesh.boundary["left"], True, False)             # symmetry
    hold(mesh.boundary["right"], True, False)
    hold(mesh.boundary["bottom"], True, True)
    return tuple(m.Restraint(n, x, y) for n, (x, y) in sorted(held.items()))


def _model(mesh, material, stages) -> m.EngineModel:
    return m.EngineModel(m.PLANE_STRAIN, tuple(mesh.nodes), tuple(mesh.elements),
                         (m.Material(material),), (0,) * len(mesh.elements), tuple(stages))


def rigid(mesh, settlements, settings=None, material=TRESCA) -> m.EngineModel:
    """Variant (a): one stage per TOTAL settlement (positive downward)."""
    settings = dict(STUDY if settings is None else settings)
    restraints, top = _restraints(mesh), footing_nodes(mesh)
    active = (True,) * len(mesh.elements)
    stages = [m.Stage(active=active, restraints=restraints,
                      imposed=tuple(m.ImposedDisplacement(n, 1, -delta) for n in top),
                      **settings)
              for delta in settlements]
    return _model(mesh, material, stages)


def flexible(mesh, pressures, settings=None, material=TRESCA) -> m.EngineModel:
    """Variant (b): one stage per TOTAL pressure q (positive downward)."""
    settings = dict(STUDY if settings is None else settings)
    restraints = _restraints(mesh)
    under = [(e, side) for e, side in mesh.boundary_sides["top"]
             if max(mesh.nodes[mesh.elements[e][k]][0] for k in (side, (side + 1) % 3))
             <= B * (1 + 1e-12)]
    active = (True,) * len(mesh.elements)
    stages = [m.Stage(active=active, restraints=restraints,
                      edge_loads=tuple(m.EdgeLoad(e, side, (-q, 0.0), (-q, 0.0), normal=True)
                                       for e, side in under),
                      **settings)
              for q in pressures]
    return _model(mesh, material, stages)


def pressure(mesh, outcome) -> float:
    """The mean pressure under the rigid strip, positive downward: minus the
    vertical reactions of its nodes, over b."""
    return -sum(outcome.reactions[n][1] for n in footing_nodes(mesh)) / B


def settlement(mesh, outcome) -> float:
    """The settlement at the axis, under the centre of the strip (the node
    (0, 0)), positive downward."""
    axis = next(n for n in mesh.boundary["top"] if mesh.nodes[n][0] == 0.0)
    return -outcome.displacement[2 * axis + 1]


def elastic_settlement(mesh, variant) -> float:
    """delta_e: the settlement of the rigid strip under P = (2 + pi) c in
    elasticity (esperado.json, variant a), from one elastic stage with a unit
    settlement: the response is linear in it."""
    outcome = analysis.run(rigid(mesh, [1.0], dict(STUDY, steps=1), Elastic(E, NU)), variant)[0]
    return P_LIM / pressure(mesh, outcome)


def stages(model: m.EngineModel, variant, **kw):
    """The stages solved, and the failure of an increment that stopped the
    analysis (None if every stage was solved)."""
    out = []
    try:
        for outcome in analysis.stages(model, variant, **kw):
            out.append(outcome)
    except solver.INCREMENT_FAILURES as err:
        return out, err
    return out, None
