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
  (``"malla": null``, in the model or in a variant) cannot be run, and must be
  one of PENDING, so the state of the validation is written here and not
  hidden behind a skip;
* **the plastic radius** of case 002: the farthest plastic integration point
  within one element (the radial size of the element that contains R0) of R0,
  as D3 says;
* **the regions of the return** in case 002 (spec 001, D8): the plastic
  points with r < r_e on the edge sigma_z = sigma_theta, those beyond on the
  main plane with sigma_z strictly between the in-plane principal stresses,
  outside one element on each side of r_e. This replaces the check the spec
  asked for (sigma_z intermediate at every plastic point), which the model,
  rightly, does not satisfy;
* **the cases are the shape the runner expects**: the conventions are the
  geotechnical ones of the sources (compression positive, u_r inward) and are
  converted in tests/_hole.py, in one place.
"""
from __future__ import annotations

import json
from pathlib import Path

import math

import _hole
from ogr_fem2d.engine.reference import mohr_coulomb as mc
from ogr_fem2d.engine.reference import solver
from ogr_fem2d.engine.reference.elastic import Elastic

CASES = Path(__file__).resolve().parents[1] / "validacion" / "casos"

#: Cases written but not runnable yet, with the reason (tasks.md, T9).
PENDING: dict[str, str] = {}


def _cases():
    out = {}
    for path in sorted(CASES.glob("*/esperado.json")):
        if path.parent.name.startswith("000-"):
            continue                                    # the template
        out[path.parent.name] = json.loads(path.read_text(encoding="utf-8"))
    return out


def _material(model, variant=None):
    m = model["material"]
    if m["ley"] == "elastica":
        return Elastic(m["E"], m["nu"])
    if m["ley"] == "mohr_coulomb":
        return mc.MohrCoulomb(m["E"], m["nu"], m["c"], math.radians(m["phi"]),
                              math.radians(variant["psi"]))
    raise AssertionError(f"material law {m['ley']!r} not runnable yet")


def _meshes(case):
    """The mesh of the model, or of each variant."""
    if "variantes" in case:
        return [v.get("malla") for v in case["variantes"]]
    return [case["modelo"]["malla"]]


def _check_geometry_and_field(model):
    # The hole model of tests/_hole.py is the one of spec 001: a = 1 m and a
    # hydrostatic field of 30 MPa. A case that says otherwise is not that.
    assert model["geometria"]["a"] == _hole.A
    assert model["tension_inicial"]["p0"] == _hole.P0


def _run(case, variant=None, engine=solver.REFERENCE):
    model = case["modelo"]
    _check_geometry_and_field(model)
    mesh_spec = variant["malla"] if variant else model["malla"]
    stage = model["fase"]
    return _hole.excavate(model["geometria"]["b"], mesh_spec["n_radial"],
                          mesh_spec["n_theta"], mesh_spec["crecimiento"],
                          _material(model, variant), stage["escalones"],
                          stage["tolerancia"], stage["iteraciones_max"],
                          stage.get("particiones_max", 0), engine)


def _element_size_at(mesh, r):
    return next(r2 - r1 for r1, r2 in zip(mesh.radii, mesh.radii[1:])
                if r1 <= r <= r2)


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
            pending = any(m is None for m in _meshes(case))
            assert pending == (name in PENDING), name

    def test_001_kirsch(self):
        check_001(solver.REFERENCE)

    def test_002_salencon_with_the_edge_zone(self):
        check_002(solver.REFERENCE)


def check_001(engine):
    """Case 001 with the engine variant ``engine`` (interface.py)."""
    case = _cases()["001-kirsch-hueco-elastico"]
    mesh, result = _run(case, engine=engine)
    tolerance = case["tolerancia_relativa"]
    for comparison in case["comparaciones"]:
        worst = _worst(mesh, result, comparison)
        assert abs(worst) <= tolerance, (comparison["magnitud"], worst)


def check_002(engine):
    """Case 002, both dilatancies, with the engine variant ``engine``."""
    case = _cases()["002-salencon-hueco-mohr-coulomb"]
    tolerance = case["tolerancia_relativa"]
    r_e = case["comprobaciones"][0]["r_e"]
    for variant in case["variantes"]:
        mesh, result = _run(case, variant, engine)
        for comparison in variant["comparaciones"]:
            if comparison["magnitud"] == "R0":
                farthest = max(math.hypot(*p.xy) for p, plastic in
                               zip(result.points, result.plastic) if plastic)
                size = _element_size_at(mesh, comparison["valor"])
                assert abs(farthest - comparison["valor"]) <= size, (
                    variant["psi"], farthest, size)
                continue
            worst = _worst(mesh, result, comparison)
            assert abs(worst) <= tolerance, (variant["psi"], worst)
        size = _element_size_at(mesh, r_e)
        on_edge = on_plane = 0
        for point, stress, plastic in zip(result.points, result.stresses,
                                          result.plastic):
            if not plastic:
                continue
            r = math.hypot(*point.xy)
            hi, lo, _ = mc.principal_in_plane(stress[0], stress[1], stress[3])
            if r < r_e - size:
                assert min(abs(stress[2] - hi), abs(stress[2] - lo)) < 1e-8 * _hole.P0
                on_edge += 1
            elif r > r_e + size:
                assert lo + 1e-6 < stress[2] < hi - 1e-6, (variant["psi"], r)
                on_plane += 1
        assert on_edge > 0 and on_plane > 0, (variant["psi"], on_edge, on_plane)
