# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.2 (spec 002, T11) — the validation cases of spec 002, run with the
mesh and compared with the value and tolerance their esperado.json fixes
(validacion/README.md: the tolerance lives in the case; a failing case is
never edited to pass).

Invariants protected:

* **case 003, the spherical cavity** (Lamé 1852, in Timoshenko and Goodier
  1951, §121): sigma_t within 0.5 % at EVERY integration point of the first
  ring of elements, both tangential components (meridian and hoop), each
  against the closed form at its own radius; u_R within 0.5 % at EVERY node
  of the cavity;
* **the case is the model it says**: its radius, field and material are
  those of the closed forms checked in the spec's comprobaciones;
* **the finite sphere** (identity, spec 002 «Validación»): against the
  exact solution of the model itself, with the outer sphere fixed at 21 m
  (sphere_fixed_outer), the error is only discretization, and it falls by
  more than three times in sigma_t and in u_R from the 2 x 8 to the 4 x 16
  mesh of the case's family;
* **spherical symmetry**: in the case, the radial displacement is the same
  at every node of the cavity, whatever its angle, to the case's tolerance,
  and the tangential displacement there is nought to the same measure;
* **case 004, the strip load** (J. H. Michell 1902, in Timoshenko and Goodier
  1951, §34): sigma_1 and sigma_3 within 0.01 q at EVERY integration point
  of the first column of elements with 0.25 <= z <= 5 m, each against
  Michell at its own (x, z), on the domain and mesh the case fixes;
* **Michell in components** (tests/_strip.py, from the principal stresses
  and the bisector): the same as superposing Flamant's point force over the
  strip (T&G §33, Eq. 66), to rounding, at points on both sides of the
  axis and far away;
* **the truncated half-space** (identity): with Michell's own tractions on
  its far sides the model has the infinite solution, and the error, only
  discretization, falls by more than three times from h0 = 0.5 to 0.25 m;
* **the domain of the ficha is not enough** (the finding of T12): with the
  supported boundary at 25 m, sigma_3 misses the tolerance, and the error
  falls as the domain grows (25, 50, 100 m), as it should if it is the
  boundary's.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import _sphere
import _strip

CASES = Path(__file__).resolve().parents[1] / "validacion" / "casos"


def case(name):
    return json.loads((CASES / name / "esperado.json").read_text(encoding="utf-8"))


def run_003():
    c = case("003-cavidad-esferica-elastica")
    mesh, stage = c["modelo"]["malla"], c["modelo"]["fase"]
    return c, _sphere.excavate(c["modelo"]["geometria"]["b"], mesh["n_radial"],
                               mesh["n_theta"], mesh["crecimiento"],
                               6 if mesh["elemento"] == "T6" else 3,
                               steps=stage["escalones"], tolerance=stage["tolerancia"],
                               max_iterations=stage["iteraciones_max"])


class TestCase003:

    def test_the_case_is_the_model_it_says(self):
        c = case("003-cavidad-esferica-elastica")
        model = c["modelo"]
        assert model["geometria"]["a"] == _sphere.A
        assert model["tension_inicial"]["p0"] == _sphere.P0
        assert (model["material"]["E"], model["material"]["nu"]) == (_sphere.E, _sphere.NU)
        assert model["analisis"] == "axisimetria"
        u = next(x for x in c["comparaciones"] if x["magnitud"] == "u_R")
        assert abs(u["valor"] - _sphere.closed.sphere_infinite(_sphere.A)[2]) < 1e-15

    def test_003_lame_sphere(self):
        c, (mesh, model, outcome) = run_003()
        sigma_t, u = _sphere.worst_errors(mesh, model, outcome, _sphere.closed.sphere_infinite)
        tolerance = c["tolerancia_relativa"]
        assert sigma_t <= tolerance and u <= tolerance, (sigma_t, u)
        # spherical symmetry on the cavity
        values = [_sphere.radial_inward(mesh, outcome, n) for n in mesh.hole]
        assert max(values) - min(values) <= tolerance * max(values)
        for n in mesh.hole:
            x, y = mesh.nodes[n]
            tangential = (-outcome.displacement[2 * n] * y
                          + outcome.displacement[2 * n + 1] * x) / math.hypot(x, y)
            assert abs(tangential) <= tolerance * max(values), n


class TestFiniteSphere:

    def test_the_discretization_error_falls(self):
        b = case("003-cavidad-esferica-elastica")["modelo"]["geometria"]["b"]
        exact = lambda r: _sphere.closed.sphere_fixed_outer(r, b)
        errors = []
        for n_theta, n_radial, growth in ((2, 8, 1.69), (4, 16, 1.3)):
            mesh, model, outcome = _sphere.excavate(b, n_radial, n_theta, growth)
            errors.append(_sphere.worst_errors(mesh, model, outcome, exact))
        (s1, u1), (s2, u2) = errors
        assert s1 / s2 > 3.0 and u1 / u2 > 3.0, errors


def run_004():
    c = case("004-carga-en-faja-elastica")
    geometry, mesh = c["modelo"]["geometria"], c["modelo"]["malla"]
    return c, _strip.solve(geometry["W"], geometry["D"], mesh["h0"], mesh["crecimiento"],
                           6 if mesh["elemento"] == "T6" else 3)


class TestCase004:

    def test_the_case_is_the_model_it_says(self):
        c = case("004-carga-en-faja-elastica")
        model = c["modelo"]
        assert model["carga"]["q"] == _strip.Q and model["geometria"]["b"] == _strip.B
        assert (model["material"]["E"], model["material"]["nu"]) == (_strip.E, _strip.NU)
        assert model["analisis"] == "deformacion_plana"

    def test_004_michell_strip(self):
        c, (mesh, model, outcome) = run_004()
        e1, e3 = _strip.worst_errors(mesh, model, outcome)
        tolerance = c["tolerancia_absoluta"]
        assert e1 <= tolerance and e3 <= tolerance, (e1, e3)

    def test_michell_in_components_is_flamant_superposed(self):
        for x, z in ((0.0, 0.5), (0.7, 0.4), (2.5, 1.5), (-1.3, 3.0), (1.0, 0.01), (15.0, 20.0)):
            got = _strip.michell_components(x, z)
            want = _strip.closed.strip_by_flamant(x, z)
            assert max(abs(a - b) for a, b in zip(got, want)) < 1e-14, (x, z, got, want)


class TestTruncatedHalfSpace:

    def test_the_discretization_error_falls(self):
        errors = []
        for h0, growth in ((0.5, 1.5), (0.25, 1.5 ** 0.5)):
            mesh, model, outcome = _strip.solve(25.0, 25.0, h0, growth, 6, "exact")
            errors.append(_strip.worst_errors(mesh, model, outcome))
        (a1, a3), (b1, b3) = errors
        assert a1 / b1 > 3.0 and a3 / b3 > 3.0, errors

    def test_the_domain_of_the_ficha_is_not_enough(self):
        tolerance = case("004-carga-en-faja-elastica")["tolerancia_absoluta"]
        sigma_3 = []
        for size in (25.0, 50.0, 100.0):
            mesh, model, outcome = _strip.solve(size, size, 0.25, 1.5 ** 0.5)
            sigma_3.append(_strip.worst_errors(mesh, model, outcome)[1])
        assert sigma_3[0] > 3 * tolerance, sigma_3
        assert sigma_3[0] > sigma_3[1] > sigma_3[2], sigma_3
