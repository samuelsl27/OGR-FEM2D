# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The six-node (quadratic) triangle, isoparametric, plane strain, small strain.

Sources, all Zienkiewicz, O. C. and Taylor, R. L. (2000). *The Finite Element
Method*, 5th ed., vol. 1:

* area coordinates L1, L2, L3: §8.8.1, Eqs. (8.30)-(8.33), pp. 180-181;
* shape functions of the quadratic triangle, p. 182: corner nodes
  N1 = (2 L1 - 1) L1, etc.; mid-side nodes N4 = 4 L1 L2, etc. Node order of
  Fig. 8.15(b): corners 1, 2, 3, then the mid-sides 4 (1-2), 5 (2-3), 6 (3-1);
* isoparametric mapping: Chapter 9, the same shape functions for the
  geometry and the displacement, so an edge whose mid-side node sits on a
  circle follows it (the boundary of the hole);
* quadrature: §9.10, Table 9.2, p. 222, the "quadratic" rule: the three
  mid-side points (1/2, 1/2, 0), (0, 1/2, 1/2), (1/2, 0, 1/2), weight 1/3 each,
  error O(h^3), exact for polynomials of degree 2 in the area coordinates;
* the element equations: Eq. (2.13b) and the comment that follows it,
  pp. 24-25: stiffness int(B^T D B) and the force of a stress state
  int(B^T sigma); the initial-stress term of the same equation is the load of
  an excavation in stressed rock, which the book gives as its example.

The weights of Table 9.2 add up to one, so an integral over the element is
    int f dA = sum_g w_g f(L_g) det J(L_g) / 2
because the reference triangle in (xi, eta) has area 1/2; for a straight
triangle det J = 2 x area and this is area x sum_g w_g f_g, as in the table.

Local coordinates: L1 = 1 - xi - eta, L2 = xi, L3 = eta.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import sys

from . import triangle
from .quadrature import QUADRATIC

#: Area coordinates of the six nodes, in the order of Fig. 8.15(b).
NODES_L = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0),
           (0.5, 0.5, 0.0), (0.0, 0.5, 0.5), (0.5, 0.0, 0.5))

#: Table 9.2, quadratic rule: (area coordinates, weight), from quadrature.py.
GAUSS_POINTS = QUADRATIC.points


def shape_functions(l1: float, l2: float, l3: float) -> list[float]:
    """N1..N6 at (L1, L2, L3), p. 182."""
    return [(2.0 * l1 - 1.0) * l1,
            (2.0 * l2 - 1.0) * l2,
            (2.0 * l3 - 1.0) * l3,
            4.0 * l1 * l2,
            4.0 * l2 * l3,
            4.0 * l3 * l1]


def shape_derivatives_local(l1: float, l2: float, l3: float
                            ) -> list[tuple[float, float]]:
    """(dN/dxi, dN/deta) of the six functions.

    With L1 = 1 - xi - eta, L2 = xi, L3 = eta, the chain rule gives
    dN/dxi = dN/dL2 - dN/dL1 and dN/deta = dN/dL3 - dN/dL1.
    """
    # dN_a / dL_k, row a, column k
    dn_dl = [(4.0 * l1 - 1.0, 0.0, 0.0),
             (0.0, 4.0 * l2 - 1.0, 0.0),
             (0.0, 0.0, 4.0 * l3 - 1.0),
             (4.0 * l2, 4.0 * l1, 0.0),
             (0.0, 4.0 * l3, 4.0 * l2),
             (4.0 * l3, 0.0, 4.0 * l1)]
    return [(d[1] - d[0], d[2] - d[0]) for d in dn_dl]


# The rest is the isoparametric triangle of triangle.py with these shape
# functions and the quadratic rule (spec 002, T4: the same operations, in the
# same order, as in spec 001).
_SHAPE = sys.modules[__name__]


def jacobian(xy: list[tuple[float, float]], l1: float, l2: float, l3: float
             ) -> tuple[list[list[float]], float]:
    """J = [[dx/dxi, dy/dxi], [dx/deta, dy/deta]] and det J."""
    return triangle.jacobian(_SHAPE, xy, l1, l2, l3)


def b_matrix(xy: list[tuple[float, float]], l1: float, l2: float, l3: float
             ) -> tuple[list[list[float]], float]:
    """The 3x12 strain-displacement matrix on (eps_x, eps_y, gamma_xy), with
    the degrees of freedom ordered (u1, v1, u2, v2, ..., u6, v6), and det J;
    ValueError for det J <= 0."""
    return triangle.b_matrix(_SHAPE, xy, l1, l2, l3)


def gauss_point_coordinates(xy: list[tuple[float, float]]
                            ) -> list[tuple[float, float]]:
    """(x, y) of the three integration points: sum_a N_a x_a."""
    return triangle.point_coordinates(_SHAPE, xy, QUADRATIC)


def stiffness(xy: list[tuple[float, float]], d: list[list[float]]
              ) -> list[list[float]]:
    """K = int B^T D B dA, Eq. (2.13b), by the quadrature of Table 9.2."""
    return triangle.stiffness(_SHAPE, xy, d, QUADRATIC)


def internal_forces(xy: list[tuple[float, float]],
                    stresses: list[tuple[float, float, float, float]]
                    ) -> list[float]:
    """f = int B^T sigma dA over the element, Eq. (2.13b), with one stress
    (sigma_xx, sigma_yy, sigma_zz, tau_xy) per integration point, in the
    order of GAUSS_POINTS. sigma_zz does no work in plane strain."""
    return triangle.internal_forces(_SHAPE, xy, stresses, QUADRATIC)


def strains(xy: list[tuple[float, float]], u: list[float]
            ) -> list[tuple[float, float, float]]:
    """(eps_x, eps_y, gamma_xy) = B u at the three integration points."""
    return triangle.strains(_SHAPE, xy, u, QUADRATIC)


def area(xy: list[tuple[float, float]]) -> float:
    """int dA by the same quadrature (exact for a straight-sided element)."""
    return triangle.area(_SHAPE, xy, QUADRATIC)
