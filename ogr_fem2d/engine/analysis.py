# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The analysis: an EngineModel (model.py) solved stage after stage (spec 002,
RF-5 and RF-9; tasks T6 onwards).

For each stage it checks the input (model.validate), turns the TOTALS of the
stage into what the stage solver needs, and keeps the state from one stage to
the next:

* restraints: the degree of freedom does not move during the stage;
* imposed displacements (D2 of spec 001): the user gives the total at the
  end of the stage; the stage imposes the difference with the displacement
  it starts from;
* loads (D2): totals; the stage goes from the force its starting stresses
  balance to the total given (reference/solver.py);
* the axis (spec 002, D1 bis): in axisymmetry every node at x = r = 0 has
  u_r = 0 by symmetry, and the engine holds it whether or not the user did;
  the result lists those nodes (rule 12: a default that changes the result
  goes with it);
* restraints that are not enough: before solving, the rigid-body motions of
  the analysis (in plane strain the two translations and the rotation; in
  axisymmetry only the axial translation, Zienkiewicz and Taylor 2000,
  §5.2.2) are checked against the restrained and imposed degrees of
  freedom; a motion they do not stop is reported by name, and no result is
  given. A mechanism of the mesh itself would only show as a singular
  matrix, which the linear solver reports;
* a stage that changes nothing (no load, nothing imposed beyond the
  starting state) is not solved: its state is the previous one, and the
  result says so (``solved``).

Not yet (spec 002): edge and point loads and self weight (T7), and elements
that are not active (T9): the engine refuses them with the task that brings
them, rather than ignoring them.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import interface
from .model import AXISYMMETRIC, EngineModel, validate
from .reference import solver

Stress = tuple[float, float, float, float]


class InsufficientRestraintError(ValueError):
    """The restraints of a stage leave a rigid-body motion free."""

    def __init__(self, stage: int, motions: list[str]):
        self.stage, self.motions = stage, motions
        super().__init__(f"stage {stage}: the restraints leave the model free to move: "
                         + "; ".join(motions))


@dataclass
class StageOutcome:
    """The state at the end of a stage, in totals."""
    displacement: list[float]                  # 2 per node
    stresses: list[Stress]                     # per integration point
    #: node -> (R_x, R_y) on every node with a restrained or imposed dof,
    #: R = f_int - f_ext (0 in a free component)
    reactions: dict[int, tuple[float, float]]
    plastic: list[bool]
    #: nodes of the axis held in u_r by the engine (D1 bis), axisymmetry
    axis_held: tuple[int, ...] = ()
    #: False when the stage changed nothing and was not solved
    solved: bool = True
    history: list[tuple[int, int, float]] = field(default_factory=list)
    steps: int = 0
    tolerance: float = 0.0
    cuts: int = 0


def _not_yet(m: EngineModel) -> None:
    if any(mat.unit_weight for mat in m.materials):
        raise NotImplementedError("self weight arrives in spec 002, T7")
    for i, s in enumerate(m.stages):
        if s.point_loads or s.edge_loads:
            raise NotImplementedError(f"stage {i}: point and edge loads arrive in spec 002, T7")
        if not all(s.active):
            raise NotImplementedError(f"stage {i}: inactive elements arrive in spec 002, T9")


def axis_nodes(m: EngineModel) -> tuple[int, ...]:
    """Nodes on the axis, x = r = 0 exactly (D1 bis); none in plane strain."""
    if m.analysis != AXISYMMETRIC:
        return ()
    return tuple(n for n, (x, _) in enumerate(m.nodes) if x == 0.0)


