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

Automatic increment cutting (§5.4.3, pp. 123-124, and Fig. 5.2): when an
increment does not converge in the iterations allowed, or a point cannot be
updated (an iterate far from equilibrium can send a point to the apex, which
psi = 0 refuses), the increment is split into two equal halves and restarted
from the last converged state. It stops, and the error is raised, after
``max_cuts`` cuts in the stage. (Counting successive cuts only, as the text
of §5.4.3 does, never ends when the failure is tied to a load level and not
to the size of the increment: each converged half resets the count and the
last piece is halved again and again.) A cut changes the path, not the
equilibrium sought; the result says how many there were (rule 12).

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
module is the oracle of the other variants (ADR-0001). Through the interface
of ogr_fem2d.engine.interface (spec 001, T10), solve_stage() drives any
variant; ReferenceVariant is this module's, and update_points() is its one
call per global iteration.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu

from .. import interface
from . import element_t3 as t3
from . import element_t6 as t6
from . import mohr_coulomb as mc
from . import triangle
from .elastic import (Elastic, axisymmetric_matrix,
                      axisymmetric_stress_increment, plane_strain_matrix,
                      stress_increment)
from .quadrature import AXISYMMETRIC, PLANE_STRAIN, rule_for

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
    """An increment did not reach the tolerance in the iterations allowed
    (spec 001, RF-6). No result is given; the history is."""

    def __init__(self, step: int, history: list[tuple[int, int, float]]):
        self.step, self.history = step, history
        last = history[-1][2] if history else float("nan")
        super().__init__(f"step {step} did not converge: relative residual "
                         f"{last:.3e} after {history[-1][1] if history else 0} "
                         "iterations")


#: The shape of each element, by its number of nodes (spec 002, T4).
SHAPES = {3: t3, 6: t6}


@dataclass(frozen=True)
class Model:
    """What the engine receives (rule 11 of AGENTS.md): nodes, triangles of
    three or of six nodes (one kind per model), one material per element,
    the restrained degrees of freedom (2 n for x, 2 n + 1 for y of node n),
    all held at zero, and the analysis: plane strain, or axisymmetry with x
    the radius and y the axis (spec 002, T5)."""
    nodes: list[tuple[float, float]]
    elements: list[tuple[int, ...]]
    materials: list[Elastic | mc.MohrCoulomb]
    restrained: frozenset[int]
    analysis: str = PLANE_STRAIN

    @property
    def axisymmetric(self) -> bool:
        return self.analysis == AXISYMMETRIC


@dataclass(frozen=True)
class IntegrationPoint:
    """What the iterations need of a point, computed once: the geometry does
    not change (small strain).

    The B matrix of triangle.b_matrix is made of the derivatives of the
    shape functions (Zienkiewicz and Taylor 2000, Eqs. 2.2-2.4): row eps_x has
    dN_a/dx under u_a, row eps_y has dN_a/dy under v_a, row gamma_xy has
    both. The point keeps those two lists, and strain() and the internal
    forces write B u and B^T sigma with them.

    In axisymmetry (spec 002, T5) B has a fourth row, eps_theta = u / r
    (Zienkiewicz and Taylor 2000, Eqs. 5.5-5.6), with N_a / r under u_a:
    the point keeps those values too (``n_over_r``; empty in plane strain),
    and its weight is that of the ring, w det J / 2 times 2 pi r (Eq. 5.13).
    """
    element: int
    index: int                         # its place in the element's rule
    nodes: tuple[int, ...]             # the nodes of its element
    dndx: tuple[float, ...]            # dN_a/dx, a = 1..n
    dndy: tuple[float, ...]            # dN_a/dy
    weight: float                      # w det J / 2 (x 2 pi r), int f dV = sum weight f
    xy: tuple[float, float]
    n_over_r: tuple[float, ...] = ()   # N_a / r, axisymmetry only

    def strain(self, u: list[float]) -> tuple[float, ...]:
        """B u, u with 2 values per node: (eps_x, eps_y, gamma_xy) in plane
        strain; (eps_r, eps_z, eps_theta, gamma_rz) in axisymmetry."""
        ex = ey = gxy = 0.0
        for n, dx, dy in zip(self.nodes, self.dndx, self.dndy):
            ux, uy = u[2 * n], u[2 * n + 1]
            ex += dx * ux
            ey += dy * uy
            gxy += dy * ux + dx * uy
        if not self.n_over_r:
            return ex, ey, gxy
        et = sum(nr * u[2 * n] for n, nr in zip(self.nodes, self.n_over_r))
        return ex, ey, et, gxy


