# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The three-node (linear) triangle (spec 002, T4).

Source: Zienkiewicz, O. C. and Taylor, R. L. (2000). *The Finite Element
Method*, 5th ed., vol. 1, §4.2.1-4.2.2, Eqs. (4.5a)-(4.10b), pp. 88-90:
nodes i, j, m anticlockwise, u = sum (a_i + b_i x + c_i y) u_i / 2 Delta with
a_i = x_j y_m - x_m y_j, b_i = y_j - y_m, c_i = x_m - x_j and 2 Delta twice
the area (Eq. 4.5c), so N_i = (a_i + b_i x + c_i y) / 2 Delta (Eq. 4.8),
which is the area coordinate L_i (§8.8.1, Eqs. 8.30-8.33, pp. 180-181).
B is constant in the element, B_i = [[b_i, 0], [0, c_i], [c_i, b_i]] / 2 Delta
(Eq. 4.10b).

It is written here, like the six-node triangle, as an isoparametric element
of triangle.py with N_i = L_i: with straight sides the mapping is the
identity of Eq. (4.8), and the tests check B against Eq. (4.10b).

Local coordinates: L1 = 1 - xi - eta, L2 = xi, L3 = eta.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import sys

from . import triangle
from .quadrature import LINEAR

#: Area coordinates of the three nodes.
NODES_L = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def shape_functions(l1: float, l2: float, l3: float) -> list[float]:
    """N1, N2, N3 at (L1, L2, L3): the area coordinates themselves."""
    return [l1, l2, l3]


def shape_derivatives_local(l1: float, l2: float, l3: float
                            ) -> list[tuple[float, float]]:
    """(dN/dxi, dN/deta): with L1 = 1 - xi - eta, L2 = xi, L3 = eta,
    constant."""
    return [(-1.0, -1.0), (1.0, 0.0), (0.0, 1.0)]


_SHAPE = sys.modules[__name__]


def b_matrix(xy: list[tuple[float, float]]) -> tuple[list[list[float]], float]:
    """The constant 3x6 strain-displacement matrix and det J = 2 Delta;
    ValueError for det J <= 0."""
    return triangle.b_matrix(_SHAPE, xy, *LINEAR.points[0][0])


def stiffness(xy: list[tuple[float, float]], d: list[list[float]]
              ) -> list[list[float]]:
    """K = int B^T D B dA = Delta B^T D B (B constant: the centroid is exact)."""
    return triangle.stiffness(_SHAPE, xy, d, LINEAR)


def internal_forces(xy: list[tuple[float, float]],
                    stresses: list[tuple[float, float, float, float]]
                    ) -> list[float]:
    """f = int B^T sigma dA with the stress of the one point."""
    return triangle.internal_forces(_SHAPE, xy, stresses, LINEAR)


def strains(xy: list[tuple[float, float]], u: list[float]
            ) -> list[tuple[float, float, float]]:
    """(eps_x, eps_y, gamma_xy) = B u at the centroid (constant)."""
    return triangle.strains(_SHAPE, xy, u, LINEAR)
