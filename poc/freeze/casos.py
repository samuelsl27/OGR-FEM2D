# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The program that is frozen with PyInstaller (spec 001, RF-10, task T15;
ADR-0001, criterion 3): it solves the validation cases with the Rust
variant of the engine and compares them with their esperado.json, exactly
as tests/test_validation_cases_v001.py and _v002.py do. Cases 001 and 002
since spec 001; 003 and 004 since spec 002, task T14.

    python poc/freeze/casos.py          # from the source tree
    dist/ogr-fem2d-casos/ogr-fem2d-casos.exe   # frozen (poc/freeze/build.py)

Exit code 0 only when every case is within its tolerances; it prints
every comparison. The esperado.json files travel inside the frozen program
(they are read from sys._MEIPASS there).

The model is the one of spec 001 (tests/_hole.py): the quarter annulus of
mesh_radial with the mesh the case fixes, rollers on the axes, the outer
boundary fixed, a hydrostatic field of 30 MPa of compression and a stage
whose total load is zero. Compression positive and u_r inward in the
comparisons, as in the cases.

Cases 003 and 004 are built and compared by the same code as their tests,
tests/_sphere.py and tests/_strip.py (the strip's mesh is defined there),
which go inside the program with the closed forms they compare against
(spec/features/002-motor-elastico/comprobaciones/soluciones_cerradas.py):
here that file is loaded first, from the tree or from inside the program,
under the name the two modules look for.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if not getattr(sys, "frozen", False):                 # from the source tree
    sys.path[:0] = [str(_ROOT), str(_ROOT / "tests")]


def _load_closed_forms() -> None:
    import importlib.util
    frozen = getattr(sys, "_MEIPASS", None)
    where = (Path(frozen) / "comprobaciones_002" if frozen else
             _ROOT / "spec" / "features" / "002-motor-elastico" / "comprobaciones")
    spec = importlib.util.spec_from_file_location("soluciones_cerradas_002",
                                                  where / "soluciones_cerradas.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


_load_closed_forms()

import _sphere  # noqa: E402
import _strip  # noqa: E402
from ogr_fem2d.engine.compiled import RUST  # noqa: E402
from ogr_fem2d.engine.mesh_radial import quarter_annulus  # noqa: E402
from ogr_fem2d.engine.reference import mohr_coulomb as mc  # noqa: E402
from ogr_fem2d.engine.reference import solver  # noqa: E402
from ogr_fem2d.engine.reference.elastic import Elastic  # noqa: E402

CASES = ("001-kirsch-hueco-elastico", "002-salencon-hueco-mohr-coulomb",
         "003-cavidad-esferica-elastica", "004-carga-en-faja-elastica")


def _cases_dir() -> Path:
    frozen = getattr(sys, "_MEIPASS", None)
    if frozen:
        return Path(frozen) / "casos"
    return Path(__file__).resolve().parents[2] / "validacion" / "casos"


def _excavate(model_spec: dict, mesh_spec: dict, material):
    geometry, stage = model_spec["geometria"], model_spec["fase"]
    p0 = model_spec["tension_inicial"]["p0"]
    mesh = quarter_annulus(geometry["a"], geometry["b"], mesh_spec["n_radial"],
                           mesh_spec["n_theta"], mesh_spec["crecimiento"])
    restrained = {2 * n + 1 for n in mesh.x_axis} | {2 * n for n in mesh.y_axis}
    for n in mesh.outer:
        restrained |= {2 * n, 2 * n + 1}
    model = solver.Model(mesh.nodes, mesh.elements, [material] * len(mesh.elements),
                         frozenset(restrained))
    result = solver.solve_stage(model, [(-p0, -p0, -p0, 0.0)] * (3 * len(mesh.elements)),
                                [0.0] * (2 * len(mesh.nodes)), stage["escalones"],
                                stage["tolerancia"], stage["iteraciones_max"],
                                stage.get("particiones_max", 0), RUST)
    return mesh, result


def _u_r(mesh, result, n):
    x, y = mesh.nodes[n]
    return -(result.displacement[2 * n] * x + result.displacement[2 * n + 1] * y) / math.hypot(x, y)


def _sigma_theta(point, stress):
    x, y = point.xy
    r = math.hypot(x, y)
    c, s = x / r, y / r
    return r, -(stress[0] * s * s + stress[1] * c * c - 2.0 * stress[3] * s * c)


def _worst(mesh, result, comparison):
    value, a = comparison["valor"], comparison["donde"]["r"]
    if comparison["magnitud"] == "u_r":
        errors = [_u_r(mesh, result, n) / value - 1.0 for n in mesh.hole]
    else:
        errors = [s_t / value - 1.0 for r, s_t in
                  (_sigma_theta(p, s) for p, s in zip(result.points, result.stresses))
                  if abs(r - a) < 1e-12]
    return max(errors, key=abs)


def _size_at(mesh, r):
    return next(r2 - r1 for r1, r2 in zip(mesh.radii, mesh.radii[1:]) if r1 <= r <= r2)


def case_001(case) -> list[str]:
    m = case["modelo"]["material"]
    mesh, result = _excavate(case["modelo"], case["modelo"]["malla"], Elastic(m["E"], m["nu"]))
    failures = []
    for comparison in case["comparaciones"]:
        worst = _worst(mesh, result, comparison)
        ok = abs(worst) <= case["tolerancia_relativa"]
        print(f"  {comparison['magnitud']:12s} worst error {worst * 100:+.3f} %  "
              f"(tolerance {case['tolerancia_relativa'] * 100:.1f} %)  {'ok' if ok else 'FAILS'}")
        if not ok:
            failures.append(comparison["magnitud"])
    return failures


def case_002(case) -> list[str]:
    m = case["modelo"]["material"]
    r_e = case["comprobaciones"][0]["r_e"]
    failures = []
    for variant in case["variantes"]:
        material = mc.MohrCoulomb(m["E"], m["nu"], m["c"], math.radians(m["phi"]),
                                  math.radians(variant["psi"]))
        mesh, result = _excavate(case["modelo"], variant["malla"], material)
        label = f"psi = {variant['psi']:.0f}"
        for comparison in variant["comparaciones"]:
            if comparison["magnitud"] == "R0":
                farthest = max(math.hypot(*p.xy) for p, plastic
                               in zip(result.points, result.plastic) if plastic)
                size = _size_at(mesh, comparison["valor"])
                ok = abs(farthest - comparison["valor"]) <= size
                print(f"  {label}: R0 {farthest:.4f} m vs {comparison['valor']:.4f} m "
                      f"(within one element, {size:.3f} m)  {'ok' if ok else 'FAILS'}")
            else:
                worst = _worst(mesh, result, comparison)
                ok = abs(worst) <= case["tolerancia_relativa"]
                print(f"  {label}: u_r(a) worst error {worst * 100:+.3f} %  (tolerance "
                      f"{case['tolerancia_relativa'] * 100:.1f} %)  {'ok' if ok else 'FAILS'}")
            if not ok:
                failures.append(f"{label} {comparison['magnitud']}")
        # the regions of the return (spec 001, D8)
        size = _size_at(mesh, r_e)
        wrong = 0
        for point, stress, plastic in zip(result.points, result.stresses, result.plastic):
            if not plastic:
                continue
            r = math.hypot(*point.xy)
            hi, lo, _ = mc.principal_in_plane(stress[0], stress[1], stress[3])
            if r < r_e - size:
                wrong += min(abs(stress[2] - hi), abs(stress[2] - lo)) >= 1e-8 * 30.0
            elif r > r_e + size:
                wrong += not (lo + 1e-6 < stress[2] < hi - 1e-6)
        print(f"  {label}: regions of the return (edge inside r_e = {r_e:.4f} m, plane "
              f"outside)  {'ok' if not wrong else f'FAILS at {wrong} points'}")
        if wrong:
            failures.append(f"{label} regions")
    return failures


def _element(mesh_spec: dict) -> int:
    return 6 if mesh_spec["elemento"] == "T6" else 3


def _report(errors: dict, tolerance: float, unit: str) -> list[str]:
    failures = []
    for name, error in errors.items():
        ok = error <= tolerance
        shown = (f"{error * 100:.3f} %  (tolerance {tolerance * 100:.1f} %)" if unit == "%"
                 else f"{error:.4f} q  (tolerance {tolerance} q)")
        print(f"  {name:12s} worst error {shown}  {'ok' if ok else 'FAILS'}")
        if not ok:
            failures.append(name)
    return failures


def case_003(case) -> list[str]:
    """The spherical cavity, axisymmetric (test_validation_cases_v002.py,
    test_003_lame_sphere)."""
    model, mesh_spec, stage = case["modelo"], case["modelo"]["malla"], case["modelo"]["fase"]
    mesh, engine_model, outcome = _sphere.excavate(
        model["geometria"]["b"], mesh_spec["n_radial"], mesh_spec["n_theta"],
        mesh_spec["crecimiento"], _element(mesh_spec), variant=RUST,
        steps=stage["escalones"], tolerance=stage["tolerancia"],
        max_iterations=stage["iteraciones_max"])
    errors = _sphere.worst_errors(mesh, engine_model, outcome, _sphere.closed.sphere_infinite)
    return _report(dict(zip(("sigma_t", "u_R"), errors)), case["tolerancia_relativa"], "%")


def case_004(case) -> list[str]:
    """The strip load, plane strain (test_validation_cases_v002.py,
    test_004_michell_strip)."""
    geometry, mesh_spec = case["modelo"]["geometria"], case["modelo"]["malla"]
    mesh, engine_model, outcome = _strip.solve(
        geometry["W"], geometry["D"], mesh_spec["h0"], mesh_spec["crecimiento"],
        _element(mesh_spec), variant=RUST)
    errors = _strip.worst_errors(mesh, engine_model, outcome)
    return _report(dict(zip(("sigma_1", "sigma_3"), errors)), case["tolerancia_absoluta"], "q")


def main() -> int:
    import ogr_fem2d
    from ogr_fem2d import _engine
    frozen = getattr(sys, "frozen", False)
    print(f"OGR FEM2D {ogr_fem2d.__version__}, {'frozen' if frozen else 'from source'}; "
          f"Python {sys.version.split()[0]}")
    print(f"engine: {Path(_engine.__file__).resolve()}")
    failures = []
    for name, check in zip(CASES, (case_001, case_002, case_003, case_004)):
        case = json.loads((_cases_dir() / name / "esperado.json").read_text(encoding="utf-8"))
        print(f"{name} ({case['ficha']})")
        t = time.perf_counter()
        failures += [f"{name}: {f}" for f in check(case)]
        print(f"  solved in {time.perf_counter() - t:.1f} s")
    print(f"ALL {len(CASES)} CASES PASS" if not failures
          else "FAILURES: " + "; ".join(failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
