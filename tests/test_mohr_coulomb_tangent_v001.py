# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.1 (spec 001, D7) — the consistent tangent of the reference
Mohr-Coulomb is the derivative of its own stress update, and the principal
derivatives are those of the source.

Invariants protected:

* **it is the derivative**: for a seeded cloud of starting stresses and
  strain increments covering the elastic region, the main plane, both edges
  and the apex, every column of the tangent equals the central difference of
  update() in that strain component, to 1e-8 of E (the difference itself is
  good to about 1e-9 with h = 1e-8: the returns are piecewise affine, so it
  is exact up to rounding when the region does not change, and points whose
  region changes within +-h are skipped);
* **equal in-plane principal stresses**: the limit of Eq. (A.30) of de
  Souza Neto et al. (2008) is the derivative there too;
* **against the source**: the principal-stress derivatives d sigma_i /
  d eps_trial_j of the main plane and of both edges equal, to rounding, the
  expressions of subroutine CTMC (de Souza Neto et al. 2008, pp. 320-323,
  lines 100-176 and 194-214), transcribed below with H = 0, for psi = 0, 15
  and 30 degrees. They are built in the engine from the return equations, not
  copied: two independent routes to the same matrix;
* **apex**: without hardening the tangent is zero (Remark 8.3);
* **elastic**: the tangent of an elastic update is the matrix of Eq. (4.16)
  of Zienkiewicz and Taylor (2000).
