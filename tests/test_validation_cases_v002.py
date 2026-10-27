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
  and the tangential displacement there is nought to the same measure.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import _sphere

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
