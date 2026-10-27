# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
One stage of a static analysis: load steps, full Newton-Raphson equilibrium
iterations with the consistent tangent, and the convergence history (spec
001, RF-5 and RF-6; D7).

Sources:

* the stage load. Zienkiewicz, O. C. and Taylor, R. L. (2000). *The Finite
  Element Method*, 5th ed., vol. 1, Eqs. (2.12)-(2.13b), pp. 24-25: the nodal
  forces are q = K a + f with f containing + int B^T sigma0 dV, "the initial
  stress term", and when "an excavation is made in rock where known tectonic
  stresses exist a removal of material will cause a force imbalance which
  results from the above term". Here the mesh has no hole and every element
  starts at sigma0; the nodes of the hole carry no external force, so the
  imbalance -int B^T sigma0 is the load of the excavation.
* the incremental scheme. de Souza Neto, E. A., Perić, D. and Owen, D. R. J.
  (2008). *Computational Methods for Plasticity*, Wiley, §4.2, pp. 95-100:
  the incremental constitutive function, path-independent within one step,
  sigma_n+1 = sigma(alpha_n, eps_n+1) (Eq. 4.60), so every iteration
  integrates the stress again from the converged state of the step start
  with the whole step's strain increment (Box 4.2, steps vi-vii; Eqs.
  4.75-4.76); the residual r = f_int - f_ext (Eqs. 4.64, 4.72); the correction
  K_T du = -r (Eq. 4.71) with the tangent stiffness K_T assembled from the
  consistent tangent of every point (Eqs. 4.73, 4.80-4.81; Box 4.2, ii-iv);
  load steps as in Box 4.1 (p. 97); and the convergence check of Eq. (4.77),
  ||r|| / ||f_ext|| <= tol (p. 98). The tangent of the Mohr-Coulomb points is
  that of §8.2.4 (mohr_coulomb.py).

Why the full Newton and not the initial stiffness (spec 001, D7): with the
initial stiffness the Mohr-Coulomb cases needed thousands of iterations per
step, with a convergence factor that tended to 1 as the mesh was refined,
and a residual that then no longer bounds the error of the displacement
(changelog v0.0.1, task T7).

The first correction of each step starts from the converged state with no
strain increment: its consistent tangent is the elastic one (every point is
inside or on the surface, and the update with a zero increment is elastic),
so the elastic stiffness is factorised once and reused there. Every later
correction assembles and factorises K_T anew; with non-associated flow it is
not symmetric, and SuperLU solves it as it is.

Loads in totals (spec 001, D2): the stage receives the TOTAL external force at
its end. The engine takes the internal force of the starting stresses as the
force the stage starts from and goes, in n equal steps, from it to the total
given: step i aims at f_start + (i/n) (f_end - f_start). For the excavation,
f_end = 0 and f_end - f_start is the initial-stress term above.

What differs from Eq. (4.77): it divides by ||f_ext_n+1||, which at the end of
an excavation is zero (the hole is left free). The residual is divided by the
norm of the load of the stage, ||f_end - f_start||, the force the stage has to
take away, which is the scale every step's out-of-balance is measured against.

The tolerance and the step count are the caller's: they change the result,
and the result carries them (rule 12 of AGENTS.md).

Restraints: zero displacement on the listed degrees of freedom (the rollers
and the fixed outer boundary of the spec 001 cases). Imposed non-zero
displacements are not in this proof of concept.

The linear solve is SciPy's SuperLU (spec 001, "Fuera de alcance").
Everything per integration point is plain Python, written to be read: this
module is the oracle of the compiled variant (ADR-0001), and update_points()
is the one call per global iteration the compiled variant will replace.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu

from . import element_t6 as t6
from . import mohr_coulomb as mc
from .elastic import Elastic, plane_strain_matrix, stress_increment

Stress = tuple[float, float, float, float]      # sigma_xx, yy, zz, tau_xy


