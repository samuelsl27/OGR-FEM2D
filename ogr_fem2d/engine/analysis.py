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
  balance to the total given (reference/solver.py). Nodal, point and edge
  loads and the self weight of the active elements are turned into
  consistent nodal forces by reference/loads.py (T7); a point load outside
  its element is reported with its stage and element;
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
  result says so (``solved``);
* excavation (RF-8, T9): each stage is solved on its ACTIVE elements only.
  The stresses of the elements that stay are those at the end of the
  previous stage, and their internal forces no longer balance the external
  ones where the removed elements were: that out-of-balance is the load of
  the excavation, the initial-stress term of Zienkiewicz and Taylor (2000),
  Eq. (2.13b), with nothing to compute apart. Nodes left without an active
  element leave the system: they keep the displacement they had, and the
  result lists them (``removed_nodes``); the stresses of inactive elements
  are None. An element that becomes active again is refused: the state it
  would come back with (construction, backfill) is not defined by any spec
  yet.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import interface
from .model import AXISYMMETRIC, EngineModel, validate
from .reference import loads, solver
from .reference.quadrature import rule_for

Stress = tuple[float, float, float, float]


class LoadError(ValueError):
    """A load that cannot be applied where it was given."""

    def __init__(self, stage: int, element: int, reason: str):
        self.stage, self.element, self.reason = stage, element, reason
        super().__init__(f"stage {stage}, load on element {element}: {reason}")


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
    #: per integration point; None for the points of inactive elements
    stresses: list[Stress | None]
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
    #: the elements of the stage, and the nodes left without any (T9)
    active: tuple[bool, ...] = ()
    removed_nodes: tuple[int, ...] = ()


def _not_yet(m: EngineModel) -> None:
    for e in range(len(m.elements)):
        flags = [s.active[e] for s in m.stages]
        if any(not a and b for a, b in zip(flags, flags[1:])):
            raise NotImplementedError(
                f"element {e} becomes active again: the state it would come back with "
                "(construction, backfill) is not defined yet (spec 002, T9)")


def axis_nodes(m: EngineModel) -> tuple[int, ...]:
    """Nodes on the axis, x = r = 0 exactly (D1 bis); none in plane strain."""
    if m.analysis != AXISYMMETRIC:
        return ()
    return tuple(n for n, (x, _) in enumerate(m.nodes) if x == 0.0)


def free_motions(coordinates: list[tuple[float, float]], analysis: str,
                 constrained: set[int]) -> list[str]:
    """The rigid-body motions the ``constrained`` dofs (of the nodes at
    ``coordinates``) do not stop, by name.

    Each motion is a vector over the dofs; the constrained dofs stop the
    combinations that are non-zero on at least one of them. The free ones
    are the null space of the motions restricted to the constrained dofs."""
    nodes = np.array(coordinates, dtype=float)
    n = len(nodes)
    if analysis == AXISYMMETRIC:
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
        if analysis == AXISYMMETRIC:
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


def stage_load(m: EngineModel, i: int) -> np.ndarray:
    """The TOTAL external force of stage ``i``, one value per dof: its nodal,
    point and edge loads and the self weight of its active elements, as
    consistent nodal forces (reference/loads.py)."""
    stage = m.stages[i]
    axi = m.analysis == AXISYMMETRIC
    shape = solver.SHAPES[m.nodes_per_element]
    rule = rule_for(m.nodes_per_element, m.analysis)
    f = np.zeros(2 * len(m.nodes))

    def add(nodes, forces):
        for n, (fx, fy) in zip(nodes, forces):
            f[2 * n] += fx
            f[2 * n + 1] += fy

    for load in stage.nodal_loads:
        add((load.node,), ((load.fx, load.fy),))
    for e, element in enumerate(m.elements):
        weight = m.materials[m.element_material[e]].unit_weight
        if stage.active[e] and weight:
            xy = [m.nodes[n] for n in element]
            add(element, loads.body_forces(shape, xy, (0.0, -weight), rule, axi))
    for p in stage.point_loads:
        element = m.elements[p.element]
        if axi and p.x == 0.0 and p.fx != 0.0:
            raise LoadError(i, p.element, "a radial force on the axis (D1 bis)")
        try:
            forces = loads.point_forces(shape, [m.nodes[n] for n in element],
                                        p.x, p.y, p.fx, p.fy)
        except ValueError as err:
            raise LoadError(i, p.element, str(err)) from None
        add(element, forces)
    for q in stage.edge_loads:
        element = m.elements[q.element]
        nodes = [element[k] for k in loads.side_nodes(len(element), q.side)]
        add(nodes, loads.edge_forces([m.nodes[n] for n in nodes], q.start, q.end,
                                     q.normal, axi))
    return f