@dataclass
class StageResult:
    """The converged end of the stage."""
    displacement: list[float]                      # 2 per node, totals
    stresses: list[Stress]                         # per integration point
    #: plastic in the last step of the stage: the plastic zone of the end
    #: state (a point that yielded earlier and then unloaded is not in it)
    plastic: list[bool]
    points: list[IntegrationPoint]
    #: (increment, iteration, relative residual), every iteration tried,
    #: those of the increments that were cut included
    history: list[tuple[int, int, float]] = field(default_factory=list)
    #: (load factor at the start, at the end, "converged" or why it was cut)
    increments: list[tuple[float, float, str]] = field(default_factory=list)
    #: The settings that change the result, and the cuts made (rule 12).
    steps: int = 0
    tolerance: float = 0.0
    cuts: int = 0


def element_kind(model: Model):
    """(shape, rule) of the elements of ``model``: one kind per model, the
    rule of spec 002, D1."""
    kinds = {len(e) for e in model.elements}
    if len(kinds) != 1 or not kinds <= set(SHAPES):
        raise ValueError(f"elements with {sorted(kinds)} nodes: all must have "
                         "three or all six")
    n = kinds.pop()
    return SHAPES[n], rule_for(n, model.analysis)


def integration_points(model: Model) -> list[IntegrationPoint]:
    """Every point of every element, in element order, then in the order of
    the element's rule."""
    shape, rule = element_kind(model)
    axi = model.axisymmetric
    points = []
    for e, element in enumerate(model.elements):
        xy = [model.nodes[n] for n in element]
        where = triangle.point_coordinates(shape, xy, rule)
        for g, ((l1, l2, l3), w) in enumerate(rule.points):
            try:
                b, det = triangle.b_matrix(shape, xy, l1, l2, l3, axi)
            except ValueError as err:
                raise ValueError(f"element {e}: {err}") from None
            n = len(element)
            points.append(IntegrationPoint(
                e, g, tuple(element),
                tuple(b[0][2 * a] for a in range(n)),       # dN_a/dx
                tuple(b[1][2 * a + 1] for a in range(n)),   # dN_a/dy
                triangle.weight(shape, xy, l1, l2, l3, w, det, axi), where[g],
                tuple(b[2][2 * a] for a in range(n)) if axi else ()))   # N_a/r
    return points


def elastic_matrix(model: Model, material) -> list[list[float]]:
    """D of a material in the model's analysis: 3 x 3 (Eq. 4.16) or 4 x 4
    (Eq. 5.12)."""
    if model.axisymmetric:
        return axisymmetric_matrix(material.young, material.poisson)
    return plane_strain_matrix(material.young, material.poisson)


def stiffness(model: Model) -> coo_matrix:
    """K = assembly of int B^T D B dA, with the ELASTIC D of each element,
    element by element with triangle.stiffness: the tangent of the first
    correction of every step."""
    shape, rule = element_kind(model)
    rows, cols, values = [], [], []
    for element, material in zip(model.elements, model.materials):
        xy = [model.nodes[n] for n in element]
        k = triangle.stiffness(shape, xy, elastic_matrix(model, material), rule,
                               model.axisymmetric)
        dofs = [2 * n + c for n in element for c in (0, 1)]
        for r in range(len(dofs)):
            for c in range(len(dofs)):
                rows.append(dofs[r])
                cols.append(dofs[c])
                values.append(k[r][c])
    n = 2 * len(model.nodes)
    return coo_matrix((values, (rows, cols)), shape=(n, n))


