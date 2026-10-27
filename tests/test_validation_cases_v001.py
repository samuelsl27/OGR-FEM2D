# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.1 (spec 001, T9) — every validation case under validacion/casos/ is
run with the mesh its esperado.json fixes and compared with the value and the
tolerance written there (validacion/README.md: the tolerance lives in the
case, not in the test; a failing case is never edited to pass).

Invariants protected:

* **the cases pass**: each comparison within its tolerance, measured where
  the engine computes and at its worst point: u_r at EVERY node on the hole,
  sigma_theta at EVERY integration point on it (the quadratic rule puts one
  at the middle of each hole edge, on the circle). Expected values and their
  sources are in each case (Kirsch 1898 and Salençon 1969, checked in task
  T1);
* **no case is left out quietly**: a case whose mesh is not fixed yet
  (``"malla": null``) cannot be run, and must be one of PENDING, so the state
  of the validation is written here and not hidden behind a skip;
* **the cases are the shape the runner expects**: the conventions are the
  geotechnical ones of the sources (compression positive, u_r inward) and are
  converted in tests/_hole.py, in one place.
"""
from __future__ import annotations

import json
from pathlib import Path

import _hole
from ogr_fem2d.engine.reference.elastic import Elastic

CASES = Path(__file__).resolve().parents[1] / "validacion" / "casos"

#: Cases written but not runnable yet, with the reason (tasks.md, T9).
PENDING = {
    "002-salencon-hueco-mohr-coulomb":
        "the equilibrium iterations of the Mohr-Coulomb cases wait for the "
        "owner's decision (changelog v0.0.1, T7)",
}


def _cases():
    out = {}
    for path in sorted(CASES.glob("*/esperado.json")):
        if path.parent.name.startswith("000-"):
            continue                                    # the template
        out[path.parent.name] = json.loads(path.read_text(encoding="utf-8"))
    return out


def _material(model):
    m = model["material"]
    if m["ley"] == "elastica":
        return Elastic(m["E"], m["nu"])
    raise AssertionError(f"material law {m['ley']!r} not runnable yet")


def _check_geometry_and_field(model):
    # The hole model of tests/_hole.py is the one of spec 001: a = 1 m and a
    # hydrostatic field of 30 MPa. A case that says otherwise is not that.
    assert model["geometria"]["a"] == _hole.A
    assert model["tension_inicial"]["p0"] == _hole.P0


def _run(case):
    model = case["modelo"]
    _check_geometry_and_field(model)
    mesh_spec, stage = model["malla"], model["fase"]
    return _hole.excavate(model["geometria"]["b"], mesh_spec["n_radial"],
                          mesh_spec["n_theta"], mesh_spec["crecimiento"],
                          _material(model), stage["escalones"],
                          stage["tolerancia"], stage["iteraciones_max"])


def _worst(mesh, result, comparison):
    where, value = comparison["donde"], comparison["valor"]
    errors = []
    if comparison["magnitud"] == "u_r" and where["tipo"] == "nudos":
        for n in mesh.hole:
            errors.append(_hole.radial_inward(mesh, result, n) / value - 1.0)
    elif (comparison["magnitud"] == "sigma_theta"
          and where["tipo"] == "puntos_de_integracion"):
        for point, stress in zip(result.points, result.stresses):
            r, _s_r, s_t, _s_z = _hole.polar_compressive(point, stress)
            if abs(r - where["r"]) < 1e-12:
                errors.append(s_t / value - 1.0)
    else:
        raise AssertionError(f"comparison not understood: {comparison}")
    assert where["r"] == _hole.A and errors, comparison
    return max(errors, key=abs)


class TestValidationCases:
    def test_pending_cases_are_exactly_those_without_a_mesh(self):
        cases = _cases()
        assert set(PENDING) <= set(cases)
        for name, case in cases.items():
            assert (case["modelo"]["malla"] is None) == (name in PENDING), name

    def test_001_kirsch(self):
        case = _cases()["001-kirsch-hueco-elastico"]
        mesh, result = _run(case)
        tolerance = case["tolerancia_relativa"]
        for comparison in case["comparaciones"]:
            worst = _worst(mesh, result, comparison)
            assert abs(worst) <= tolerance, (comparison["magnitud"], worst)
