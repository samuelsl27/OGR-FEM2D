# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.11 (spec 005, T1) — the field quantities and the sign of what the
results give (RF-5 to RF-7; D1, D2, D16).

Invariants protected:

* **the invariants do not turn with the axes**: for tensors drawn at random
  and axes turned by random angles (JCZ 2007, Eq. 2.29), sigma_1, sigma_3,
  the three ordered principal stresses, p, J2, q and the differential stress
  are the same; theta_1 turns with the axes;
* **the exact identities**: sigma_1 + sigma_3 = sxx + syy; the sum of the
  squares of JCZ Eq. (2.146); J2 of Eq. (2.163) equals that of the principal
  stresses, Eq. (2.164); a hydrostatic state has q = 0 and no differential
  stress;
* **the branches of the angle** of sigma_1, JCZ Eqs. (2.41)-(2.44), each in
  its quadrant;
* **the order of the three** with sigma_z greatest, intermediate and least
  (D2: sigma_1 can be the intermediate);
* **the user's sign** (D1): a uniaxial compression of the engine (tension
  positive) is a positive sigma_1; a shortening is a positive strain; a
  displacement keeps its sign; and the change of sign lives in
  model/conventions.py only (rule 10);
* **the catalogue** (D16): unique ids and keys, every entry with its
  definition, source, unit and convention, and its name in axisymmetry
  (RF-6); every id computes.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from ogr_fem2d.model import conventions
from ogr_fem2d.results import quantities as qt

ROOT = Path(__file__).resolve().parents[1]
RNG = np.random.default_rng(20261124)
TENSORS = RNG.uniform(-50.0, 50.0, size=(200, 4))
INVARIANT = ("sigma_1", "sigma_3", "sigma_I", "sigma_II", "sigma_III", "p", "q", "sigma_diff")


def _turned(s, angle):
    """The components in axes turned by ``angle`` (radians, anticlockwise),
    JCZ Eqs. (2.25)-(2.27); z does not move."""
    c, n = math.cos(angle), math.sin(angle)
    xx, yy, zz, xy = s[..., 0], s[..., 1], s[..., 2], s[..., 3]
    out = np.empty_like(s)
    out[..., 0] = xx * c * c + 2.0 * xy * n * c + yy * n * n
    out[..., 1] = xx * n * n - 2.0 * xy * n * c + yy * c * c
    out[..., 2] = zz
    out[..., 3] = (yy - xx) * n * c + xy * (c * c - n * n)
    return out


class TestTheInvariants:
    def test_they_do_not_turn_with_the_axes(self):
        for angle in RNG.uniform(-math.pi, math.pi, size=7):
            turned = _turned(TENSORS, angle)
            for q in INVARIANT:
                a, b = qt.stress_quantity(q, TENSORS), qt.stress_quantity(q, turned)
                assert np.allclose(a, b, rtol=0.0, atol=1e-11), (q, angle)

    def test_theta_1_turns_with_the_axes(self):
        angle = 0.3
        a = qt.stress_quantity("theta_1", TENSORS)
        b = qt.stress_quantity("theta_1", _turned(TENSORS, angle))
        diff = np.mod(a - b - math.degrees(angle) + 90.0, 180.0) - 90.0
        assert np.allclose(diff, 0.0, atol=1e-9)

    def test_the_exact_identities(self):
        s = TENSORS
        s1, s3 = qt.stress_quantity("sigma_1", s), qt.stress_quantity("sigma_3", s)
        assert np.allclose(s1 + s3, s[:, 0] + s[:, 1], rtol=0.0, atol=1e-12)
        # JCZ Eq. (2.146)
        left = s[:, 0] ** 2 + s[:, 1] ** 2 + s[:, 2] ** 2 + 2.0 * s[:, 3] ** 2
        assert np.allclose(left, s1 ** 2 + s3 ** 2 + s[:, 2] ** 2, rtol=1e-12)
        # J2 of Eq. (2.163) is that of the principal stresses, Eq. (2.164)
        a, b, c = qt.principal_3d(s)
        assert np.allclose(qt.j2(s), ((a - b) ** 2 + (b - c) ** 2 + (c - a) ** 2) / 6.0, rtol=1e-12)
        assert np.all(s1 >= s3)

    def test_a_hydrostatic_state(self):
        s = np.array([[7.0, 7.0, 7.0, 0.0], [-3.0, -3.0, -3.0, 0.0]])
        assert np.all(qt.stress_quantity("q", s) == 0.0)
        assert np.all(qt.stress_quantity("sigma_diff", s) == 0.0)
        assert np.all(qt.stress_quantity("p", s) == s[:, 0])

    def test_the_mean_counts_sigma_z(self):
        """JCZ Eq. (2.153): the three normal stresses, sigma_z included."""
        assert float(qt.stress_quantity("p", np.array([3.0, 6.0, 9.0, 5.0]))) == 6.0

    def test_von_mises_of_a_uniaxial_stress_is_the_stress(self):
        """q = sqrt(3 J2) is the uniaxial stress itself (dSN 2008, Eqs.
        6.108-6.111)."""
        assert math.isclose(float(qt.stress_quantity("q", np.array([12.0, 0.0, 0.0, 0.0]))), 12.0)


