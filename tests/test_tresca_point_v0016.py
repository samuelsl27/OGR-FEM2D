# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.16 (spec 007, T1; RF-12, D14) — Mohr-Coulomb with phi = psi = 0 is the
Tresca model of its source, at one integration point, before it is used in
case 008 (rule 8 of AGENTS.md).

The oracle is written here from the source, apart from the code under test:
de Souza Neto, Perić and Owen (2008), §8.1.1, Boxes 8.1-8.3 (pp. 275-278),
the implicit return of the Tresca model in principal stresses, with
sigma_y = 2 c and no hardening (H = 0), so that the Newton iterations of
Boxes 8.2 and 8.3 end in one step and are written in closed form:

* elastic when s1_t - s3_t - sigma_y <= 0 (Box 8.1, iii);
* main plane: dgamma = (s1_t - s3_t - sigma_y) / (4 G), s1 = s1_t - 2 G dgamma,
  s2 = s2_t, s3 = s3_t + 2 G dgamma (Eqs. 8.16, 8.18), valid if s1 >= s2 >= s3;
* otherwise the corner chosen by T : s_t = s1_t + s3_t - 2 s2_t (Eq. 8.32):
  positive, the right one (Eqs. 8.20, 8.23); else the left (Eqs. 8.25, 8.26);
  [[4G, 2G], [2G, 4G]] (dgamma_a, dgamma_b) = (sbar_a - sigma_y, sbar_b - sigma_y);
* the pressure does not change, and sigma = sum (s_i + p) e_i e_i (Eq. 8.28).

Remark 8.2 (p. 300) says the Mohr-Coulomb returns reduce to these with
phi = psi = 0. The principal stresses of the oracle come from numpy's
eigh of the 3 x 3 tensor (sigma_zz is principal in plane strain), not from
mohr_coulomb.principal_in_plane.

Invariants protected:

* **the four regions** of a seeded cloud of trial stresses: the same stress
  (1e-12 of the stress scale), the same region and the same multipliers as
  the oracle, and the cloud covers elastic, plane and both corners;
* **no apex**: with phi = 0 no state of the cloud asks for it (the code
  refuses the apex with phi = 0; Tresca has none);
* **simple shear in plane strain**, from zero stress: tau_xy = G gamma until
  tau_xy = c, then c exactly, with sigma_xx = sigma_yy = sigma_zz = 0 (with
  them zero, sigma_1 - sigma_3 = 2 tau; Eq. 8.12 with sigma_y = 2 c);
* **the consistent tangent** in the plane and both corners equals the
  central difference of the update (it is what the Newton of the stage
  uses in case 008);
* **Rust** gives what the reference gives over the same cloud (ADR-0001,
  criterion 1: 1e-10).

The material is that of case 008 (ficha VER-STR-05), in MPa: E = 250,
nu = 0.2, c = 0.1.
"""
from __future__ import annotations

import numpy as np

from ogr_fem2d.engine import interface
from ogr_fem2d.engine.reference import mohr_coulomb as mc

E, NU, C = 250.0, 0.2, 0.1
TRESCA = mc.MohrCoulomb(E, NU, C, 0.0, 0.0)
G = E / (2.0 * (1.0 + NU))
SIGMA_Y = 2.0 * C
SCALE = 1.0          # MPa: the stresses of the cloud are below it


def _trial(start, inc):
    """The elastic trial stress (sigma_xx, yy, zz, tau_xy) of plane strain,
    from Lamé's constants (Eq. 4.16 written apart)."""
    lam = E * NU / ((1.0 + NU) * (1.0 - 2.0 * NU))
    ex, ey, gxy = inc
    vol = ex + ey
    return (start[0] + lam * vol + 2.0 * G * ex, start[1] + lam * vol + 2.0 * G * ey,
            start[2] + lam * vol, start[3] + G * gxy)


