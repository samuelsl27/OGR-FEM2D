# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The isoparametric triangle, whatever its number of nodes (spec 002, T4):
what element_t3 (three nodes) and element_t6 (six) have in common.

Source: Zienkiewicz, O. C. and Taylor, R. L. (2000). *The Finite Element
Method*, 5th ed., vol. 1:

* the displacement u = sum_a N_a a_a and the strain eps = B a with
  B = S N: §2.2, Eqs. (2.1)-(2.4), pp. 20-22; in plane strain the operator S
  of Eq. (4.9), p. 89, gives for each node the block
  B_a = [[dN_a/dx, 0], [0, dN_a/dy], [dN_a/dy, dN_a/dx]] (Eq. 4.10b);
* isoparametric mapping, Chapter 9: the same shape functions for geometry
  and displacement; [dN/dx, dN/dy] = J^-1 [dN/dxi, dN/deta];
* the element equations, Eqs. (2.13a)-(2.13b), pp. 24-25: stiffness
  int B^T D B dA and the force of a stress state int B^T sigma dA;
* axisymmetry (spec 002, T5), §5.2, pp. 112-119: x is the radius r and y
  the axis z; the strains are (eps_r, eps_z, eps_theta, gamma_rz) with
  eps_theta = u / r (Eq. 5.5), so B gains the row of the hoop strain,
  B_a = [[dN_a/dr, 0], [0, dN_a/dz], [N_a / r, 0], [dN_a/dz, dN_a/dr]]
  (Eq. 5.6), and every integral is over the whole ring, 2 pi r dr dz
  (Eqs. 5.13 and 5.15-5.19; spec 002, D2). N_a / r needs r > 0 at every
  integration point: the rules of D1 keep the points off the axis;
* quadrature: reference/quadrature.py (Table 9.2, p. 222); over the element
  int f dA = sum_g w_g f(L_g) det J(L_g) / 2, the reference triangle in
  (xi, eta) having area 1/2.

Local coordinates: L1 = 1 - xi - eta, L2 = xi, L3 = eta.

A shape is a module with NODES_L (area coordinates of its nodes),
shape_functions(l1, l2, l3) and shape_derivatives_local(l1, l2, l3), the
latter giving (dN/dxi, dN/deta) per node. Everything below works for any
number of nodes n, with the degrees of freedom ordered (u1, v1, ..., un, vn),
and with ``axisymmetric`` for the ring (four strain rows, 2 pi r in the
weight); without it, plane strain (three rows).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from .quadrature import Rule


def jacobian(shape, xy: list[tuple[float, float]], l1: float, l2: float, l3: float
             ) -> tuple[list[list[float]], float]:
    """J = [[dx/dxi, dy/dxi], [dx/deta, dy/deta]] and det J."""
    dn = shape.shape_derivatives_local(l1, l2, l3)
    n = len(dn)
    j11 = sum(dn[a][0] * xy[a][0] for a in range(n))
    j12 = sum(dn[a][0] * xy[a][1] for a in range(n))
    j21 = sum(dn[a][1] * xy[a][0] for a in range(n))
    j22 = sum(dn[a][1] * xy[a][1] for a in range(n))
    return [[j11, j12], [j21, j22]], j11 * j22 - j12 * j21


def b_matrix(shape, xy: list[tuple[float, float]], l1: float, l2: float, l3: float,
             axisymmetric: bool = False) -> tuple[list[list[float]], float]:
    """The strain-displacement matrix and det J: 3 x 2n on (eps_x, eps_y,
    gamma_xy) in plane strain; 4 x 2n on (eps_r, eps_z, eps_theta, gamma_rz)
    in axisymmetry (Eq. 5.6).

    Raises ValueError for a non-positive det J: an inverted or degenerate
    element gives no result, not a wrong one (spec 001, edge cases); and in
    axisymmetry for a point at r <= 0, where N / r cannot be evaluated.
    """
    (j11, j12), (j21, j22) = jacobian(shape, xy, l1, l2, l3)[0]
    det = j11 * j22 - j12 * j21
    if det <= 0.0:
        raise ValueError(f"det J = {det:.6g} <= 0 at L = ({l1}, {l2}, {l3})")
    dn = shape.shape_derivatives_local(l1, l2, l3)
    n = len(dn)
    if axisymmetric:
        r, n_over_r = _hoop(shape, xy, l1, l2, l3)
    b = [[0.0] * (2 * n) for _ in range(4 if axisymmetric else 3)]
    shear = 3 if axisymmetric else 2
    for a in range(n):
        # [dN/dx, dN/dy] = J^-1 [dN/dxi, dN/deta]
        dndx = (j22 * dn[a][0] - j12 * dn[a][1]) / det
        dndy = (-j21 * dn[a][0] + j11 * dn[a][1]) / det
        b[0][2 * a] = dndx
        b[1][2 * a + 1] = dndy
        b[shear][2 * a] = dndy
        b[shear][2 * a + 1] = dndx
        if axisymmetric:
            b[2][2 * a] = n_over_r[a]           # eps_theta = u / r, Eq. (5.5)
    return b, det


