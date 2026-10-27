# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Closed-form references of spec 002, checked against their sources.

    .venv/Scripts/python spec/features/002-motor-elastico/comprobaciones/soluciones_cerradas.py

Conventions INSIDE this file: stresses compression-positive and displacement
positive INWARD (toward the cavity, or downward under the strip), as in the
cases. The engine is tension-positive (spec 001, D1); the tests convert.

Sources, Timoshenko, S. and Goodier, J. N. (1951). *Theory of Elasticity*,
2nd ed., McGraw-Hill:

* §33, Eq. (66), p. 85: a vertical point force P on the straight boundary of
  a semi-infinite plate (Flamant 1892) gives the simple radial distribution
  sigma_r = -2 P cos(theta) / (pi r), theta from the vertical, sigma_theta =
  tau = 0 (tension positive);
* §34, Eqs. (c)-(f), pp. 92-95: a uniform load q on a portion of that
  boundary (J. H. Michell 1902): at any point the principal stresses are
  -2A (alpha + sin alpha) and -2A (alpha - sin alpha), 2 A pi = q, alpha the
  angle between the radii to the two edges of the load, and the principal
  direction bisects that angle (beta = alpha / 2);
* §121, Eqs. (197)-(198), pp. 358-359: the spherical shell a <= R <= b
  under internal and external pressure (Lamé 1852), sigma_R = C/R^3 + D and
  sigma_t = sigma_R + (R/2) d sigma_R / dR (Eq. e);
* §6, Hooke's law (pp. 6-9), for the displacement of the cavity, which
  §121 does not print: the tangential strain of the sphere is u/R.