class StateUpdateError(mc.ReturnMappingError):
    """The stress update failed at one integration point (spec 001, RF-4)."""

    def __init__(self, element: int, point: int, step: int | None,
                 iteration: int | None, reason: str):
        self.element, self.point = element, point
        self.step, self.iteration = step, iteration
        self.reason = reason
        super().__init__(f"element {element}, integration point {point}, "
                         f"step {step}, iteration {iteration}: {reason}")


class NotConvergedError(RuntimeError):
    """A step did not reach the tolerance in the iterations allowed
    (spec 001, RF-6). No result is given; the history is."""

    def __init__(self, step: int, history: list[tuple[int, int, float]]):
        self.step, self.history = step, history
        last = history[-1][2] if history else float("nan")
        super().__init__(f"step {step} did not converge: relative residual "
                         f"{last:.3e} after {history[-1][1] if history else 0} "
                         "iterations")


@dataclass(frozen=True)
class Model:
    """What the engine receives (rule 11 of AGENTS.md): nodes, six-node
    elements, one material per element and the restrained degrees of
    freedom (2 n for x, 2 n + 1 for y of node n), all held at zero."""
    nodes: list[tuple[float, float]]
    elements: list[tuple[int, int, int, int, int, int]]
    materials: list[Elastic | mc.MohrCoulomb]
    restrained: frozenset[int]


@dataclass(frozen=True)
class IntegrationPoint:
    """What the iterations need of a point, computed once: the geometry does
    not change (small strain).

    The B matrix of t6.b_matrix is made of the derivatives of the six shape
    functions (Zienkiewicz and Taylor 2000, Eqs. 2.2-2.4): row eps_x has
    dN_a/dx under u_a, row eps_y has dN_a/dy under v_a, row gamma_xy has
    both. The point keeps those two lists, and strain() and the internal
    forces write B u and B^T sigma with them."""
    element: int
    index: int                         # 0, 1, 2 in t6.GAUSS_POINTS
    nodes: tuple[int, ...]             # the six nodes of its element
    dndx: tuple[float, ...]            # dN_a/dx, a = 1..6
    dndy: tuple[float, ...]            # dN_a/dy
    weight: float                      # w det J / 2, so int f dA = sum weight f
    xy: tuple[float, float]

    def strain(self, u: list[float]) -> tuple[float, float, float]:
        """(eps_x, eps_y, gamma_xy) = B u, u with 2 values per node."""
        ex = ey = gxy = 0.0
        for n, dx, dy in zip(self.nodes, self.dndx, self.dndy):
            ux, uy = u[2 * n], u[2 * n + 1]
            ex += dx * ux
            ey += dy * uy
            gxy += dy * ux + dx * uy
        return ex, ey, gxy


@dataclass
class StageResult:
    """The converged end of the stage."""
    displacement: list[float]                      # 2 per node, totals
    stresses: list[Stress]                         # per integration point
    #: plastic in the last step of the stage: the plastic zone of the end
    #: state (a point that yielded earlier and then unloaded is not in it)
    plastic: list[bool]
    points: list[IntegrationPoint]
    history: list[tuple[int, int, float]] = field(default_factory=list)
    #: The settings that change the result (rule 12).
    steps: int = 0
    tolerance: float = 0.0


def integration_points(model: Model) -> list[IntegrationPoint]:
    """Every point of every element, in element order, then GAUSS_POINTS
    order."""
    points = []
    for e, element in enumerate(model.elements):
        xy = [model.nodes[n] for n in element]
        where = t6.gauss_point_coordinates(xy)
        for g, ((l1, l2, l3), w) in enumerate(t6.GAUSS_POINTS):
            try:
                b, det = t6.b_matrix(xy, l1, l2, l3)
            except ValueError as err:
                raise ValueError(f"element {e}: {err}") from None
            points.append(IntegrationPoint(
                e, g, tuple(element),
                tuple(b[0][2 * a] for a in range(6)),       # dN_a/dx
                tuple(b[1][2 * a + 1] for a in range(6)),   # dN_a/dy
                w * det / 2.0, where[g]))
    return points


