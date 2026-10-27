# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.1 (spec 001, T5) — the reference Mohr-Coulomb returns every trial stress
to where de Souza Neto, Perić and Owen (2008, §8.2) say it must go, by the
path the flow rule says.

Invariants protected, at one integration point:

* **elastic**: a trial stress inside the surface comes back unchanged;
* **main plane**: the updated stress is on the plane (Phi = 0), in the same
  sextant, and trial - updated = D : (dgamma N1), with dgamma >= 0 — the
  plastic strain is the flow vector of Eq. (8.55);
* **right edge**: on the main plane and on the one on its right, which with
  the same c means sigma_2 = sigma_3; both multipliers >= 0, and the plastic
  strain is dgamma_a N1 + dgamma_b N6 (Eqs. 8.57-8.58);
* **left edge**: the same with N2, so sigma_1 = sigma_2 (Eq. 8.59). This is
  the test that would have caught the dgamma_b of Box 8.6 for sigma_1;
* **apex**: hydrostatic at p = c cot(phi) (Eq. 8.81); with psi = 0 it is
  refused (p. 300), not invented;
* **always admissible**: for a cloud of seeded trial stresses, the result
  never lies outside the surface, and lies on it whenever the trial did;
* **isotropy**: rotating the trial tensor in the plane rotates the result
  by the same angle;
