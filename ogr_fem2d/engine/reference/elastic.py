# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Linear isotropic elasticity in plane strain and in axisymmetry.

Source: Zienkiewicz, O. C. and Taylor, R. L. (2000). *The Finite Element
Method*, 5th ed., vol. 1, §4.2.4, Eqs. (4.15)-(4.16), p. 91: with eps_z = 0,

    sigma_z = nu (sigma_x + sigma_y)

and, on the in-plane components (eps_x, eps_y, gamma_xy),

                E (1 - nu)          | 1            nu/(1-nu)   0                    |
    D = ------------------------- . | nu/(1-nu)    1           0                    |
         (1 + nu)(1 - 2 nu)         | 0            0           (1-2nu)/(2(1-nu))    |

In axisymmetry (spec 002, T5), §5.2.4, Eq. (5.12), p. 117, on the four
strains (eps_r, eps_z, eps_theta, gamma_rz) of Eq. (5.5):

                E              | 1-nu  nu    nu    0          |
    D = ------------------- .  | nu    1-nu  nu    0          |
        (1 + nu)(1 - 2 nu)     | nu    nu    1-nu  0          |
                               | 0     0     0     (1-2nu)/2  |

the first three rows of the isotropic law with the hoop strain kept (in
plane strain it is zero, and the 3 x 3 matrix above is what is left).

Stresses are tension-positive (spec 001, D1). The stress vector of the engine
is (sigma_xx, sigma_yy, sigma_zz, tau_xy): sigma_zz is kept because the
Mohr-Coulomb law of plane strain needs it to order the principal stresses.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Elastic:
    """Material: Young's modulus E and Poisson's ratio nu."""
    young: float
    poisson: float


def plane_strain_matrix(young: float, poisson: float) -> list[list[float]]:
    """The 3x3 matrix D of Eq. (4.16), on (eps_x, eps_y, gamma_xy)."""
    factor = young * (1.0 - poisson) / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
    ratio = poisson / (1.0 - poisson)
    shear = (1.0 - 2.0 * poisson) / (2.0 * (1.0 - poisson))
    return [[factor, factor * ratio, 0.0],
            [factor * ratio, factor, 0.0],
            [0.0, 0.0, factor * shear]]


def stress_increment(young: float, poisson: float,
                     strain: tuple[float, float, float]
                     ) -> tuple[float, float, float, float]:
    """(d_sigma_xx, d_sigma_yy, d_sigma_zz, d_tau_xy) for a strain increment
    (d_eps_xx, d_eps_yy, d_gamma_xy): Eq. (4.16), and sigma_z of Eq. (4.15)."""
    d = plane_strain_matrix(young, poisson)
    s_xx = d[0][0] * strain[0] + d[0][1] * strain[1]
    s_yy = d[1][0] * strain[0] + d[1][1] * strain[1]
    t_xy = d[2][2] * strain[2]
    return s_xx, s_yy, poisson * (s_xx + s_yy), t_xy


def axisymmetric_matrix(young: float, poisson: float) -> list[list[float]]:
    """The 4x4 matrix D of Eq. (5.12), on (eps_r, eps_z, eps_theta, gamma_rz)."""
    factor = young / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
    a, b = factor * (1.0 - poisson), factor * poisson
    return [[a, b, b, 0.0],
            [b, a, b, 0.0],
            [b, b, a, 0.0],
            [0.0, 0.0, 0.0, factor * (1.0 - 2.0 * poisson) / 2.0]]


def axisymmetric_stress_increment(young: float, poisson: float,
                                  strain: tuple[float, float, float, float]
                                  ) -> tuple[float, float, float, float]:
    """(d_sigma_r, d_sigma_z, d_sigma_theta, d_tau_rz) for a strain increment
    (d_eps_r, d_eps_z, d_eps_theta, d_gamma_rz): Eq. (5.12)."""
    d = axisymmetric_matrix(young, poisson)
    return tuple(sum(d[i][j] * strain[j] for j in range(4)) for i in range(4))