def point_stiffness(p: IntegrationPoint, d: list[list[float]]) -> list[float]:
    """weight B^T D B of one point (Eq. 4.80), 2n x 2n row-major in the
    dofs (u1, v1, ..., un, vn) of its n nodes: the layout of
    interface.PointsUpdate. Block of nodes (a, b): B_a^T D B_b,
    B_a = [[dN_a/dx, 0], [0, dN_a/dy], [dN_a/dy, dN_a/dx]]."""
    if p.n_over_r:
        return _axisymmetric_point_stiffness(p, d)
    m = 2 * len(p.nodes)
    k = [0.0] * (m * m)
    for a, (ax, ay) in enumerate(zip(p.dndx, p.dndy)):
        # B_a^T rows: u_a -> (ax, 0, ay), v_a -> (0, ay, ax)
        for ra, (c0, c1, c2) in ((2 * a, (ax, 0.0, ay)),
                                 (2 * a + 1, (0.0, ay, ax))):
            for b, (bx, by) in enumerate(zip(p.dndx, p.dndy)):
                # D B_b, the columns for u_b and v_b
                dbu = (d[0][0] * bx + d[0][2] * by, d[1][0] * bx + d[1][2] * by,
                       d[2][0] * bx + d[2][2] * by)
                dbv = (d[0][1] * by + d[0][2] * bx, d[1][1] * by + d[1][2] * bx,
                       d[2][1] * by + d[2][2] * bx)
                k[m * ra + 2 * b] = p.weight * (c0 * dbu[0] + c1 * dbu[1] + c2 * dbu[2])
                k[m * ra + 2 * b + 1] = p.weight * (c0 * dbv[0] + c1 * dbv[1] + c2 * dbv[2])
    return k


def _axisymmetric_point_stiffness(p: IntegrationPoint, d: list[list[float]]
                                  ) -> list[float]:
    """weight B^T D B of one point in axisymmetry, D 4 x 4 on (eps_r, eps_z,
    eps_theta, gamma_rz): the column of B for u_a is (dN_a/dr, 0, N_a/r,
    dN_a/dz) and for v_a (0, dN_a/dz, 0, dN_a/dr) (Eq. 5.6)."""
    columns = []
    for dx, dy, nr in zip(p.dndx, p.dndy, p.n_over_r):
        columns += [(dx, 0.0, nr, dy), (0.0, dy, 0.0, dx)]
    m = len(columns)
    k = [0.0] * (m * m)
    for i, bi in enumerate(columns):
        for j, bj in enumerate(columns):
            dbj = [sum(d[r][c] * bj[c] for c in range(4)) for r in range(4)]
            k[m * i + j] = p.weight * sum(bi[r] * dbj[r] for r in range(4))
    return k


def tangent_stiffness(points: list[IntegrationPoint],
                      tangents: list[list[list[float]]],
                      n_dofs: int) -> coo_matrix:
    """K_T = assembly of int B^T D B dA with the consistent tangent D of
    each point (Eq. 4.80), point by point."""
    rows, cols, values = [], [], []
    for p, d in zip(points, tangents):
        dofs = [2 * n + c for n in p.nodes for c in (0, 1)]
        k = point_stiffness(p, d)
        m = len(dofs)
        for i in range(m):
            for j in range(m):
                rows.append(dofs[i])
                cols.append(dofs[j])
                values.append(k[m * i + j])
    return coo_matrix((values, (rows, cols)), shape=(n_dofs, n_dofs))


