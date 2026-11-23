# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.9 (spec 004, T4) — the initial state from the model: the change of
sign in one place, the field stress and the four modes of initial loading
(RF-7, RF-8, D6, D11, D14).

Invariants protected:

* **one change of sign** (spec 001, D1; rule 10): a field of compression
  reaches the engine negative, component by component, rotated as JCZ
  (2007) Eqs. 2.28-2.30 say; a normal load is the engine's normal with its
  sign changed;
* **the gravitational field is in equilibrium with its own weight**
  (identity; JCZ 2007, Eqs. 13.1 and 13.5): two horizontal strata under a
  horizontal surface, the sides on rollers and the base fixed, the mode
  "field stress and body force" in both, give no displacement, to rounding,
  and the stresses stay the field's;
* **every mode moves the number** (rule 7): the four modes give four
  different states (displacements or stresses), and each is what D11 says:
  without the field no point starts with stress (the engine gets None),
  without the self weight the material weighs nothing;
* **in axisymmetry the field must be in radial equilibrium** (T&G 1951,
  Eq. 177; spec 002, D3 amendment): K != Kz, or sigma_r != sigma_theta, is
  an error of the model, rule ``field``, with the reason.
"""
from __future__ import annotations

import math
from dataclasses import replace

import _models
from ogr_fem2d.engine import analysis
from ogr_fem2d.engine.initial_stress import Stratum
from ogr_fem2d.model import conventions, field, translate
from ogr_fem2d.model import model as md

L = _models.meshed(_models.layers())


def _with_mode(m, mode):
    return replace(m, materials=tuple(replace(x, initial_loading=mode) for x in m.materials))


def _run(m):
    e = translate.to_engine(m)
    return e, analysis.run(e)[0]


class TestTheSign:
    def test_a_compressive_field_reaches_the_engine_negative(self):
        m = _models.meshed(_models.tunnel())
        m = replace(m, field=md.ConstantField(30.0, 10.0, 20.0, 30.0))
        e = translate.to_engine(m)
        sxx, syy, szz, txy = e.initial_stresses[0]
        c, s = math.cos(math.radians(30.0)), math.sin(math.radians(30.0))
        assert abs(sxx + (30.0 * c * c + 10.0 * s * s)) < 1e-12
        assert abs(syy + (30.0 * s * s + 10.0 * c * c)) < 1e-12
        assert abs(szz + 20.0) < 1e-12 and abs(txy + 20.0 * s * c) < 1e-12

    def test_a_normal_push_is_the_engines_pull_with_its_sign_changed(self):
        assert conventions.engine_normal(100.0) == -100.0
        assert conventions.engine_normal(-2.5) == 2.5


class TestGravity:
    def test_the_gravitational_field_with_its_weight_does_not_move(self):
        e, out = _run(L)
        biggest = max(abs(u) for u in out.displacement)
        # the scale of a displacement here: 240 kPa over 10 m on E = 3e4 kPa
        assert biggest < 1e-10 * 240.0 * 10.0 / 3.0e4, biggest
        for got, start in zip(out.stresses, e.initial_stresses):
            assert all(abs(a - b) <= 1e-9 * 240.0 for a, b in zip(got, start))

    def test_the_field_at_a_point_is_the_column_above_it(self):
        """sigma_v the column above the point; K that of the stratum of the
        point's element, also at the points on the contact (found in T4)."""
        e = translate.to_engine(L)
        from ogr_fem2d.engine import initial_stress as ini
        points = ini.integration_point_coordinates(e)
        per = len(points) // len(e.elements)
        on_contact = 0
        for k, element in enumerate(e.elements):
            below = sum(e.nodes[n][1] for n in element[:3]) / 3.0 < -4.0
            for (x, y), s in zip(points[k * per:(k + 1) * per],
                                 e.initial_stresses[k * per:(k + 1) * per]):
                sv = 18.0 * -y if y >= -4.0 else 18.0 * 4.0 + 24.0 * (-4.0 - y)
                kk, kz = (0.5, 0.45) if below else (0.6, 0.7)
                assert abs(s[1] + sv) < 1e-9 and abs(s[0] + kk * sv) < 1e-9 and s[3] == 0.0
                assert abs(s[2] + kz * sv) < 1e-9
                on_contact += y == -4.0 and below
        assert on_contact > 0, "no point of an element below the contact lies on it"


class TestTheModes:
    def test_four_modes_four_states(self):
        states = {}
        for mode in md.INITIAL_LOADINGS:
            e, out = _run(_with_mode(L, mode))
            states[mode] = (tuple(round(u, 12) for u in out.displacement),
                            tuple(tuple(round(v, 9) for v in s) for s in out.stresses))
        values = list(states.values())
        assert len(set(values)) == 4, "two modes gave the same state"

    def test_each_mode_is_what_it_says(self):
        for mode, has_field, has_weight in ((md.FIELD_STRESS, True, False),
                                            (md.FIELD_AND_BODY, True, True),
                                            (md.BODY_FORCE, False, True),
                                            (md.NO_LOADING, False, False)):
            e = translate.to_engine(_with_mode(L, mode))
            assert (e.initial_stresses is not None) == has_field, mode
            assert all((mat.unit_weight > 0.0) == has_weight for mat in e.materials), mode

    def test_the_unit_weight_of_a_material(self):
        mat = md.Material("m", unit_weight=19.0)
        assert field.unit_weight(replace(mat, initial_loading=md.FIELD_AND_BODY)) == 19.0
        assert field.unit_weight(replace(mat, initial_loading=md.FIELD_STRESS)) == 0.0

    def test_no_stress_anywhere_is_none(self):
        m = replace(_models.meshed(_models.strip()), field=md.ConstantField())
        assert translate.to_engine(m).initial_stresses is None


def _axisymmetric(f):
    ext = md.Boundary("ext", md.EXTERNAL, ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)), True)
    m = md.Model(analysis=md.AXISYMMETRIC, boundaries=(ext,),
                 materials=(md.Material("m", "", 1.0e4, 0.25, 20.0, md.FIELD_STRESS),),
                 assignments=(md.Assignment((5.0, 5.0), "m", (False,)),), field=f,
                 mesh_settings=_models.g.MeshSettings(boundary_nodes=16))
    return _models.meshed(m)


class TestAxisymmetry:
    def test_a_field_out_of_radial_equilibrium_is_an_error(self):
        for f in (md.ConstantField(10.0, 5.0, 5.0, 0.0),
                  md.GravityField(10.0, (Stratum(-1.0, 20.0, 0.5, 0.6),))):
            try:
                translate.to_engine(_axisymmetric(f))
            except md.ModelError as err:
                assert err.problems[0].rule == "field" and "radial" in err.problems[0].message
            else:
                raise AssertionError(f"{f} was accepted in axisymmetry")

    def test_one_in_equilibrium_is_accepted(self):
        for f in (md.ConstantField(10.0, 10.0, 10.0, 0.0),
                  md.GravityField(10.0, (Stratum(-1.0, 20.0, 0.5, 0.5),))):
            assert translate.to_engine(_axisymmetric(f)).initial_stresses is not None