"""
from __future__ import annotations

import math
import random

from ogr_fem2d.engine.reference import mohr_coulomb as mc
from ogr_fem2d.engine.reference.elastic import plane_strain_matrix

E, NU, C, PHI = 10000.0, 0.2, 3.45, math.radians(30.0)
MATERIALS = [mc.MohrCoulomb(E, NU, C, PHI, math.radians(p)) for p in (0, 15, 30)]


def _numerical(m, start, inc, h=1e-8):
    """Columns of d sigma / d eps by central differences, or None when the
    region changes within +-h."""
    base = mc.update(m, start, inc)
    columns = []
    for j in range(3):
        plus, minus = list(inc), list(inc)
        plus[j] += h
        minus[j] -= h
        try:
            up, um = mc.update(m, start, tuple(plus)), mc.update(m, start, tuple(minus))
        except mc.ReturnMappingError:
            return None
        if up.region != base.region or um.region != base.region:
            return None
        columns.append([(up.stress[c] - um.stress[c]) / (2 * h) for c in (0, 1, 3)])
    return [[columns[j][i] for j in range(3)] for i in range(3)]


def _largest_gap(a, b):
    return max(abs(a[i][j] - b[i][j]) for i in range(3) for j in range(3))


class TestItIsTheDerivative:
    def test_a_seeded_cloud_covering_every_region(self):
        rng = random.Random(3)
        seen = set()
        for _ in range(3000):
            m = rng.choice(MATERIALS)
            start = tuple(rng.uniform(-40.0, 5.0) for _ in range(3)) + (rng.uniform(-10.0, 10.0),)
            inc = tuple(rng.uniform(-3e-3, 3e-3) for _ in range(3))
            try:
                u = mc.update(m, start, inc, tangent=True)
            except mc.ReturnMappingError:
                continue                       # the apex with psi = 0
            numerical = _numerical(m, start, inc)
            if numerical is None:
                continue
            assert _largest_gap(u.tangent, numerical) < 1e-8 * E, (u.region, start, inc)
            seen.add(u.region)
        assert seen == {"elastic", "plane", "right edge", "left edge", "apex"}, seen

    def test_equal_in_plane_principal_stresses(self):
        for m in MATERIALS:
            for inc in ((0.0, 0.0, 0.0), (1e-4, 1e-4, 0.0)):
                start = (-5.0, -5.0, -40.0, 0.0)      # sigma_xx = sigma_yy, plastic
                u = mc.update(m, start, inc, tangent=True)
                assert u.region != "elastic"
                numerical = _numerical(m, start, inc)
                assert numerical is not None
                assert _largest_gap(u.tangent, numerical) < 1e-8 * E, u.region

    def test_the_elastic_tangent_is_the_elastic_matrix(self):
        u = mc.update(MATERIALS[0], (-30.0, -30.0, -30.0, 0.0), (1e-5, -1e-5, 2e-5),
                      tangent=True)
        assert u.region == "elastic"
        assert _largest_gap(u.tangent, plane_strain_matrix(E, NU)) < 1e-9

    def test_the_apex_tangent_is_zero(self):
        m = MATERIALS[2]
        u = mc.update(m, (0.0, 0.0, 0.0, 0.0), (5e-3, 5e-3, 0.0), tangent=True)
        assert u.region == "apex"
        assert max(abs(x) for row in u.tangent for x in row) == 0.0


def _ctmc_plane(m):
    """CTMC, lines 194-214, H = 0: DPSTRS for the main plane, rows and
    columns (max, mid, min) = (II, MM, JJ)."""
    g, k = m.shear_modulus, m.bulk_modulus
    sf, sp = math.sin(m.phi), math.sin(m.psi)
    consta = 4 * g * (1 + sf * sp / 3) + 4 * k * sf * sp
    denom = -consta
    b1 = (2 * g * (1 + sp / 3) + 2 * k * sp) / denom
    b2 = (4 * g / 3 - 2 * k) * sp / denom
    b3 = (2 * g * (1 - sp / 3) - 2 * k * sp) / denom
    return [[2 * g * (2 / 3 + b1 * (1 + sf / 3)) + k * (1 + 2 * b1 * sf),
             (3 * k - 2 * g) / 3 * (1 + 2 * b1 * sf),
             2 * g * (-1 / 3 - b1 * (1 - sf / 3)) + k * (1 + 2 * b1 * sf)],
            [2 * g * (-1 / 3 - b2 * (1 + sf / 3)) + k * (1 - 2 * b2 * sf),
             4 * g / 3 * (1 + b2 * sf) + k * (1 - 2 * b2 * sf),
             2 * g * (-1 / 3 + b2 * (1 - sf / 3)) + k * (1 - 2 * b2 * sf)],
            [2 * g * (-1 / 3 - b3 * (1 + sf / 3)) + k * (1 - 2 * b3 * sf),
             (3 * k - 2 * g) / 3 * (1 - 2 * b3 * sf),
             2 * g * (2 / 3 + b3 * (1 - sf / 3)) + k * (1 - 2 * b3 * sf)]]


def _ctmc_edge(m, right):
    """CTMC, lines 100-176, H = 0: DPSTRS for the right or the left edge."""
    g, k = m.shear_modulus, m.bulk_modulus
    sf, sp = math.sin(m.phi), math.sin(m.psi)
    r2g, r4g, r2k = 2 * g, 4 * g, 2 * k
    r2gd3, r4gd3 = r2g / 3, r4g / 3
    sphsps = sf * sp
    consta = r4g * (1 + sphsps / 3) + 4 * k * sphsps
    if right:
        constb = r2g * (1 + sf + sp - sphsps / 3) + 4 * k * sphsps
    else:
        constb = r2g * (1 - sf - sp - sphsps / 3) + 4 * k * sphsps
    aa, ab, ba, bb = -consta, -constb, -constb, -consta
    aux1 = r2g * (1 + sp / 3) + r2k * sp
    aux2 = (r4gd3 - r2k) * sp
    aux3 = r2g * (1 - sp / 3) - r2k * sp
    r = 1 / (aa * bb - ab * ba)
    s = sf
    if right:
        d_ii = k + r4gd3 + aux1 * (-ab + bb + aa - ba) * (r2g + (r2k + r2gd3) * s) * r
        d_im = k - r2gd3 + aux1 * (r2g * (ab - aa) + ((-ab + bb + aa - ba) * (r2k + r2gd3) + (ba - bb) * r2g) * s) * r
        d_ij = k - r2gd3 + aux1 * (r2g * (ba - bb) + ((-ab + bb + aa - ba) * (r2k + r2gd3) + (ab - aa) * r2g) * s) * r
        d_mi = k - r2gd3 + (aux2 * (ab - bb) + aux3 * (ba - aa)) * (r2g + (r2k + r2gd3) * s) * r
        d_mm = k + r4gd3 + (aux2 * ((r2k * (ab - bb) + (ab * r2gd3 + bb * r4gd3)) * s - ab * r2g)
                            + aux3 * (aa * r2g + (r2k * (ba - aa) - (aa * r2gd3 + ba * r4gd3)) * s)) * r
        d_mj = k - r2gd3 + (aux2 * ((r2k * (ab - bb) - (bb * r2gd3 + ab * r4gd3)) * s + bb * r2g)
                            + aux3 * ((r2k * (ba - aa) + (aa * r4gd3 + ba * r2gd3)) * s - ba * r2g)) * r
        d_ji = k - r2gd3 + ((aux2 * (ba - aa) + aux3 * (ab - bb)) * ((r2k + r2gd3) * s + r2g)) * r
        d_jm = k - r2gd3 + (aux2 * ((r2k * (ba - aa) - (ba * r4gd3 + aa * r2gd3)) * s + aa * r2g)
                            + aux3 * ((r2k * (ab - bb) + (ab * r2gd3 + bb * r4gd3)) * s - ab * r2g)) * r
        d_jj = k + r4gd3 + (aux2 * ((r2k * (ba - aa) + (aa * r4gd3 + ba * r2gd3)) * s - ba * r2g)
                            + aux3 * ((r2k * (ab - bb) - (ab * r4gd3 + bb * r2gd3)) * s + bb * r2g)) * r
    else:
        d_ii = k + r4gd3 + (aux1 * ((r2k * (bb - ab) + (ab * r4gd3 + bb * r2gd3)) * s + bb * r2g)
                            + aux2 * ((r2k * (ba - aa) + (aa * r4gd3 + ba * r2gd3)) * s + ba * r2g)) * r
        d_im = k - r2gd3 + (aux1 * ((r2k * (bb - ab) - (ab * r2gd3 + bb * r4gd3)) * s - ab * r2g)
                            + aux2 * ((r2k * (ba - aa) - (aa * r2gd3 + ba * r4gd3)) * s - aa * r2g)) * r
        d_ij = k - r2gd3 + ((aux1 * (bb - ab) + aux2 * (ba - aa)) * ((r2k + r2gd3) * s - r2g)) * r
        d_mi = k - r2gd3 + (aux1 * ((r2k * (aa - ba) - (aa * r4gd3 + ba * r2gd3)) * s - ba * r2g)
                            + aux2 * ((r2k * (ab - bb) - (ab * r4gd3 + bb * r2gd3)) * s - bb * r2g)) * r
        d_mm = k + r4gd3 + (aux1 * ((r2k * (aa - ba) + (aa * r2gd3 + ba * r4gd3)) * s + aa * r2g)
                            + aux2 * ((r2k * (ab - bb) + (ab * r2gd3 + bb * r4gd3)) * s + ab * r2g)) * r
        d_mj = k - r2gd3 + ((aux1 * (aa - ba) + aux2 * (ab - bb)) * ((r2k + r2gd3) * s - r2g)) * r
        d_ji = k - r2gd3 + (aux3 * ((r2k * (ab - bb - aa + ba) + (aa - ab) * r4gd3 + (ba - bb) * r2gd3) * s
                                    + (ba - bb) * r2g)) * r
        d_jm = k - r2gd3 + (aux3 * ((r2k * (ab - bb - aa + ba) + (ab - aa) * r2gd3 + (bb - ba) * r4gd3) * s
                                    + (ab - aa) * r2g)) * r
        d_jj = k + r4gd3 + (aux3 * (ab - bb - aa + ba) * ((r2k + r2gd3) * s - r2g)) * r
    return [[d_ii, d_im, d_ij], [d_mi, d_mm, d_mj], [d_ji, d_jm, d_jj]]


def _engine_principal(m, region):
    """d sigma_i / d eps_trial_j = P De in the sorted principal order."""
    g, k = m.shear_modulus, m.bulk_modulus
    lam = k - 2 * g / 3
    p = mc.principal_derivatives(m, region)
    de = [[lam + (2 * g if i == j else 0.0) for j in range(3)] for i in range(3)]
    return [[sum(p[i][q] * de[q][j] for q in range(3)) for j in range(3)] for i in range(3)]


class TestAgainstTheSource:
    def test_main_plane_and_edges_match_ctmc(self):
        for m in MATERIALS:
            for region, ref in (("plane", _ctmc_plane(m)),
                                ("right edge", _ctmc_edge(m, True)),
                                ("left edge", _ctmc_edge(m, False))):
                got = _engine_principal(m, region)
                assert _largest_gap(got, ref) < 1e-12 * E, (math.degrees(m.psi), region)

    def test_apex_principal_derivatives_vanish(self):
        assert _engine_principal(MATERIALS[2], "apex") == [[0.0] * 3 for _ in range(3)]
