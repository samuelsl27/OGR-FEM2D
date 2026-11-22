# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Closed-form references of spec 003 (task T10), checked against their source.

Run it with the project's environment:

    .venv/Scripts/python spec/features/003-malla/comprobaciones/soluciones_cerradas.py

It prints the checks of T10. Nothing here is the engine or the mesher: it is
the external side of case 005 and its identity (spec 003, D12).

Source: Jaeger, J. C., Cook, N. G. W. and Zimmerman, R. W. (2007).
*Fundamentals of Rock Mechanics*, 4th ed., §8.5, Kirsch (1898):

* stresses around the hole with far-field principal stresses sigma_1 along x
  and sigma_2 along y, (8.113)-(8.115), p. 219;
* displacements of the uniaxial field sigma_1, (8.121)-(8.125), pp. 220-221:
  8G u_r / (a sigma_1) = [(kappa - 1)(r/a) + 2(a/r)]
                         + 2[(r/a) + (kappa + 1)(a/r) - (a/r)^3] cos 2 theta,
  8G u_theta / (a sigma_1) = -2[(r/a) + (kappa - 1)(a/r) + (a/r)^3] sin 2 theta,
  kappa = 3 - 4 nu in plane strain; sigma_2 by theta -> theta + pi/2 (p. 219).

THE DISPLACEMENT THE EXCAVATION CAUSES. (8.122) with A = B = C = 0 is the
field of the medium without the hole (the potentials of p. 216):
8G u_r / (a sigma_1) = (kappa - 1)(r/a) + 2 (r/a) cos 2 theta and
8G u_theta / (a sigma_1) = -2 (r/a) sin 2 theta. Subtracting it (own
derivation):
  8G u_r / (a sigma_1) = 2(a/r) + 2[(kappa + 1)(a/r) - (a/r)^3] cos 2 theta,
  8G u_theta / (a sigma_1) = -2[(kappa - 1)(a/r) + (a/r)^3] sin 2 theta.
With sigma_1 = sigma_2 = p it is p a^2 / (2 G r), the (8.90) of spec 001.