def update_stress(material: Elastic | mc.MohrCoulomb, stress: Stress,
                  strain_increment: tuple[float, ...]
                  ) -> tuple[Stress, bool, list[list[float]]]:
    """The incremental constitutive function (Eq. 4.60) of one point: the
    stress at the end of the increment, whether it is plastic, and the
    consistent tangent of that update (Eq. 4.81). Four strain components
    are axisymmetry, elastic only (spec 002, D6)."""
    if len(strain_increment) == 4:
        if isinstance(material, mc.MohrCoulomb):
            raise ValueError("Mohr-Coulomb is not validated in axisymmetry "
                             "(spec 002, D6)")
        d = axisymmetric_stress_increment(material.young, material.poisson,
                                          strain_increment)
        return (tuple(s + ds for s, ds in zip(stress, d)), False,
                axisymmetric_matrix(material.young, material.poisson))
    if isinstance(material, mc.MohrCoulomb):
        result = mc.update(material, stress, strain_increment, tangent=True)
        return result.stress, result.region != "elastic", result.tangent
    d = stress_increment(material.young, material.poisson, strain_increment)
    return ((stress[0] + d[0], stress[1] + d[1], stress[2] + d[2],
             stress[3] + d[3]), False,
            plane_strain_matrix(material.young, material.poisson))


def internal_forces(points: list[IntegrationPoint], stresses: list[Stress],
                    n_dofs: int) -> list[float]:
    """f_int = assembly of int B^T sigma dA (Eq. 4.65; triangle.internal_forces
    with the B of each point kept). sigma_zz does no work in plane strain;
    in axisymmetry it is the hoop stress and adds N_a / r sigma_theta to the
    radial force of node a (Eq. 5.6)."""
    f = [0.0] * n_dofs
    for p, (s_xx, s_yy, s_zz, t_xy) in zip(points, stresses):
        for n, dx, dy in zip(p.nodes, p.dndx, p.dndy):
            # the two rows of B^T for node n: (dx, 0, dy) and (0, dy, dx)
            f[2 * n] += p.weight * (dx * s_xx + dy * t_xy)
            f[2 * n + 1] += p.weight * (dy * s_yy + dx * t_xy)
        for n, nr in zip(p.nodes, p.n_over_r):
            f[2 * n] += p.weight * nr * s_zz
    return f


def integrate_points(points: list[IntegrationPoint], materials: list,
                     start: list[Stress],
                     strains: list[tuple[float, float, float]]
                     ) -> tuple[list[Stress], list[bool], list]:
    """The constitutive integration of every point (Eq. 4.60): ``materials``
    one per point. Returns (stresses, plastic, tangents)."""
    stresses, plastic, tangents = [], [], []
    for p, material, s0, strain in zip(points, materials, start, strains):
        try:
            s, is_plastic, d = update_stress(material, s0, strain)
        except mc.ReturnMappingError as err:
            raise StateUpdateError(p.element, p.index, None, None,
                                   str(err)) from None
        stresses.append(s)
        plastic.append(is_plastic)
        tangents.append(d)
    return stresses, plastic, tangents


def update_points(points: list[IntegrationPoint], materials: list,
                  start: list[Stress], du: list[float]
                  ) -> tuple[list[Stress], list[float], list[bool], list]:
    """THE call per global iteration (ADR-0001): given the displacement
    increment of the step, the stress of every point from the converged
    state of the step start (Box 4.2, vi-vii), the internal forces
    (viii-ix) and the consistent tangent of every point (ii). ``materials``
    one per point. Returns (stresses, f_int, plastic, tangents)."""
    stresses, plastic, tangents = integrate_points(
        points, materials, start, [p.strain(du) for p in points])
    return (stresses, internal_forces(points, stresses, len(du)), plastic,
            tangents)