* **the elastic part** is the same law as ``elastic.stress_increment``.
"""
from __future__ import annotations

import math
import random

from ogr_fem2d.engine.reference import mohr_coulomb as mc
from ogr_fem2d.engine.reference.elastic import stress_increment

# The material of case STR-02, with both dilatancies of the case.
MAT0 = mc.MohrCoulomb(10000.0, 0.2, 3.45, math.radians(30.0), 0.0)
MAT30 = mc.MohrCoulomb(10000.0, 0.2, 3.45, math.radians(30.0), math.radians(30.0))
MAT15 = mc.MohrCoulomb(10000.0, 0.2, 3.45, math.radians(30.0), math.radians(15.0))


def _phi_max(m, s):
    """The largest of the six yield functions = the main plane after sorting."""
    s = sorted(s, reverse=True)
    return mc.yield_function(m, s[0], s[2])


def _plastic_strain(m, trial, updated):
    """Principal plastic strain from trial - updated = D : eps_p (isotropic
    elasticity inverted in principal axes)."""
    g, k = m.shear_modulus, m.bulk_modulus
    ds = [t - u for t, u in zip(trial, updated)]
    p = sum(ds) / 3.0
    return [(d - p) / (2.0 * g) + p / (3.0 * k) for d in ds]


def _close(a, b, tol=1e-9):
    return all(abs(x - y) <= tol * max(1.0, abs(x), abs(y)) for x, y in zip(a, b))


class TestTheRegions:
    def test_inside_is_elastic(self):
        trial = (-10.0, -12.0, -15.0)
        out, region, dg = mc.return_principal(MAT0, trial)
        assert region == "elastic" and out == trial and dg == (0.0, 0.0)

    def test_main_plane(self):
        for m in (MAT0, MAT15, MAT30):
            trial = (-2.0, -20.0, -40.0)
            out, region, (dg, _) = mc.return_principal(m, trial)
            assert region == "plane", region
            assert abs(mc.yield_function(m, out[0], out[2])) < 1e-10
            assert out[0] >= out[1] >= out[2]
            assert dg > 0
            sp = math.sin(m.psi)
            want = [dg * (1 + sp), 0.0, -dg * (1 - sp)]
            assert _close(_plastic_strain(m, trial, out), want), (
                _plastic_strain(m, trial, out), want)

    def test_right_edge(self):
        for m in (MAT0, MAT15, MAT30):
            trial = (5.0, -55.0, -56.0)       # s2 close to s3
            out, region, (dga, dgb) = mc.return_principal(m, trial)
            assert region == "right edge", region
            assert abs(mc.yield_function(m, out[0], out[2])) < 1e-10
            assert abs(out[1] - out[2]) < 1e-9 * max(1.0, abs(out[1]))
            assert dga >= 0 and dgb >= 0, (dga, dgb)
            sp = math.sin(m.psi)
            want = [(dga + dgb) * (1 + sp), -dgb * (1 - sp), -dga * (1 - sp)]
            assert _close(_plastic_strain(m, trial, out), want)

    def test_left_edge(self):
        for m in (MAT0, MAT15, MAT30):
            trial = (-1.0, -2.0, -60.0)       # s2 close to s1
            out, region, (dga, dgb) = mc.return_principal(m, trial)
            assert region == "left edge", region
            assert abs(mc.yield_function(m, out[0], out[2])) < 1e-10
            assert abs(out[0] - out[1]) < 1e-9 * max(1.0, abs(out[0]))
            assert dga >= 0 and dgb >= 0, (dga, dgb)
            sp = math.sin(m.psi)
            want = [dga * (1 + sp), dgb * (1 + sp), -(dga + dgb) * (1 - sp)]
            assert _close(_plastic_strain(m, trial, out), want)

    def test_apex(self):
        for m in (MAT15, MAT30):
            trial = (30.0, 25.0, 20.0)        # tension, beyond the apex
            out, region, _ = mc.return_principal(m, trial)
            assert region == "apex", region
            p = m.cohesion / math.tan(m.phi)
            assert all(abs(s - p) < 1e-12 for s in out), out

    def test_apex_with_zero_dilatancy_is_refused(self):
        try:
            mc.return_principal(MAT0, (30.0, 25.0, 20.0))
        except mc.ReturnMappingError as exc:
            assert "psi = 0" in str(exc)
        else:
            raise AssertionError("an apex return with psi = 0 gave a stress")


class TestAlwaysAdmissible:
    def test_a_seeded_cloud_of_trial_stresses(self):
        rng = random.Random(2026)
        seen = set()
        for m in (MAT15, MAT30):
            for _ in range(3000):
                trial = tuple(sorted((rng.uniform(-80.0, 20.0) for _ in range(3)),
                                     reverse=True))
                out, region, dg = mc.return_principal(m, trial)
                seen.add(region)
                scale = max(1.0, *(abs(x) for x in trial))
                assert _phi_max(m, out) <= 1e-10 * scale, (trial, out, region)
                if region != "elastic":
                    assert abs(_phi_max(m, out)) <= 1e-10 * scale, (trial, out)
                    assert min(dg) >= -1e-14, (trial, dg)
        # the cloud reached every region, so the checks above covered them all
        assert seen == {"elastic", "plane", "right edge", "left edge", "apex"}, seen


class TestTheTensor:
    def test_the_elastic_part_is_the_elastic_law(self):
        start = (-30.0, -30.0, -30.0, 0.0)
        inc = (1e-5, -2e-5, 3e-6)
        u = mc.update(MAT0, start, inc)
        d = stress_increment(MAT0.young, MAT0.poisson, inc)
        assert u.region == "elastic"
        assert _close(u.stress, tuple(s + x for s, x in zip(start, d)), 1e-14)

    def test_isotropy_in_the_plane(self):
        start = (-30.0, -30.0, -30.0, 0.0)
        inc = (4e-3, -1e-3, 0.0)                 # plastic, with a sigma_zz
        base = mc.update(MAT30, start, inc)
        assert base.region != "elastic"
        alpha = 0.37
        c, s = math.cos(alpha), math.sin(alpha)
        # rotate the strain increment (tensor with gamma = 2 eps_xy)
        exx, eyy, exy = inc[0], inc[1], inc[2] / 2
        rxx = c * c * exx + s * s * eyy + 2 * s * c * exy
        ryy = s * s * exx + c * c * eyy - 2 * s * c * exy
        rxy = -s * c * exx + s * c * eyy + (c * c - s * s) * exy
        rot = mc.update(MAT30, start, (rxx, ryy, 2 * rxy))
        sxx, syy, szz, txy = base.stress
        want = (c * c * sxx + s * s * syy + 2 * s * c * txy,
                s * s * sxx + c * c * syy - 2 * s * c * txy,
                szz,
                -s * c * sxx + s * c * syy + (c * c - s * s) * txy)
        assert rot.region == base.region
        assert _close(rot.stress, want, 1e-10), (rot.stress, want)

    def test_the_tensor_result_is_on_the_surface(self):
        start = (-30.0, -30.0, -30.0, 0.0)
        u = mc.update(MAT0, start, (6e-3, -2e-3, 1e-3))
        p_hi, p_lo, _ = mc.principal_in_plane(u.stress[0], u.stress[1], u.stress[3])
        assert abs(_phi_max(MAT0, (p_hi, p_lo, u.stress[2]))) < 1e-9
