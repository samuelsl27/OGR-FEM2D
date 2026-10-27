# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Closed-form references of spec 001 (task T1), checked against their sources.

Run it with the project's environment:

    .venv/Scripts/python spec/features/001-prueba-de-concepto/comprobaciones/soluciones_cerradas.py

It prints, for the data of cases STR-01 and STR-02, every check that task T1
records in ``plan.md``. Nothing here is the engine: it is the external side of
the comparison, written out so that each number can be traced to an equation.

Conventions INSIDE this file: stresses compression-positive and radial
displacement positive INWARD, as in both sources (Jaeger, Cook and Zimmerman
2007; Salençon 1969 counts tension positive, and is converted where used).
The engine uses tension positive (spec 001, D1); the tests convert.

Sources:

* Jaeger, J. C., Cook, N. G. W. and Zimmerman, R. W. (2007). *Fundamentals of
  Rock Mechanics*, 4th ed., §8.4: hollow cylinder (8.73)-(8.89) and hole in an
  infinite medium (8.90)-(8.92); §8.5: Kirsch (8.104)-(8.106).
* Salençon, J. (1969). « Contraction quasi-statique d'une cavité à symétrie
  sphérique ou cylindrique dans un milieu élasto-plastique ». Annales des Ponts
  et Chaussées, IV, pp. 231-236: criterion and flow (§3), cylindrical cavity
  (§5): (2''), (3''), (9''), (4''), (6''), and r(r0, c) for k = 1 (p. 236).