"""
from __future__ import annotations

import math

from scipy.integrate import quad

# ---------------------------------------------------------------- STR-04
Q, B_HALF = 1.0, 1.0            # MPa, m: load and half-width of the strip


def strip_principal(x: float, z: float, q: float = Q, b: float = B_HALF
                    ) -> tuple[float, float, float]:
    """(sigma_1, sigma_3, angle of sigma_1 from the vertical) at (x, z), z
    the depth (> 0), x from the centre of the strip, compression positive:
    Michell's solution, T&G §34 Eq. (f) with 2 A pi = q. The angle is that of
    the bisector of the radii to the edges (beta = alpha / 2)."""
    left, right = math.atan2(x + b, z), math.atan2(x - b, z)   # from the vertical
    alpha = left - right
    s1 = q / math.pi * (alpha + math.sin(alpha))
    s3 = q / math.pi * (alpha - math.sin(alpha))
    return s1, s3, 0.5 * (left + right)


def strip_by_flamant(x: float, z: float, q: float = Q, b: float = B_HALF
                     ) -> tuple[float, float, float]:
    """The same by superposing Flamant's point force (T&G §33, Eq. 66) over
    the strip, q dy at each point: an independent check of Michell's closed
    form. Returns (sigma_xx, sigma_zz, tau_xz), compression positive, x
    horizontal and z downward."""
    def components(y):
        dx, dz = x - y, z
        r2 = dx * dx + dz * dz
        # radial compression 2 dP cos(theta) / (pi r), cos(theta) = dz / r,
        # along the unit vector (dx, dz) / r
        s = 2.0 * q * dz / (math.pi * r2)
        return s * dx * dx / r2, s * dz * dz / r2, s * dx * dz / r2

    opts = dict(limit=200, epsabs=1e-13, epsrel=1e-12)
    return tuple(quad(lambda y, k=k: components(y)[k], -b, b, **opts)[0]
                 for k in range(3))


def principal_of(sxx: float, szz: float, txz: float) -> tuple[float, float]:
    centre, radius = 0.5 * (sxx + szz), math.hypot(0.5 * (sxx - szz), txz)
    return centre + radius, centre - radius


# ---------------------------------------------------------------- STR-09
E, NU = 20000.0, 0.2            # MPa, -
P0, A = 10.0, 1.0               # field pressure (MPa) and cavity radius (m)
G = E / (2.0 * (1.0 + NU))


def sphere_infinite(r: float) -> tuple[float, float, float]:
    """(sigma_R, sigma_t, u_in) at radius r: the cavity in an infinite medium
    under the field P0, excavated (pi = 0). From (197)-(198) with pi = 0 and
    b -> inf, compression positive: sigma_R = P0 (1 - a^3/r^3), sigma_t =
    P0 (1 + a^3 / (2 r^3)). u_in from Hooke's law on the stress change of
    the excavation: d sigma_R = P0 a^3/r^3, d sigma_t = -P0 a^3/(2 r^3)
    (tension positive), eps_t = u/r = (d sigma_t - nu (d sigma_R + d
    sigma_t))/E = -(1 + nu) P0 a^3 / (2 E r^3), so u_in = P0 a^3 / (4 G r^2)."""
    s_r = P0 * (1.0 - A ** 3 / r ** 3)
    s_t = P0 * (1.0 + A ** 3 / (2.0 * r ** 3))
    return s_r, s_t, P0 * A ** 3 / (4.0 * G * r ** 2)


def sphere_fixed_outer(r: float, b: float) -> tuple[float, float, float]:
    """The same excavation in a spherical shell a <= R <= b whose outer
    surface does not move (u(b) = 0): the identity of a finite model, as
    lame_fixed_outer was for the ring of spec 001.

    The stress change of the excavation is a Lamé field (T&G §121):
    d sigma_R = C/R^3 + D, d sigma_t = -C/(2 R^3) + D (tension positive,
    Eq. e), with d sigma_R(a) = P0 (the hole is unloaded). Its strain is
    eps_t = u/R = (d sigma_t - nu (d sigma_R + d sigma_t))/E =
    (-(1 + nu) C / (2 R^3) + (1 - 2 nu) D) / E, and u(b) = 0 gives
    D = (1 + nu) C / (2 (1 - 2 nu) b^3). Our derivation from the source;
    with b -> inf it is sphere_infinite.
    """
    k = (1.0 + NU) / (2.0 * (1.0 - 2.0 * NU) * b ** 3)
    c = P0 / (1.0 / A ** 3 + k)              # from d sigma_R(a) = P0
    d = k * c
    d_r = c / r ** 3 + d
    d_t = -c / (2.0 * r ** 3) + d
    u_out = r * (-(1.0 + NU) * c / (2.0 * r ** 3) + (1.0 - 2.0 * NU) * d) / E
    return P0 - d_r, P0 - d_t, -u_out


if __name__ == "__main__":
    print("STR-04, Michell vs Flamant superposed (compression +):")
    worst = 0.0
    for x, z in ((0.0, 0.25), (0.0, 1.0), (0.0, 5.0), (0.7, 0.4), (2.5, 1.5), (-1.3, 3.0)):
        s1, s3, _ = strip_principal(x, z)
        f1, f3 = principal_of(*strip_by_flamant(x, z))
        worst = max(worst, abs(s1 - f1), abs(s3 - f3))
        print(f"  ({x:+.2f}, {z:.2f}): sigma_1 {s1:.6f} / {f1:.6f}, sigma_3 {s3:.6f} / {f3:.6f}")
    print(f"  largest difference {worst:.1e} MPa")
    print("STR-09, cavity in an infinite medium:", sphere_infinite(A))
    for b in (5.0, 21.0, 100.0, 1e6):
        fin, inf = sphere_fixed_outer(A, b), sphere_infinite(A)
        print(f"  outer fixed at {b:>9.0f} m: u_in(a) {fin[2]:.9e} ({(fin[2] / inf[2] - 1) * 100:+.4f} %),"
              f" sigma_t(a) {fin[1]:.6f} ({(fin[1] / inf[1] - 1) * 100:+.4f} %), sigma_R(a) {fin[0]:.1e}")