def radius(shape, xy: list[tuple[float, float]], l1: float, l2: float, l3: float
           ) -> float:
    """r = x = sum_a N_a x_a at (L1, L2, L3)."""
    n = shape.shape_functions(l1, l2, l3)
    return sum(n[a] * xy[a][0] for a in range(len(n)))


def _hoop(shape, xy, l1, l2, l3) -> tuple[float, list[float]]:
    """r and N_a / r at a point, for the hoop row of B; r must be > 0."""
    r = radius(shape, xy, l1, l2, l3)
    if r <= 0.0:
        raise ValueError(f"integration point at r = {r:.6g} <= 0, L = ({l1}, {l2}, "
                         f"{l3}): on or across the axis (spec 002, D1)")
    return r, [n / r for n in shape.shape_functions(l1, l2, l3)]


def weight(shape, xy: list[tuple[float, float]], l1: float, l2: float, l3: float,
           w: float, det: float, axisymmetric: bool = False) -> float:
    """The factor of a point in int f dV: w det J / 2, times 2 pi r over the
    ring in axisymmetry (Eq. 5.13)."""
    factor = w * det / 2.0
    if axisymmetric:
        factor *= 2.0 * math.pi * radius(shape, xy, l1, l2, l3)
    return factor


def point_coordinates(shape, xy: list[tuple[float, float]], rule: Rule
                      ) -> list[tuple[float, float]]:
    """(x, y) of the points of the rule: sum_a N_a x_a."""
    out = []
    for (l1, l2, l3), _ in rule.points:
        n = shape.shape_functions(l1, l2, l3)
        out.append((sum(n[a] * xy[a][0] for a in range(len(n))),
                    sum(n[a] * xy[a][1] for a in range(len(n)))))
    return out


def stiffness(shape, xy: list[tuple[float, float]], d: list[list[float]], rule: Rule,
              axisymmetric: bool = False) -> list[list[float]]:
    """K = int B^T D B dV, Eq. (2.13a) (Eq. 5.13 over the ring), by the
    quadrature of ``rule``; D is 3 x 3, or 4 x 4 in axisymmetry."""
    m = 2 * len(shape.NODES_L)
    k = [[0.0] * m for _ in range(m)]
    for (l1, l2, l3), w in rule.points:
        b, det = b_matrix(shape, xy, l1, l2, l3, axisymmetric)
        factor = weight(shape, xy, l1, l2, l3, w, det, axisymmetric)
        rows = len(b)
        db = [[sum(d[i][q] * b[q][c] for q in range(rows)) for c in range(m)]
              for i in range(rows)]
        for r in range(m):
            for c in range(m):
                k[r][c] += factor * sum(b[i][r] * db[i][c] for i in range(rows))
    return k


def internal_forces(shape, xy: list[tuple[float, float]],
                    stresses: list[tuple[float, float, float, float]], rule: Rule,
                    axisymmetric: bool = False) -> list[float]:
    """f = int B^T sigma dV over the element, Eq. (2.13b), with one stress
    (sigma_xx, sigma_yy, sigma_zz, tau_xy) per point of ``rule``, in its
    order. sigma_zz does no work in plane strain; in axisymmetry it is the
    hoop stress and works through eps_theta = u / r."""
    m = 2 * len(shape.NODES_L)
    f = [0.0] * m
    for ((l1, l2, l3), w), s in zip(rule.points, stresses):
        b, det = b_matrix(shape, xy, l1, l2, l3, axisymmetric)
        factor = weight(shape, xy, l1, l2, l3, w, det, axisymmetric)
        vec = tuple(s) if axisymmetric else (s[0], s[1], s[3])
        for r in range(m):
            f[r] += factor * sum(b[i][r] * vec[i] for i in range(len(b)))
    return f


def strains(shape, xy: list[tuple[float, float]], u: list[float], rule: Rule,
            axisymmetric: bool = False) -> list[tuple[float, ...]]:
    """B u at the points of ``rule``: (eps_x, eps_y, gamma_xy), or (eps_r,
    eps_z, eps_theta, gamma_rz) in axisymmetry."""
    out = []
    for (l1, l2, l3), _ in rule.points:
        b, _det = b_matrix(shape, xy, l1, l2, l3, axisymmetric)
        out.append(tuple(sum(b[i][c] * u[c] for c in range(len(u)))
                         for i in range(len(b))))
    return out


def area(shape, xy: list[tuple[float, float]], rule: Rule) -> float:
    """int dA by the quadrature of ``rule`` (exact for a straight element)."""
    return sum(w * jacobian(shape, xy, *l)[1] / 2.0 for l, w in rule.points)


def volume(shape, xy: list[tuple[float, float]], rule: Rule) -> float:
    """int 2 pi r dA, the volume of the ring, by the quadrature of ``rule``
    (exact for a straight element whenever the rule integrates degree 1:
    the area times the path of its centroid, p. 118)."""
    total = 0.0
    for (l1, l2, l3), w in rule.points:
        det = jacobian(shape, xy, l1, l2, l3)[1]
        total += weight(shape, xy, l1, l2, l3, w, det, True)
    return total