Conventions INSIDE this file, those of the source: stresses compression
positive, and displacements positive towards -r and -theta (spec 001 checked
it for u_r: the (1 - 2 nu) P0 r of (8.90) is a contraction under compression).
The engine counts tension positive and displacement along +x, +y; the tests
convert (``engine_displacement``).
"""
from __future__ import annotations

import math

E, NU = 10000.0, 0.2            # MPa, - (STR-01)
P0 = 30.0                       # MPa, hydrostatic in STR-01
A = 1.0                         # hole radius, m
G = E / (2.0 * (1.0 + NU))
KAPPA = 3.0 - 4.0 * NU          # plane strain
LAM = E * NU / ((1.0 + NU) * (1.0 - 2.0 * NU))


def kirsch_stress(r: float, theta: float, s1: float, s2: float, a: float = A
                  ) -> tuple[float, float, float]:
    """(sigma_r, sigma_theta, tau_r_theta), compression positive, around the
    open hole: JCZ (8.113)-(8.115)."""
    q2, q4 = (a / r) ** 2, (a / r) ** 4
    mean, half = 0.5 * (s1 + s2), 0.5 * (s1 - s2)
    c, s = math.cos(2.0 * theta), math.sin(2.0 * theta)
    sigma_t = mean * (1.0 + q2) - half * (1.0 + 3.0 * q4) * c
    sigma_r = mean * (1.0 - q2) + half * (1.0 - 4.0 * q2 + 3.0 * q4) * c
    tau = -half * (1.0 + 2.0 * q2 - 3.0 * q4) * s
    return sigma_r, sigma_t, tau


def far_field(theta: float, s1: float, s2: float) -> tuple[float, float, float]:
    """(sigma_r, sigma_theta, tau_r_theta) of the field without the hole: the
    limit r -> infinity of (8.113)-(8.115)."""
    mean, half = 0.5 * (s1 + s2), 0.5 * (s1 - s2)
    c, s = math.cos(2.0 * theta), math.sin(2.0 * theta)
    return mean + half * c, mean - half * c, -half * s


def _uniaxial_induced(r: float, theta: float, s: float, a: float, g: float, kappa: float
                      ) -> tuple[float, float]:
    q = a / r
    c, sn = math.cos(2.0 * theta), math.sin(2.0 * theta)
    ur = a * s / (8.0 * g) * (2.0 * q + 2.0 * ((kappa + 1.0) * q - q ** 3) * c)
    ut = a * s / (8.0 * g) * (-2.0 * ((kappa - 1.0) * q + q ** 3) * sn)
    return ur, ut


def kirsch_induced_displacement(r: float, theta: float, s1: float, s2: float,
                                a: float = A, g: float = G, kappa: float = KAPPA
                                ) -> tuple[float, float]:
    """(u_r, u_theta) caused by opening the hole, positive towards -r and
    -theta (the source's convention): sigma_1 as in (8.124)-(8.125) minus the
    field without the hole, plus sigma_2 with theta + pi/2."""
    u1 = _uniaxial_induced(r, theta, s1, a, g, kappa)
    u2 = _uniaxial_induced(r, theta + 0.5 * math.pi, s2, a, g, kappa)
    return u1[0] + u2[0], u1[1] + u2[1]


def engine_displacement(x: float, y: float, s1: float, s2: float, a: float = A
                        ) -> tuple[float, float]:
    """The same, in the engine's convention: (u_x, u_y) along +x, +y."""
    r, theta = math.hypot(x, y), math.atan2(y, x)
    ur, ut = kirsch_induced_displacement(r, theta, s1, s2, a)
    c, s = math.cos(theta), math.sin(theta)
    return -(ur * c - ut * s), -(ur * s + ut * c)


def hooke_from_displacement(r: float, theta: float, s1: float, s2: float,
                            h: float = 1e-5) -> tuple[float, float, float]:
    """The stress change that the induced displacement gives through Hooke's
    law in plane strain, with its strains by central differences:
    eps_r = du_r/dr, eps_theta = u_r/r + (1/r) du_theta/dtheta,
    gamma = (1/r) du_r/dtheta + du_theta/dr - u_theta/r (polar strains, the
    signs of the source's convention for stresses and displacements agree)."""
    def u(rr, tt):
        return kirsch_induced_displacement(rr, tt, s1, s2)
    ur, ut = u(r, theta)
    dur_dr = (u(r + h, theta)[0] - u(r - h, theta)[0]) / (2 * h)
    dut_dr = (u(r + h, theta)[1] - u(r - h, theta)[1]) / (2 * h)
    dur_dt = (u(r, theta + h)[0] - u(r, theta - h)[0]) / (2 * h)
    dut_dt = (u(r, theta + h)[1] - u(r, theta - h)[1]) / (2 * h)
    eps_r = dur_dr
    eps_t = ur / r + dut_dt / r
    gamma = dur_dt / r + dut_dr - ut / r
    vol = eps_r + eps_t
    return LAM * vol + 2.0 * G * eps_r, LAM * vol + 2.0 * G * eps_t, G * gamma


if __name__ == "__main__":
    print("hydrostatic: induced u_r(a) =", kirsch_induced_displacement(A, 0.3, P0, P0)[0],
          " p a / 2G =", P0 * A / (2 * G))
    for r, t in ((1.0, 0.0), (1.5, 0.4), (3.0, 1.2)):
        ks = kirsch_stress(r, t, 30.0, 15.0)
        ff = far_field(t, 30.0, 15.0)
        hk = hooke_from_displacement(r, t, 30.0, 15.0)
        print(f"r = {r}, theta = {t}: Kirsch - far field = "
              f"{tuple(round(k - f, 6) for k, f in zip(ks, ff))}, Hooke = {tuple(round(v, 6) for v in hk)}")