def stiffness(model: Model) -> coo_matrix:
    """K = assembly of int B^T D B dA, with the ELASTIC D of each element,
    element by element with t6.stiffness: the tangent of the first
    correction of every step."""
    rows, cols, values = [], [], []
    for element, material in zip(model.elements, model.materials):
        xy = [model.nodes[n] for n in element]
        k = t6.stiffness(xy, plane_strain_matrix(material.young,
                                                 material.poisson))
        dofs = [2 * n + c for n in element for c in (0, 1)]
        for r in range(12):
            for c in range(12):
                rows.append(dofs[r])
                cols.append(dofs[c])
                values.append(k[r][c])
    n = 2 * len(model.nodes)
    return coo_matrix((values, (rows, cols)), shape=(n, n))


def tangent_stiffness(points: list[IntegrationPoint],
                      tangents: list[list[list[float]]],
                      n_dofs: int) -> coo_matrix:
    """K_T = assembly of int B^T D B dA with the consistent tangent D of
    each point (Eq. 4.80). Block of nodes (a, b): weight B_a^T D B_b, with
    B_a = [[dN_a/dx, 0], [0, dN_a/dy], [dN_a/dy, dN_a/dx]]."""
    rows, cols, values = [], [], []
    for p, d in zip(points, tangents):
        for nb, bx, by in zip(p.nodes, p.dndx, p.dndy):
            # D B_b, columns for u_b and v_b
            dbu = (d[0][0] * bx + d[0][2] * by, d[1][0] * bx + d[1][2] * by,
                   d[2][0] * bx + d[2][2] * by)
            dbv = (d[0][1] * by + d[0][2] * bx, d[1][1] * by + d[1][2] * bx,
                   d[2][1] * by + d[2][2] * bx)
            for na, ax, ay in zip(p.nodes, p.dndx, p.dndy):
                # B_a^T rows: u_a -> (ax, 0, ay), v_a -> (0, ay, ax)
                for ra, (c0, c1, c2) in ((2 * na, (ax, 0.0, ay)),
                                         (2 * na + 1, (0.0, ay, ax))):
                    rows += [ra, ra]
                    cols += [2 * nb, 2 * nb + 1]
                    values += [p.weight * (c0 * dbu[0] + c1 * dbu[1] + c2 * dbu[2]),
                               p.weight * (c0 * dbv[0] + c1 * dbv[1] + c2 * dbv[2])]
    return coo_matrix((values, (rows, cols)), shape=(n_dofs, n_dofs))


def update_stress(material: Elastic | mc.MohrCoulomb, stress: Stress,
                  strain_increment: tuple[float, float, float]
                  ) -> tuple[Stress, bool, list[list[float]]]:
    """The incremental constitutive function (Eq. 4.60) of one point: the
    stress at the end of the increment, whether it is plastic, and the
    consistent tangent of that update (Eq. 4.81)."""
    if isinstance(material, mc.MohrCoulomb):
        result = mc.update(material, stress, strain_increment, tangent=True)
        return result.stress, result.region != "elastic", result.tangent
    d = stress_increment(material.young, material.poisson, strain_increment)
    return ((stress[0] + d[0], stress[1] + d[1], stress[2] + d[2],
             stress[3] + d[3]), False,
            plane_strain_matrix(material.young, material.poisson))


def internal_forces(points: list[IntegrationPoint], stresses: list[Stress],
                    n_dofs: int) -> list[float]:
    """f_int = assembly of int B^T sigma dA (Eq. 4.65; t6.internal_forces
    with the B of each point kept). sigma_zz does no work in plane strain."""
    f = [0.0] * n_dofs
    for p, (s_xx, s_yy, _s_zz, t_xy) in zip(points, stresses):
        for n, dx, dy in zip(p.nodes, p.dndx, p.dndy):
            # the two rows of B^T for node n: (dx, 0, dy) and (0, dy, dx)
            f[2 * n] += p.weight * (dx * s_xx + dy * t_xy)
            f[2 * n + 1] += p.weight * (dy * s_yy + dx * t_xy)
    return f