"""
from __future__ import annotations

import math

from scipy.integrate import solve_ivp
from scipy.optimize import brentq

# Data of the cases (fichas VER-STR-01 and VER-STR-02)
E, NU = 10000.0, 0.2            # MPa, -
P0, PI = 30.0, 0.0              # far-field (initial) and internal pressure, MPa
A = 1.0                         # hole radius, m
COH, PHI = 3.45, math.radians(30.0)

G = E / (2.0 * (1.0 + NU))
KM1 = 2.0 * (1.0 - 2.0 * NU)    # (kappa - 1) for plane strain, JCZ 2007 below (8.86)
H = COH / math.tan(PHI)         # Salençon's H = C cotg(phi)
KP = (1.0 + math.sin(PHI)) / (1.0 - math.sin(PHI))   # = tg^2(pi/4 + phi/2)


def k_flow(psi: float) -> float:
    """Salençon's k for a dilatancy psi: eps_p_theta = -k eps_p_r (§3.1).

    k = 1 is « l'hypothèse de Mohr » (no plastic volume change, psi = 0) and
    k = Ka is the associated case. For the contracting cylinder, with
    sigma_r = sigma_1 and sigma_theta = sigma_3 (§5), a plastic potential
    sigma_3 - Kps sigma_1 gives k = 1 / Kps, Kps = (1 + sin psi)/(1 - sin psi).
    """
    return (1.0 - math.sin(psi)) / (1.0 + math.sin(psi))


# ---------------------------------------------------------------- elastic
def kirsch_hydrostatic(r: float) -> tuple[float, float, float]:
    """(sigma_r, sigma_theta, u_in) of the excavation in an infinite medium.

    JCZ 2007 (8.90)-(8.92) with Pi = 0; u_in is the part due to the hole only
    (the (1 - 2 nu) P0 r term of (8.90) is the displacement of the in-situ
    field from an unstressed state, which the excavation does not cause).
    The sign of sigma_theta is that of the limit b -> inf of (8.86), and of
    (8.104) with sigma_1 = sigma_2: + (Po - Pi)(a/r)^2.
    """
    return (P0 - (P0 - PI) * (A / r) ** 2,
            P0 + (P0 - PI) * (A / r) ** 2,
            (P0 - PI) * A ** 2 / (2.0 * G * r))


def lame_fixed_outer(r: float, b: float) -> tuple[float, float, float]:
    """The same excavation on a FINITE ring a <= r <= b with u(b) = 0.

    From the general solution JCZ 2007 (8.78)-(8.81), compression positive:
    2G u_r = (kappa - 1) c r - d / r, sigma_r = 2c + d/r^2, sigma_theta =
    2c - d/r^2, applied to the increment of the excavation: d_sigma_r(a) =
    -(P0 - Pi) and d_u(b) = 0. Exact for the model as it is meshed.
    """
    c = -(P0 - PI) / (2.0 + KM1 * b ** 2 / A ** 2)
    d = KM1 * c * b ** 2
    return (P0 + 2.0 * c + d / r ** 2,
            P0 + 2.0 * c - d / r ** 2,
            (KM1 * c * r - d / r) / (2.0 * G))


# ---------------------------------------------------------------- Salençon
def _plastic_stress(r: float) -> tuple[float, float]:
    """Plastic zone, compression positive: Salençon (2'') with (3''), and the
    criterion (sigma_theta - H) = Kp (sigma_r - H), tension positive (§5)."""
    s_r = -H + (PI + H) * (r / A) ** (KP - 1.0)
    return s_r, KP * s_r + H * (KP - 1.0)


def _integrate_plastic(r0: float, u0_in: float, psi: float) -> float:
    """u_in(a) from u_in(r0), small strain, plastic zone a <= r <= r0.

    Salençon's flow (§3.1) integrated in time, since every point that yields
    keeps yielding with the same k: eps_p_theta = -k eps_p_r. With
    eps_r = du/dr and eps_theta = u/r (u outward) this is
    u/r + k du/dr = e_theta + k e_r, the elastic strains of plane strain
    (eps_z = 0 and, sigma_z being intermediate, eps_p_z = 0: (4'')) from the
    initial state. It is the small-strain form of (6'').
    """
    k = k_flow(psi)

    def rhs(r, u):
        s_r, s_t = _plastic_stress(r)
        d_r, d_t = P0 - s_r, P0 - s_t          # tension-positive increments
        e_r = ((1.0 - NU) * d_r - NU * d_t) / (2.0 * G)
        e_t = ((1.0 - NU) * d_t - NU * d_r) / (2.0 * G)
        return [((e_t + k * e_r) - u[0] / r) / k]

    sol = solve_ivp(rhs, (r0, A), [-u0_in], rtol=1e-12, atol=1e-15)
    return -sol.y[0][-1]


def salencon_infinite(psi: float) -> dict:
    """R0, sigma_re and u_in(a) in an infinite medium.

    R0 from (3'') solved for c; sigma_re from (2'') at r = c; the elastic zone
    is the hole solution with sigma_re at R0. u_in(a) by _integrate_plastic.
    """
    r0 = A * (2.0 * (P0 + H) / ((1.0 + KP) * (PI + H))) ** (1.0 / (KP - 1.0))
    s_re = (2.0 * P0 - H * (KP - 1.0)) / (KP + 1.0)
    u_r0 = (P0 - s_re) * r0 / (2.0 * G)
    return {"R0": r0, "s_re": s_re, "u_R0": u_r0,
            "u_a": _integrate_plastic(r0, u_r0, psi)}


def salencon_finite(b: float, psi: float) -> dict:
    """The same with the outer boundary FIXED at b (u(b) = 0).

    The plastic stresses do not depend on b; the elastic ring R0 <= r <= b is
    lame-like (JCZ 2007 (8.78)-(8.81)) with sigma_r(R0) continuous and the
    criterion met at R0 from the elastic side, which fixes R0. Our derivation
    from the two sources; it reproduces salencon_infinite when b -> inf.
    """
    def unknowns(r0):
        c = (_plastic_stress(r0)[0] - P0) / (2.0 + KM1 * b ** 2 / r0 ** 2)
        d = KM1 * c * b ** 2
        s_r, s_t = P0 + 2.0 * c + d / r0 ** 2, P0 + 2.0 * c - d / r0 ** 2
        return s_t - (KP * s_r + H * (KP - 1.0)), c, d

    r0 = brentq(lambda R: unknowns(R)[0], A * 1.0001, b * 0.999)
    _, c, d = unknowns(r0)
    u_r0 = (KM1 * c * r0 - d / r0) / (2.0 * G)
    return {"R0": r0, "u_R0": u_r0, "u_a": _integrate_plastic(r0, u_r0, psi)}


def ficha_u(r: float, psi: float) -> float:
    """The displacement formula of ficha VER-STR-02 (transcribed from the
    manual of the reference program), to be checked, not used."""
    kps = (1.0 + math.sin(psi)) / (1.0 - math.sin(psi))
    sol = salencon_infinite(psi)
    r0, s_re = sol["R0"], sol["s_re"]
    if r >= r0:
        return r0 ** 2 / (2.0 * G) * (P0 - s_re) / r
    q = PI + H
    return r / (2.0 * G) * ((2.0 * NU - 1.0) * (P0 + H)
                            + (1.0 - NU) * (KP ** 2 - 1.0) / (KP + kps) * q
                            * (r0 / A) ** (KP - 1.0) * (r0 / r) ** (kps + 1.0)
                            + ((1.0 - NU) * (KP * kps + 1.0) / (KP + kps) - NU)
                            * q * (r / A) ** (KP - 1.0))


def salencon_k1_published(r0_pos: float) -> float:
    """u_in at initial radius r0_pos, linearised from Salençon p. 236
    (Coulomb, k = 1, finite strain): r^2 = r0^2 + ... ; u ~ (r^2 - r0^2)/(2 r0)."""
    c = salencon_infinite(0.0)["R0"]
    q = P0 + H
    r2_minus = (2.0 * q / E * (1 - 2 * NU) * (1 + NU) * r0_pos ** 2
                - 4.0 * q / E / (1 + KP) * (1 - 2 * NU) * (1 + NU)
                * r0_pos ** (1 + KP) * c ** (1 - KP)
                + 4.0 * q / E * (1 - KP) / (1 + KP) * (1 - NU ** 2) * c ** 2)
    return -r2_minus / (2.0 * r0_pos)


if __name__ == "__main__":
    print("Kirsch, wall:", kirsch_hydrostatic(A))
    for psi_deg in (0.0, 30.0):
        psi = math.radians(psi_deg)
        s = salencon_infinite(psi)
        print(f"Salencon psi={psi_deg:.0f}: R0={s['R0']:.6f} s_re={s['s_re']:.5f} "
              f"u_a={s['u_a']:.9f}  ficha={ficha_u(A, psi):.9f}")
    print("Salencon k=1 published (linearised) u_a:", f"{salencon_k1_published(A):.9f}")
    print(" b    STR-01 u_a vs Kirsch   STR-02 psi=0   STR-02 psi=30")
    u_k = kirsch_hydrostatic(A)[2]
    s0 = salencon_infinite(0.0)["u_a"]
    s30 = salencon_infinite(math.radians(30.0))["u_a"]
    for b in (21.0, 100.0):
        print(f"{b:5.0f}  {(lame_fixed_outer(A, b)[2] / u_k - 1) * 100:+8.3f} %"
              f"   {(salencon_finite(b, 0.0)['u_a'] / s0 - 1) * 100:+8.3f} %"
              f"   {(salencon_finite(b, math.radians(30.0))['u_a'] / s30 - 1) * 100:+8.3f} %")
