# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The program that is frozen with PyInstaller (spec 001, RF-10, task T15;
ADR-0001, criterion 3): it solves the two validation cases with the Rust
variant of the engine and compares them with their esperado.json, exactly
as tests/test_validation_cases_v001.py does.

    python poc/freeze/casos.py          # from the source tree
    dist/ogr-fem2d-casos/ogr-fem2d-casos.exe   # frozen (poc/freeze/build.py)

Exit code 0 only when both cases are within their tolerances; it prints
every comparison. The esperado.json files travel inside the frozen program
(they are read from sys._MEIPASS there).

The model is the one of spec 001 (tests/_hole.py): the quarter annulus of
mesh_radial with the mesh the case fixes, rollers on the axes, the outer
boundary fixed, a hydrostatic field of 30 MPa of compression and a stage
whose total load is zero. Compression positive and u_r inward in the
comparisons, as in the cases.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

if not getattr(sys, "frozen", False):                 # from the source tree
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ogr_fem2d.engine.compiled import RUST  # noqa: E402
from ogr_fem2d.engine.mesh_radial import quarter_annulus  # noqa: E402
from ogr_fem2d.engine.reference import mohr_coulomb as mc  # noqa: E402
from ogr_fem2d.engine.reference import solver  # noqa: E402
from ogr_fem2d.engine.reference.elastic import Elastic  # noqa: E402

CASES = ("001-kirsch-hueco-elastico", "002-salencon-hueco-mohr-coulomb")


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


def main() -> int:
    import ogr_fem2d
    from ogr_fem2d import _engine
    frozen = getattr(sys, "frozen", False)
    print(f"OGR FEM2D {ogr_fem2d.__version__}, {'frozen' if frozen else 'from source'}; "
          f"Python {sys.version.split()[0]}")
    print(f"engine: {Path(_engine.__file__).resolve()}")
    failures = []
    for name, check in zip(CASES, (case_001, case_002)):
        case = json.loads((_cases_dir() / name / "esperado.json").read_text(encoding="utf-8"))
        print(f"{name} ({case['ficha']})")
        t = time.perf_counter()
        failures += [f"{name}: {f}" for f in check(case)]
        print(f"  solved in {time.perf_counter() - t:.1f} s")
    print("BOTH CASES PASS" if not failures else "FAILURES: " + "; ".join(failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