def update_points(points: list[IntegrationPoint], materials: list,
                  start: list[Stress], du: list[float]
                  ) -> tuple[list[Stress], list[float], list[bool], list]:
    """THE call per global iteration (ADR-0001): given the displacement
    increment of the step, the stress of every point from the converged
    state of the step start (Box 4.2, vi-vii), the internal forces
    (viii-ix) and the consistent tangent of every point (ii). Returns
    (stresses, f_int, plastic, tangents)."""
    stresses, plastic, tangents = [], [], []
    for p, s0 in zip(points, start):
        try:
            s, is_plastic, d = update_stress(materials[p.element], s0,
                                             p.strain(du))
        except mc.ReturnMappingError as err:
            raise StateUpdateError(p.element, p.index, None, None,
                                   str(err)) from None
        stresses.append(s)
        plastic.append(is_plastic)
        tangents.append(d)
    return (stresses, internal_forces(points, stresses, len(du)), plastic,
            tangents)


def _norm(v, free) -> float:
    return math.sqrt(sum(v[i] * v[i] for i in free))


def solve_stage(model: Model, initial_stresses: list[Stress],
                external_load: list[float], steps: int, tolerance: float,
                max_iterations: int) -> StageResult:
    """Solve one stage from ``initial_stresses`` (one per integration point,
    in integration_points() order; the displacements start at zero) to the
    TOTAL ``external_load`` (one value per dof; the restrained ones are
    reactions and are ignored).

    Raises NotConvergedError when a step does not reach ``tolerance`` in
    ``max_iterations`` solves, and StateUpdateError when a point cannot be
    updated: in neither case is a result given.
    """
    if steps < 1 or max_iterations < 1 or tolerance <= 0.0:
        raise ValueError("need steps >= 1, max_iterations >= 1, tolerance > 0")
    points = integration_points(model)
    if len(initial_stresses) != len(points):
        raise ValueError("one initial stress per integration point")
    n_dofs = 2 * len(model.nodes)
    free = [i for i in range(n_dofs) if i not in model.restrained]

    def factorise(matrix: coo_matrix):
        return splu(matrix.tocsr()[free][:, free].tocsc())

    elastic = factorise(stiffness(model))

    f_start = internal_forces(points, initial_stresses, n_dofs)
    load = [external_load[i] - f_start[i] for i in range(n_dofs)]
    scale = _norm(load, free)
    if scale == 0.0:
        raise ValueError("the stage has no load: nothing to solve")

    displacement = [0.0] * n_dofs
    converged = list(initial_stresses)
    plastic = [False] * len(points)
    history: list[tuple[int, int, float]] = []
    for step in range(1, steps + 1):
        target = [f_start[i] + step / steps * load[i] for i in range(n_dofs)]
        du = [0.0] * n_dofs
        # Iteration 0 is the step's start: its residual is the load added.
        f_int = internal_forces(points, converged, n_dofs)
        stresses, step_plastic = converged, [False] * len(points)
        solver = elastic            # the tangent with no strain increment
        for iteration in range(0, max_iterations + 1):
            # r = f_ext - f_int with the sign of the right-hand side of (4.71)
            r = [target[i] - f_int[i] for i in range(n_dofs)]
            relative = _norm(r, free) / scale
            history.append((step, iteration, relative))
            if iteration > 0 and relative <= tolerance:
                break
            if iteration == max_iterations:
                raise NotConvergedError(step, history)
            correction = solver.solve(np.array([r[i] for i in free]))
            for j, i in enumerate(free):
                du[i] += float(correction[j])
            try:
                stresses, f_int, step_plastic, tangents = update_points(
                    points, model.materials, converged, du)
            except StateUpdateError as err:
                raise StateUpdateError(err.element, err.point, step,
                                       iteration + 1, err.reason) from None
            if any(step_plastic):
                solver = factorise(tangent_stiffness(points, tangents, n_dofs))
            else:
                solver = elastic
        converged, plastic = stresses, step_plastic
        displacement = [u + d for u, d in zip(displacement, du)]

    return StageResult(displacement, converged, plastic, points, history,
                       steps, tolerance)