class TestTheAngle:
    def test_the_four_branches(self):
        cases = {(4.0, 2.0, 1.0): (0.0, 45.0), (2.0, 4.0, 1.0): (45.0, 90.0),
                 (2.0, 4.0, -1.0): (90.0, 135.0), (4.0, 2.0, -1.0): (135.0, 180.0)}
        for (xx, yy, xy), (low, high) in cases.items():
            theta = float(qt.stress_quantity("theta_1", np.array([xx, yy, 0.0, xy])))
            assert low < theta < high, (xx, yy, xy, theta)

    def test_the_normal_stress_there_is_sigma_1(self):
        """JCZ Eq. (2.31) at theta_1 is sigma_1."""
        theta = np.radians(qt.stress_quantity("theta_1", TENSORS))
        xx, yy, xy = TENSORS[:, 0], TENSORS[:, 1], TENSORS[:, 3]
        normal = 0.5 * (xx + yy) + 0.5 * (xx - yy) * np.cos(2 * theta) + xy * np.sin(2 * theta)
        assert np.allclose(normal, qt.stress_quantity("sigma_1", TENSORS), rtol=0.0, atol=1e-11)


class TestTheOrder:
    def test_sigma_z_anywhere(self):
        for sz, want in ((20.0, (20.0, 10.0, 2.0)), (5.0, (10.0, 5.0, 2.0)), (-1.0, (10.0, 2.0, -1.0))):
            s = np.array([10.0, 2.0, sz, 0.0])
            got = tuple(float(qt.stress_quantity(q, s)) for q in ("sigma_I", "sigma_II", "sigma_III"))
            assert got == want, (sz, got)
            assert float(qt.stress_quantity("sigma_diff", s)) == want[0] - want[2]
        # sigma_1 in the plane stays the in-plane one when sigma_z is greater
        assert float(qt.stress_quantity("sigma_1", np.array([10.0, 2.0, 20.0, 0.0]))) == 10.0


class TestTheSign:
    def test_a_compression_of_the_engine_is_positive(self):
        engine = np.array([0.0, -10.0, 0.0, 0.0])         # tension positive: compression in y
        s = conventions.user_stress(engine)
        assert float(qt.stress_quantity("sigma_1", s)) == 10.0
        assert float(qt.stress_quantity("theta_1", s)) == 90.0

    def test_a_shortening_is_positive_and_a_displacement_keeps_its_sign(self):
        e = conventions.user_strain(np.array([-1e-3, 0.0, 0.0]))
        assert float(qt.strain_quantity("eps_xx", qt.strain4(e, "plane_strain"))) == 1e-3
        u = conventions.user_displacement(np.array([0.5, -0.25]))
        assert list(u) == [0.5, -0.25]

    def test_the_sign_changes_in_one_place(self):
        """Rule 10: no module of ogr_fem2d/results changes a sign of the
        engine's; they all go through model/conventions.py."""
        for path in (ROOT / "ogr_fem2d" / "results").glob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert "def user_" not in text, path.name
            assert "-outcome" not in text and "-np.asarray" not in text, path.name


class TestTheCatalogue:
    def test_every_entry_is_complete(self):
        ids = [q.id for q in qt.CATALOGUE]
        assert len(ids) == len(set(ids)) and len({q.key for q in qt.CATALOGUE}) == len(ids)
        for q in qt.CATALOGUE:
            assert q.kind in (qt.STRESS, qt.STRAIN, qt.DISPLACEMENT), q.id
            assert q.unit in (qt.PRESSURE, qt.LENGTH, qt.DIMENSIONLESS, qt.ANGLE), q.id
            assert q.definition and q.source and q.convention and q.label and q.label_axi, q.id

    def test_the_names_in_axisymmetry(self):
        assert "circumferential" in qt.get("sigma_z").name("axisymmetric")
        assert "radial" in qt.get("sigma_xx").name("axisymmetric").lower()
        assert qt.get("sigma_z").name("plane_strain") != qt.get("sigma_z").name("axisymmetric")

    def test_every_id_computes(self):
        s, e, u = TENSORS[:3], qt.strain4(TENSORS[:3, :3], "plane_strain"), TENSORS[:3, :2]
        for q in qt.CATALOGUE:
            tensor = {qt.STRESS: s, qt.STRAIN: e, qt.DISPLACEMENT: u}[q.kind]
            assert qt.of(q.id, tensor).shape == (3,), q.id

    def test_an_unknown_id_is_named(self):
        try:
            qt.get("sigma_9")
        except KeyError as err:
            assert "sigma_9" in str(err)
        else:
            raise AssertionError("no error")