def tresca(start, inc):
    """Boxes 8.1-8.3 with H = 0: (stress, region, (dgamma_a, dgamma_b))."""
    t = _trial(start, inc)
    tensor = np.array([[t[0], t[3], 0.0], [t[3], t[1], 0.0], [0.0, 0.0, t[2]]])
    values, vectors = np.linalg.eigh(tensor)
    order = np.argsort(values)[::-1]
    sig, e = values[order], vectors[:, order]
    p = sig.mean()
    s1, s2, s3 = sig - p
    if s1 - s3 - SIGMA_Y <= 1e-12 * SCALE:
        return t, "elastic", (0.0, 0.0)
    dg = (s1 - s3 - SIGMA_Y) / (4.0 * G)
    s = (s1 - 2.0 * G * dg, s2, s3 + 2.0 * G * dg)
    region, dgamma = "plane", (dg, 0.0)
    if not (s[0] >= s[1] - 1e-12 and s[1] >= s[2] - 1e-12):
        right = s1 + s3 - 2.0 * s2 > 0.0
        sb = (s1 - s2) if right else (s2 - s3)
        a, b = np.linalg.solve([[4.0 * G, 2.0 * G], [2.0 * G, 4.0 * G]],
                               [s1 - s3 - SIGMA_Y, sb - SIGMA_Y])
        if right:
            s = (s1 - 2.0 * G * (a + b), s2 + 2.0 * G * b, s3 + 2.0 * G * a)
        else:
            s = (s1 - 2.0 * G * a, s2 - 2.0 * G * b, s3 + 2.0 * G * (a + b))
        region, dgamma = ("right edge" if right else "left edge"), (a, b)
    full = sum((si + p) * np.outer(e[:, i], e[:, i]) for i, si in enumerate(s))
    return (full[0, 0], full[1, 1], full[2, 2], full[0, 1]), region, dgamma


def _cloud(n=4000, seed=7):
    rng = np.random.default_rng(seed)
    start = np.column_stack([rng.uniform(-0.5, 0.2, (n, 3)), rng.uniform(-0.1, 0.1, n)])
    # the starting state inside the surface, as in a stage: scaled back
    # towards its pressure until sigma_1 - sigma_3 <= 2 c
    for row in start:
        t = np.array([[row[0], row[3], 0.0], [row[3], row[1], 0.0], [0.0, 0.0, row[2]]])
        v = np.linalg.eigvalsh(t)
        if v[-1] - v[0] > SIGMA_Y:
            p = v.mean()
            f = 0.99 * SIGMA_Y / (v[-1] - v[0])
            row[:3] = p + f * (row[:3] - p)
            row[3] *= f
    strains = rng.uniform(-2e-3, 2e-3, (n, 3))
    return start, strains


class TestTheReturnIsTresca:
    def test_every_region_of_the_cloud(self):
        start, strains = _cloud()
        seen = set()
        for s0, inc in zip(start, strains):
            got = mc.update(TRESCA, tuple(s0), tuple(inc))
            want, region, dgamma = tresca(s0, inc)
            assert got.region == region, (s0, inc, got.region, region)
            gap = max(abs(a - b) for a, b in zip(got.stress, want))
            assert gap <= 1e-12 * SCALE, (region, gap)
            assert abs(got.dgamma[0] - dgamma[0]) <= 1e-12 * SCALE / G
            assert abs(got.dgamma[1] - dgamma[1]) <= 1e-12 * SCALE / G
            assert min(got.dgamma) >= -1e-15
            seen.add(region)
        assert seen == {"elastic", "plane", "right edge", "left edge"}, seen

    def test_no_state_asks_for_the_apex(self):
        # mc.update raises ReturnMappingError at the apex with phi = 0: a
        # cloud ten times larger, with larger increments, never gets there
        start, _ = _cloud(n=40000, seed=8)
        strains = np.random.default_rng(9).uniform(-2e-2, 2e-2, (40000, 3))
        regions = {mc.update(TRESCA, tuple(s0), tuple(inc)).region
                   for s0, inc in zip(start, strains)}
        assert "apex" not in regions and {"right edge", "left edge"} <= regions


class TestSimpleShear:
    def test_tau_reaches_c_and_stays(self):
        stress = (0.0, 0.0, 0.0, 0.0)
        dg = 0.1 * C / G                    # 10 increments to yield, 30 in all
        for k in range(1, 31):
            stress = mc.update(TRESCA, stress, (0.0, 0.0, dg)).stress
            assert abs(stress[3] - min(G * k * dg, C)) <= 1e-12 * C, (k, stress)
            assert max(abs(x) for x in stress[:3]) <= 1e-12 * C, (k, stress)


def _numerical(start, inc, h=1e-9):
    base = mc.update(TRESCA, start, inc)
    columns = []
    for j in range(3):
        plus, minus = list(inc), list(inc)
        plus[j] += h
        minus[j] -= h
        up, um = mc.update(TRESCA, start, tuple(plus)), mc.update(TRESCA, start, tuple(minus))
        if up.region != base.region or um.region != base.region:
            return None
        columns.append([(up.stress[c] - um.stress[c]) / (2 * h) for c in (0, 1, 3)])
    return [[columns[j][i] for j in range(3)] for i in range(3)]