def free_motions(m: EngineModel, constrained: set[int]) -> list[str]:
    """The rigid-body motions the ``constrained`` dofs do not stop, by name.

    Each motion is a vector over the dofs; the constrained dofs stop the
    combinations that are non-zero on at least one of them. The free ones
    are the null space of the motions restricted to the constrained dofs."""
    nodes = np.array(m.nodes, dtype=float)
    n = len(nodes)
    if m.analysis == AXISYMMETRIC:
        modes = [np.tile([0.0, 1.0], n)]
    else:
        centre = nodes.mean(axis=0)
        rotation = np.zeros(2 * n)
        rotation[0::2] = -(nodes[:, 1] - centre[1])
        rotation[1::2] = nodes[:, 0] - centre[0]
        modes = [np.tile([1.0, 0.0], n), np.tile([0.0, 1.0], n), rotation]
    basis = np.array(modes).T                       # (2n, k)
    rows = sorted(constrained)
    held = basis[rows] if rows else np.zeros((0, basis.shape[1]))
    scale = np.abs(basis).max()
    if held.shape[0]:
        _, sv, vt = np.linalg.svd(held)
        rank = int(np.sum(sv > 1e-10 * scale))
        null = vt[rank:]
    else:
        null = np.eye(basis.shape[1])
    out = []
    for v in null:
        if m.analysis == AXISYMMETRIC:
            out.append("translation along the axis (y = z)")
            continue
        a, b, c = v
        if abs(c) < 1e-10 * max(abs(a), abs(b), abs(c)):
            out.append(f"translation along ({a / np.hypot(a, b):+.3f}, {b / np.hypot(a, b):+.3f})")
        else:
            # u = a - c (y - yc), v = b + c (x - xc): at rest at this point
            xc, yc = nodes.mean(axis=0)
            out.append(f"rotation about ({xc - b / c:.6g}, {yc + a / c:.6g})")
    return out


def _reactions(result_reactions: dict[int, float]) -> dict[int, tuple[float, float]]:
    out: dict[int, list[float]] = {}
    for dof, value in result_reactions.items():
        out.setdefault(dof // 2, [0.0, 0.0])[dof % 2] = value
    return {n: (r[0], r[1]) for n, r in sorted(out.items())}


def run(m: EngineModel, variant: interface.Variant = solver.REFERENCE) -> list[StageOutcome]:
    """Every stage of ``m``, in order. The input is validated first
    (model.InputError with every problem); then each stage is solved from the
    end of the previous one."""
    validate(m)
    _not_yet(m)
    n_dofs = 2 * len(m.nodes)
    laws = [m.materials[k].law for k in m.element_material]
    axis = axis_nodes(m)
    stresses = (list(m.initial_stresses) if m.initial_stresses is not None
                else [(0.0, 0.0, 0.0, 0.0)] * m.n_points)
    displacement = np.zeros(n_dofs)
    outcomes = []
    for i, stage in enumerate(m.stages):
        imposed_total = {2 * d.node + d.component: d.value for d in stage.imposed}
        held = {2 * r.node + c for r in stage.restraints
                for c, on in ((0, r.x), (1, r.y)) if on}
        held |= {2 * n for n in axis}
        held -= set(imposed_total)
        free = free_motions(m, held | set(imposed_total))
        if free:
            raise InsufficientRestraintError(i, free)
        load = np.zeros(n_dofs)
        for f in stage.nodal_loads:
            load[2 * f.node] += f.fx
            load[2 * f.node + 1] += f.fy
        engine_model = solver.Model(list(m.nodes), list(m.elements), laws,
                                    frozenset(held), m.analysis)
        increments = {dof: value - displacement[dof] for dof, value in imposed_total.items()}
        try:
            result = solver.solve_stage(engine_model, stresses, list(load), stage.steps,
                                        stage.tolerance, stage.max_iterations,
                                        stage.max_cuts, variant, increments)
        except solver.NoLoadError:
            # nothing changes: the state stays; its reactions are recomputed
            points = solver.integration_points(engine_model)
            f_int = solver.internal_forces(points, stresses, n_dofs)
            constrained = held | set(imposed_total)
            reactions = {dof: f_int[dof] - load[dof] for dof in sorted(constrained)}
            outcomes.append(StageOutcome([float(u) for u in displacement], list(stresses),
                                         _reactions(reactions),
                                         [False] * len(stresses), axis, solved=False,
                                         steps=stage.steps, tolerance=stage.tolerance))
            continue
        displacement = displacement + np.array(result.displacement)
        stresses = result.stresses
        outcomes.append(StageOutcome([float(u) for u in displacement], list(stresses),
                                     _reactions(result.reactions), result.plastic, axis,
                                     True, result.history, result.steps, result.tolerance,
                                     result.cuts))
    return outcomes