# ------------------------------------------------ the reference as a variant
def geometry(model: Model, points: list[IntegrationPoint]) -> interface.Geometry:
    """The arrays the variants receive (interface.Geometry)."""
    return interface.Geometry(
        n_dofs=2 * len(model.nodes),
        nodes=np.array([p.nodes for p in points], dtype=np.int64),
        dndx=np.array([p.dndx for p in points], dtype=np.float64),
        dndy=np.array([p.dndy for p in points], dtype=np.float64),
        weight=np.array([p.weight for p in points], dtype=np.float64),
        element=np.array([p.element for p in points], dtype=np.int64),
        index=np.array([p.index for p in points], dtype=np.int64),
        xy=np.array([p.xy for p in points], dtype=np.float64),
        materials=np.array([interface.material_row(model.materials[p.element])
                            for p in points], dtype=np.float64),
        n_over_r=(np.array([p.n_over_r for p in points], dtype=np.float64)
                  if model.axisymmetric else None))


def _material_of(row) -> Elastic | mc.MohrCoulomb:
    kind, young, poisson, cohesion, phi, psi = (float(x) for x in row)
    if kind == interface.MOHR_COULOMB:
        return mc.MohrCoulomb(young, poisson, cohesion, phi, psi)
    return Elastic(young, poisson)


class _ReferencePrepared:
    """The reference set up for a stage: the arrays turned back into the
    plain Python objects above, and every call computed by them."""

    def __init__(self, g: interface.Geometry):
        self.n_dofs = g.n_dofs
        hoop = g.n_over_r if g.n_over_r is not None else [()] * len(g.nodes)
        self.points = [IntegrationPoint(int(e), int(i), tuple(int(n) for n in nodes),
                                        tuple(float(x) for x in dx),
                                        tuple(float(y) for y in dy), float(w),
                                        (float(xy[0]), float(xy[1])),
                                        tuple(float(v) for v in nr))
                       for e, i, nodes, dx, dy, w, xy, nr
                       in zip(g.element, g.index, g.nodes, g.dndx, g.dndy,
                              g.weight, g.xy, hoop)]
        self.materials = [_material_of(row) for row in g.materials]

    @staticmethod
    def _stresses(array) -> list[Stress]:
        return [tuple(float(x) for x in row) for row in array]

    def internal_forces(self, stresses):
        return np.array(internal_forces(self.points, self._stresses(stresses),
                                        self.n_dofs))

    def integrate(self, start, strains):
        stresses, plastic, tangents = integrate_points(
            self.points, self.materials, self._stresses(start),
            [tuple(float(x) for x in row) for row in strains])
        return interface.Integration(np.array(stresses), np.array(plastic),
                                     np.array(tangents))

    def update(self, start, du):
        stresses, f_int, plastic, tangents = update_points(
            self.points, self.materials, self._stresses(start),
            [float(x) for x in du])
        k = [point_stiffness(p, d) for p, d in zip(self.points, tangents)]
        return interface.PointsUpdate(np.array(stresses), np.array(f_int),
                                      np.array(plastic), np.array(tangents),
                                      np.array(k))


class ReferenceVariant:
    """The Python reference behind the common interface (spec 001, T10)."""
    name = "reference"

    def prepare(self, g: interface.Geometry) -> _ReferencePrepared:
        return _ReferencePrepared(g)


REFERENCE = ReferenceVariant()


def _norm(v, free) -> float:
    return float(np.sqrt(np.sum(v[free] ** 2)))