class TestTheTangent:
    def test_it_is_the_derivative_of_the_update(self):
        start, strains = _cloud(n=600, seed=21)
        checked = set()
        for s0, inc in zip(start, strains):
            u = mc.update(TRESCA, tuple(s0), tuple(inc), tangent=True)
            if u.region == "elastic":
                continue
            numerical = _numerical(tuple(s0), tuple(inc))
            if numerical is None:
                continue
            gap = max(abs(u.tangent[i][j] - numerical[i][j]) for i in range(3) for j in range(3))
            assert gap <= 1e-5 * E, (u.region, gap)
            checked.add(u.region)
        assert checked == {"plane", "right edge", "left edge"}, checked


class TestRust:
    def test_the_same_cloud(self):
        from ogr_fem2d.engine.compiled import RUST
        start, strains = _cloud()
        n = len(start)
        rows = np.tile(interface.material_row(TRESCA), (n, 1))
        g = interface.Geometry(0, np.zeros((n, 6), np.int64), np.zeros((n, 6)),
                               np.zeros((n, 6)), np.zeros(n), np.arange(n),
                               np.zeros(n, np.int64), np.zeros((n, 2)), rows)
        got = RUST.prepare(g).integrate(start, strains)
        ref = [mc.update(TRESCA, tuple(s0), tuple(inc), tangent=True)
               for s0, inc in zip(start, strains)]
        assert np.abs(got.stresses - np.array([r.stress for r in ref])).max() <= 1e-10 * SCALE
        assert np.array_equal(got.plastic, np.array([r.region != "elastic" for r in ref]))
        assert np.abs(got.tangents - np.array([r.tangent for r in ref])).max() <= 1e-10 * E


class TestHugeTrialStresses:
    """Spec 007, T5: a trial stress 1e4 times c, from an iterate far from
    equilibrium. The edge return is valid, but its sigma_2 = sigma_3 comes
    with a rounding of the order of 1e-16 of the trial; the order check
    measured its tolerance against the returned stress alone and refused
    it, then refused the apex (phi = 0). The state is the one found in case
    008 (changelog v0.0.16, T5)."""
    TRIAL = (19491.297628738663, 1.0127285971657638, -19486.233985752835)

    def test_the_state_of_case_008_goes_to_the_right_edge(self):
        stress, region, (dga, dgb) = mc.return_principal(TRESCA, self.TRIAL)
        assert region == "right edge" and dga >= 0.0 and dgb >= 0.0
        assert abs(stress[0] - stress[2] - 2.0 * C) <= 1e-12 * max(self.TRIAL)
        assert abs(stress[1] - stress[2]) <= 1e-12 * max(self.TRIAL)
        p = sum(self.TRIAL) / 3.0
        assert abs(sum(stress) / 3.0 - p) <= 1e-12 * max(self.TRIAL)    # Tresca keeps p

    def test_a_cloud_of_huge_deviators_never_asks_for_the_apex(self):
        # strain increments of up to 100: deviatoric trial stresses up to
        # 1e4 MPa, against c = 0.1 MPa; the reference and Rust alike
        from ogr_fem2d.engine.compiled import RUST
        rng = np.random.default_rng(31)
        n = 20000
        start, _ = _cloud(n=n, seed=32)
        strains = rng.uniform(-100.0, 100.0, (n, 3))
        ref = [mc.update(TRESCA, tuple(s0), tuple(inc)) for s0, inc in zip(start, strains)]
        regions = {r.region for r in ref}       # mc.update raises at the apex
        assert {"right edge", "left edge"} <= regions <= {"right edge", "left edge", "plane"}, regions
        rows = np.tile(interface.material_row(TRESCA), (n, 1))
        g = interface.Geometry(0, np.zeros((n, 6), np.int64), np.zeros((n, 6)),
                               np.zeros((n, 6)), np.zeros(n), np.arange(n),
                               np.zeros(n, np.int64), np.zeros((n, 2)), rows)
        got = RUST.prepare(g).integrate(start, strains)
        want = np.array([r.stress for r in ref])
        assert np.abs(got.stresses - want).max() <= 1e-10 * np.abs(want).max()