def _reactions(result_reactions: dict[int, float], used: list[int]
               ) -> dict[int, tuple[float, float]]:
    """node -> (R_x, R_y), from the reactions of the stage's system, whose
    node k is the model's node used[k]."""
    out: dict[int, list[float]] = {}
    for dof, value in result_reactions.items():
        out.setdefault(used[dof // 2], [0.0, 0.0])[dof % 2] = float(value)
    return {n: (r[0], r[1]) for n, r in sorted(out.items())}


def run(m: EngineModel, variant: interface.Variant = solver.REFERENCE) -> list[StageOutcome]:
    """Every stage of ``m``, in order. The input is validated first
    (model.InputError with every problem); then each stage is solved, on its
    active elements, from the end of the previous one."""
    validate(m)
    _not_yet(m)
    laws = [m.materials[k].law for k in m.element_material]
    per_element = m.n_points // len(m.elements)
    axis = set(axis_nodes(m))
    stresses: list[Stress | None] = (list(m.initial_stresses) if m.initial_stresses is not None
                                     else [(0.0, 0.0, 0.0, 0.0)] * m.n_points)
    displacement = np.zeros(2 * len(m.nodes))
    outcomes = []
    for i, stage in enumerate(m.stages):
        # the stage's system: its active elements and their nodes, renumbered
        active = [e for e in range(len(m.elements)) if stage.active[e]]
        used = sorted({n for e in active for n in m.elements[e]})
        local = {n: k for k, n in enumerate(used)}
        dofs = np.array([2 * n + c for n in used for c in (0, 1)], dtype=np.int64)
        local_dof = {2 * n + c: 2 * k + c for n, k in local.items() for c in (0, 1)}
        points = [g for e in active for g in range(e * per_element, (e + 1) * per_element)]

        imposed_total = {2 * d.node + d.component: d.value for d in stage.imposed}
        held = {2 * r.node + c for r in stage.restraints
                for c, on in ((0, r.x), (1, r.y)) if on and r.node in local}
        held |= {2 * n for n in axis if n in local}
        held -= set(imposed_total)
        constrained = {local_dof[d] for d in held | set(imposed_total)}
        free = free_motions([m.nodes[n] for n in used], m.analysis, constrained)
        if free:
            raise InsufficientRestraintError(i, free)

        load = stage_load(m, i)[dofs]
        engine_model = solver.Model([m.nodes[n] for n in used],
                                    [tuple(local[n] for n in m.elements[e]) for e in active],
                                    [laws[e] for e in active],
                                    frozenset(local_dof[d] for d in held), m.analysis)
        start = [stresses[g] for g in points]
        increments = {local_dof[d]: value - displacement[d] for d, value in imposed_total.items()}
        removed = tuple(n for n in range(len(m.nodes)) if n not in local)
        try:
            result = solver.solve_stage(engine_model, start, list(load), stage.steps,
                                        stage.tolerance, stage.max_iterations,
                                        stage.max_cuts, variant, increments)
        except solver.NoLoadError:
            # nothing changes: the state stays; its reactions are recomputed
            f_int = solver.internal_forces(solver.integration_points(engine_model), start,
                                           len(dofs))
            reactions = {d: f_int[d] - load[d] for d in sorted(constrained)}
            stresses = [stresses[g] if stage.active[g // per_element] else None
                        for g in range(m.n_points)]
            outcomes.append(StageOutcome(
                [float(u) for u in displacement], list(stresses), _reactions(reactions, used),
                [False] * m.n_points, tuple(sorted(axis & set(used))), False,
                steps=stage.steps, tolerance=stage.tolerance,
                active=tuple(stage.active), removed_nodes=removed))
            continue
        displacement[dofs] += np.array(result.displacement)
        new: list[Stress | None] = [None] * m.n_points
        plastic = [False] * m.n_points
        for g, s, yielded in zip(points, result.stresses, result.plastic):
            new[g], plastic[g] = s, yielded
        stresses = new
        outcomes.append(StageOutcome(
            [float(u) for u in displacement], list(stresses),
            _reactions(result.reactions, used), plastic, tuple(sorted(axis & set(used))),
            True, result.history, result.steps, result.tolerance, result.cuts,
            tuple(stage.active), removed))
    return outcomes