def solve_stage(model: Model, initial_stresses: list[Stress],
                external_load: list[float], steps: int, tolerance: float,
                max_iterations: int, max_cuts: int = 0,
                variant: interface.Variant = REFERENCE) -> StageResult:
    """Solve one stage from ``initial_stresses`` (one per integration point,
    in integration_points() order; the displacements start at zero) to the
    TOTAL ``external_load`` (one value per dof; the restrained ones are
    reactions and are ignored), in ``steps`` equal increments, with at most
    ``max_cuts`` cuts of an increment in two in the whole stage, the work
    per integration point done by ``variant`` (interface.py).

    Raises NotConvergedError when an increment does not reach ``tolerance``
    in ``max_iterations`` solves, and StateUpdateError when a point cannot
    be updated, once the cuts allowed are used up: in neither case is a
    result given.
    """
    if (steps < 1 or max_iterations < 1 or tolerance <= 0.0
            or max_cuts < 0):
        raise ValueError("need steps >= 1, max_iterations >= 1, "
                         "tolerance > 0 and max_cuts >= 0")
    points = integration_points(model)
    if len(initial_stresses) != len(points):
        raise ValueError("one initial stress per integration point")
    n_dofs = 2 * len(model.nodes)
    free = np.array([i for i in range(n_dofs) if i not in model.restrained],
                    dtype=np.int64)
    g = geometry(model, points)
    prepared = variant.prepare(g)
    rows, cols = interface.stiffness_pattern(g)

    def factorise(matrix: coo_matrix):
        return splu(matrix.tocsr()[free][:, free].tocsc())

    elastic = factorise(stiffness(model))

    start0 = np.array(initial_stresses, dtype=np.float64)
    f_start = prepared.internal_forces(start0)
    load = np.asarray(external_load, dtype=np.float64) - f_start
    scale = _norm(load, free)
    if scale == 0.0:
        raise ValueError("the stage has no load: nothing to solve")

    history: list[tuple[int, int, float]] = []

    def increment(number: int, start: np.ndarray, factor: float):
        """One increment from the converged ``start`` to the load factor
        ``factor`` (Box 4.2). Returns (du, stresses, plastic)."""
        target = f_start + factor * load
        du = np.zeros(n_dofs)
        # Iteration 0 is the increment's start: its residual is the load added.
        f_int = prepared.internal_forces(start)
        stresses, plastic = start, np.zeros(len(points), dtype=bool)
        solver = elastic            # the tangent with no strain increment
        for iteration in range(0, max_iterations + 1):
            # r = f_ext - f_int with the sign of the right-hand side of (4.71)
            r = target - f_int
            relative = _norm(r, free) / scale
            history.append((number, iteration, relative))
            if iteration > 0 and relative <= tolerance:
                return du, stresses, plastic
            if iteration == max_iterations:
                raise NotConvergedError(number, history)
            du[free] += solver.solve(r[free])
            try:
                result = prepared.update(start, du)
            except StateUpdateError as err:
                raise StateUpdateError(err.element, err.point, number,
                                       iteration + 1, err.reason) from None
            stresses, f_int, plastic = (result.stresses,
                                        result.internal_forces, result.plastic)
            if plastic.any():
                solver = factorise(coo_matrix(
                    (result.stiffness.ravel(), (rows, cols)),
                    shape=(n_dofs, n_dofs)))
            else:
                solver = elastic
        raise AssertionError("unreachable")

    displacement = np.zeros(n_dofs)
    converged = start0
    plastic = np.zeros(len(points), dtype=bool)
    increments: list[tuple[float, float, str]] = []
    # Load factors still to reach, in order (Box 4.1); a cut inserts the
    # midpoint of the failed increment in front (§5.4.3).
    pending = [i / steps for i in range(1, steps + 1)]
    factor, number, cuts = 0.0, 0, 0
    while pending:
        number += 1
        try:
            du, stresses, step_plastic = increment(number, converged,
                                                   pending[0])
        except (NotConvergedError, StateUpdateError) as err:
            if cuts == max_cuts:
                raise
            increments.append((factor, pending[0], f"cut: {err}"))
            pending.insert(0, 0.5 * (factor + pending[0]))
            cuts += 1
            continue
        increments.append((factor, pending[0], "converged"))
        factor = pending.pop(0)
        converged, plastic = stresses, step_plastic
        displacement = displacement + du

    return StageResult([float(u) for u in displacement],
                       [tuple(float(x) for x in s) for s in converged],
                       [bool(x) for x in plastic], points, history,
                       increments, steps, tolerance, cuts)
