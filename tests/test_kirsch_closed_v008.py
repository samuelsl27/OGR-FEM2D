# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.8 (spec 003, T10) — Kirsch with a non-hydrostatic field: the
displacement the excavation causes (spec/features/003-malla/comprobaciones/
soluciones_cerradas.py), the external side of case 005's identity.

Source: Jaeger, Cook and Zimmerman (2007), §8.5: stresses (8.113)-(8.115),
p. 219; displacements (8.121)-(8.125), pp. 220-221. The induced displacement
is (8.124)-(8.125) minus the field without the hole (own derivation).

Invariants protected, each a check of one part of the source against
another:

* **hydrostatic**: with sigma_1 = sigma_2 = p the induced u_r is
  p a^2 / (2 G r), the (8.90) of spec 001 (its kirsch_hydrostatic), and
  u_theta is zero;
* **Hooke**: the strains of the induced displacement (central differences,
  polar strains) give through Hooke's law in plane strain the stress change
  of (8.113)-(8.115) minus the far field, everywhere and for uniaxial,
  biaxial and inverted fields; this fixes the signs of u_r AND u_theta and
  the subtraction of the field without the hole;
* **the hole is free and the hole is far**: (8.113)-(8.115) give
  sigma_r = tau = 0 at r = a, and the induced displacement decays as 1/r;
* **the engine's convention**: engine_displacement is the induced
  displacement turned to +x, +y: its outward radial part is -u_r.
"""
from __future__ import annotations

import math

from _hole import closed as closed_001
from _kirsch import closed as k

POINTS = [(r, t) for r in (1.0, 1.2, 2.0, 4.5) for t in (0.0, 0.3, 1.1, 2.0, 3.0, 4.4)]
FIELDS = [(30.0, 15.0), (30.0, 0.0), (10.0, 40.0), (20.0, -5.0)]


class TestHydrostatic:
    def test_it_is_the_8_90_of_spec_001(self):
        for r, t in POINTS:
            ur, ut = k.kirsch_induced_displacement(r, t, k.P0, k.P0)
            assert math.isclose(ur, closed_001.kirsch_hydrostatic(r)[2], rel_tol=1e-14)
            assert abs(ut) <= 1e-18


class TestHooke:
    def test_the_strains_give_the_stress_change_of_kirsch(self):
        for s1, s2 in FIELDS:
            scale = max(abs(s1), abs(s2))
            for r, t in POINTS:
                if r == 1.0:
                    continue            # central differences need both sides
                ks, ff = k.kirsch_stress(r, t, s1, s2), k.far_field(t, s1, s2)
                hk = k.hooke_from_displacement(r, t, s1, s2)
                for got, a, b in zip(hk, ks, ff):
                    assert abs(got - (a - b)) <= 1e-6 * scale, (s1, s2, r, t, got, a - b)


class TestHoleAndFar:
    def test_the_hole_is_free(self):
        for s1, s2 in FIELDS:
            for t in (0.0, 0.7, 2.5):
                sr, _st, tau = k.kirsch_stress(k.A, t, s1, s2)
                assert abs(sr) <= 1e-13 * abs(s1) and abs(tau) <= 1e-13 * abs(s1)

    def test_the_induced_displacement_decays_as_1_over_r(self):
        for s1, s2 in FIELDS:
            u10 = k.kirsch_induced_displacement(1e3, 0.4, s1, s2)
            u20 = k.kirsch_induced_displacement(2e3, 0.4, s1, s2)
            for a, b in zip(u10, u20):
                assert math.isclose(a, 2.0 * b, rel_tol=1e-5), (a, b)


class TestEngineConvention:
    def test_outward_radial_part_is_minus_u_r(self):
        for s1, s2 in FIELDS:
            for r, t in POINTS:
                x, y = r * math.cos(t), r * math.sin(t)
                ux, uy = k.engine_displacement(x, y, s1, s2)
                ur, ut = k.kirsch_induced_displacement(r, t, s1, s2)
                out = ux * math.cos(t) + uy * math.sin(t)
                ccw = -ux * math.sin(t) + uy * math.cos(t)
                assert math.isclose(out, -ur, rel_tol=1e-12, abs_tol=1e-18)
                assert math.isclose(ccw, -ut, rel_tol=1e-12, abs_tol=1e-18)
