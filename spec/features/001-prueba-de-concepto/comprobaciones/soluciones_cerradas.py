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
* de Souza Neto, E. A., Perić, D. and Owen, D. R. J. (2008). Computational
  Methods for Plasticity, Wiley, §8.2: the flow vectors of an edge of the
  Mohr-Coulomb pyramid, Eqs. (8.58)-(8.59), for the edge zone below.

THE EXACT SOLUTION OF THE MODEL (spec 001, D8). Salençon assumes sigma_z is the
intermediate principal stress (§5, (4'')). With the data of STR-02 it is not
near the wall: with no plastic strain in z, sigma_z = P0 - nu (d_sigma_r +
d_sigma_theta) would reach 20.39 MPa at r = a, above sigma_theta = 11.95 MPa,
so for a <= r < r_e = 1.2814 m the stress lies on the edge sigma_z =
sigma_theta and the flow has a z component. Equilibrium does not involve
sigma_z, so sigma_r, sigma_theta and R0 stay Salençon's; the displacement
does not: salencon_edge_* below. Salençon's own u_r(a) is kept as an
informative value.
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


# ------------------------------------------------- Salençon with the edge
def sigma_z_without_plastic_z(r: float) -> float:
    """sigma_z in the plastic zone if eps_p_z = 0 (Salençon's (4'')): the
    elastic eps_z is then zero, so d_sigma_z = nu (d_sigma_r + d_sigma_theta)
    (plane strain), compression positive."""
    s_r, s_t = _plastic_stress(r)
    return P0 - NU * ((P0 - s_r) + (P0 - s_t))


def edge_radius() -> float:
    """r_e: below it sigma_z (as above) would exceed sigma_theta, and the
    stress is on the edge sigma_z = sigma_theta. A if there is no such zone."""
    def excess(r):
        return sigma_z_without_plastic_z(r) - _plastic_stress(r)[1]
    if excess(A) <= 0.0:
        return A
    return brentq(excess, A, 10.0 * A)


def _integrate_plastic_with_edge(r0: float, u0_in: float, psi: float) -> float:
    """u_in(a) from u_in(r0), small strain, with the edge zone.

    Flow: on the main plane (sigma_1 = sigma_r, sigma_3 = sigma_theta, tension
    positive) the vector N1 of Eq. (8.55); on the edge with sigma_z =
    sigma_theta, N1 and the vector of the plane (sigma_r, sigma_z), Eqs.
    (8.58)-(8.59) with psi:
        eps_p = dgamma_a [(1 + sin psi) e_r - (1 - sin psi) e_theta]
              + dgamma_b [(1 + sin psi) e_r - (1 - sin psi) e_z].
    With k = (1 - sin psi)/(1 + sin psi) both give, at every instant and so in
    total, k eps_p_r + eps_p_theta + eps_p_z = 0. Plane strain, eps_z = 0, so
    eps_p_z = -e_z (the elastic z strain, zero on the plane zone), and with
    eps_r = du/dr, eps_theta = u/r (u outward):
        u/r + k du/dr = e_theta + k e_r + e_z,
    the elastic strains being those of the stress change from P0 (three
    dimensional, sigma_z = sigma_theta in the edge zone). Without the edge
    zone it is _integrate_plastic. Its consistency (dgamma_a, dgamma_b >= 0:
    eps_p_theta <= 0 everywhere, e_z >= 0 in the edge zone) is checked by
    check_edge_consistency(). Our derivation from the two sources.
    """
    k = k_flow(psi)
    r_e = edge_radius()

    def rhs(r, u):
        e_r, e_t, e_z = _elastic_strains_with_edge(r, r_e)
        return [((e_t + k * e_r + e_z) - u[0] / r) / k]

    sol = solve_ivp(rhs, (r0, A), [-u0_in], rtol=1e-12, atol=1e-15,
                    max_step=1e-3)
    return -sol.y[0][-1]


def _elastic_strains_with_edge(r: float, r_e: float
                               ) -> tuple[float, float, float]:
    """(e_r, e_theta, e_z) of the stress change from the field, isotropic
    elasticity, tension positive."""
    s_r, s_t = _plastic_stress(r)
    s_z = s_t if r < r_e else sigma_z_without_plastic_z(r)
    d_r, d_t, d_z = P0 - s_r, P0 - s_t, P0 - s_z
    return ((d_r - NU * (d_t + d_z)) / E,
            (d_t - NU * (d_r + d_z)) / E,
            (d_z - NU * (d_r + d_t)) / E)


def salencon_edge_infinite(psi: float) -> dict:
    """R0 and the elastic zone of salencon_infinite; u_in(a) with the edge."""
    base = salencon_infinite(psi)
    return {"R0": base["R0"], "r_e": edge_radius(),
            "u_a": _integrate_plastic_with_edge(base["R0"], base["u_R0"], psi),
            "u_a_salencon": base["u_a"]}


def salencon_edge_finite(b: float, psi: float) -> dict:
    """The same on the ring with u(b) = 0 (the elastic part of
    salencon_finite)."""
    base = salencon_finite(b, psi)
    return {"R0": base["R0"], "r_e": edge_radius(),
            "u_a": _integrate_plastic_with_edge(base["R0"], base["u_R0"], psi),
            "u_a_salencon": base["u_a"]}


def check_edge_consistency(psi: float, n: int = 400) -> tuple[float, float]:
    """(min of -eps_p_theta over the plastic zone, min of e_z over the edge
    zone): both must be >= 0 for the multipliers to be non-negative."""
    k = k_flow(psi)
    r_e = edge_radius()
    base = salencon_infinite(psi)

    def rhs(r, u):
        e_r, e_t, e_z = _elastic_strains_with_edge(r, r_e)
        return [((e_t + k * e_r + e_z) - u[0] / r) / k]

    sol = solve_ivp(rhs, (base["R0"], A), [-base["u_R0"]], rtol=1e-12,
                    atol=1e-15, max_step=1e-3, dense_output=True)
    worst_theta, worst_z = math.inf, math.inf
    for i in range(1, n):
        r = A + (base["R0"] - A) * i / n
        e_r, e_t, e_z = _elastic_strains_with_edge(r, r_e)
        worst_theta = min(worst_theta, -(sol.sol(r)[0] / r - e_t))
        if r < r_e:
            worst_z = min(worst_z, e_z)
    return worst_theta, worst_z


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
    print(f"Edge zone (D8): r_e = {edge_radius():.4f} m; "
          f"sigma_z without plastic z at r = a: {sigma_z_without_plastic_z(A):.3f} MPa "
          f"vs sigma_theta(a) = {_plastic_stress(A)[1]:.3f} MPa")
    for psi_deg in (0.0, 30.0):
        psi = math.radians(psi_deg)
        inf = salencon_edge_infinite(psi)
        worst_theta, worst_z = check_edge_consistency(psi)
        print(f"psi={psi_deg:.0f}: u_a with edge {inf['u_a']:.9f} "
              f"({(inf['u_a'] / inf['u_a_salencon'] - 1) * 100:+.3f} % on Salencon); "
              f"b=21 {salencon_edge_finite(21.0, psi)['u_a']:.9f}, "
              f"b=100 {salencon_edge_finite(100.0, psi)['u_a']:.9f}; "
              f"consistency (>= 0): {worst_theta:.2e} {worst_z:.2e}")
