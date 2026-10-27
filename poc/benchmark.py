# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The measure of spec 001 (RF-8, task T13): what each variant of the engine
costs, for criterion 5 of ADR-0001 (Rust at least 10 times faster than
vectorised NumPy in the constitutive integration).

    .venv/Scripts/python poc/benchmark.py            # writes poc/resultados/
    .venv/Scripts/python poc/benchmark.py --points 20000 --repeats 3

How it measures (the suite's rule, AGENTS.md of OGR Slip2D, «Cómo medir el
coste de un cambio»): A/B IN THE SAME PROCESS, BACK TO BACK, WITH A REPEATED
CONTROL. Timings across processes or sessions drift with the machine, so
every variant is timed in one run, one after the other, and then the whole
round is repeated: the second round is the control. If the two rounds of a
variant differ as much as the effect being measured, the measure does not
decide. Each timing is the median of ``repeats`` calls, after one warm-up
call.

One thread for everyone: the Rust variant runs in one thread (spec 001,
"Fuera de alcance"), so the thread pools of NumPy's libraries are limited to
one before NumPy is imported.

What is measured:

1. **The constitutive integration** (criterion 5): ``integrate`` of the three
   variants on the same seeded set of points and strain increments
   (seeded_set): Mohr-Coulomb with psi = 0, 15 and 30 degrees, with the
   proportion of each region of the return fixed and written in the result
   (PROPORTIONS). The region of each point is the reference's, the oracle.
2. **The call per global iteration** (``update``: strains, integration,
   internal forces and B^T D B of every point) on the mesh of validation
   case 002 with psi = 30 degrees, at its plastic end state.
3. **The assembly** of K_T from the values of update (SciPy, the same for the
   three variants) and **the linear solution** (SuperLU factorisation and
   one solve), RF-8.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import os

for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_name, "1")

import argparse  # noqa: E402
import datetime  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import platform  # noqa: E402
import statistics  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import scipy  # noqa: E402
from scipy.sparse import coo_matrix  # noqa: E402
from scipy.sparse.linalg import splu  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ogr_fem2d.engine import interface  # noqa: E402
from ogr_fem2d.engine.mesh_radial import quarter_annulus  # noqa: E402
from ogr_fem2d.engine.reference import mohr_coulomb as mc  # noqa: E402
from ogr_fem2d.engine.reference import solver  # noqa: E402

#: Share of each region of the return in the seeded set.
PROPORTIONS = {"elastic": 0.40, "plane": 0.30, "right edge": 0.10,
               "left edge": 0.10, "apex": 0.10}
E, NU, C, PHI = 10000.0, 0.2, 3.45, math.radians(30.0)
SEED = 2026


def _candidates(rng, n):
    """Trial states of two kinds: compressive, around the field of the
    cases (they give elastic points, the plane and the edges), and tensile
    with dilatancy (they reach the apex, which psi = 0 refuses)."""
    half = n // 2
    psi = np.concatenate([rng.choice([0.0, 15.0, 30.0], half),
                          rng.choice([15.0, 30.0], n - half)])
    start = np.concatenate([
        np.column_stack([rng.uniform(-40.0, 5.0, (half, 3)), rng.uniform(-10.0, 10.0, half)]),
        np.column_stack([rng.uniform(-5.0, 10.0, (n - half, 3)), rng.uniform(-2.0, 2.0, n - half)])])
    strains = np.concatenate([rng.uniform(-3e-3, 3e-3, (half, 3)),
                              np.column_stack([rng.uniform(0.0, 3e-3, (n - half, 2)),
                                               rng.uniform(-5e-4, 5e-4, n - half)])])
    return psi, start, strains


def _region(psi, start, strain):
    m = mc.MohrCoulomb(E, NU, C, PHI, math.radians(psi))
    try:
        return mc.update(m, tuple(start), tuple(strain)).region
    except mc.ReturnMappingError:
        return None


def seeded_set(n: int, seed: int = SEED):
    """n points with PROPORTIONS of each region, decided by the reference.
    Returns (materials (n, 6), start (n, 4), strains (n, 3), regions)."""
    rng = np.random.default_rng(seed)
    wanted = {r: int(round(share * n)) for r, share in PROPORTIONS.items()}
    wanted["elastic"] += n - sum(wanted.values())
    chosen = {r: [] for r in wanted}
    while any(len(chosen[r]) < wanted[r] for r in wanted):
        psi, start, strains = _candidates(rng, max(1000, n))
        for k in range(len(psi)):
            region = _region(psi[k], start[k], strains[k])
            if region in chosen and len(chosen[region]) < wanted[region]:
                chosen[region].append((psi[k], start[k], strains[k]))
    rows = [(region, item) for region in PROPORTIONS for item in chosen[region]]
    order = rng.permutation(len(rows))           # mixed, as in a mesh
    rows = [rows[i] for i in order]
    materials = np.array([[interface.MOHR_COULOMB, E, NU, C, PHI, math.radians(p)]
                          for _r, (p, _s, _e) in rows])
    start = np.array([s for _r, (_p, s, _e) in rows])
    strains = np.array([e for _r, (_p, _s, e) in rows])
    return materials, start, strains, [r for r, _ in rows]


def point_geometry(materials) -> interface.Geometry:
    """A geometry with only materials: integrate() needs nothing else."""
    n = len(materials)
    return interface.Geometry(0, np.zeros((n, 6), np.int64), np.zeros((n, 6)),
                              np.zeros((n, 6)), np.zeros(n), np.arange(n),
                              np.zeros(n, np.int64), np.zeros((n, 2)), materials)


def timed(call, repeats: int) -> float:
    """Median seconds of ``repeats`` calls, after one warm-up call."""
    call()
    times = []
    for _ in range(repeats):
        t = time.perf_counter()
        call()
        times.append(time.perf_counter() - t)
    return statistics.median(times)


def rounds(calls: dict, repeats: dict) -> dict:
    """The A/B of the suite: every call timed one after the other, then the
    whole round again as the control. name -> (first, control) seconds."""
    first = {name: timed(call, repeats[name]) for name, call in calls.items()}
    control = {name: timed(call, repeats[name]) for name, call in calls.items()}
    return {name: (first[name], control[name]) for name in calls}


def _variants():
    from ogr_fem2d.engine.compiled import RUST
    from poc.vectorized import NUMPY
    return {"reference": solver.REFERENCE, "numpy": NUMPY, "rust": RUST}


def measure_integration(n: int, repeats: int) -> dict:
    materials, start, strains, regions = seeded_set(n)
    g = point_geometry(materials)
    prepared = {name: v.prepare(g) for name, v in _variants().items()}
    calls = {name: (lambda p=p: p.integrate(start, strains)) for name, p in prepared.items()}
    reps = {"reference": max(1, repeats // 3), "numpy": repeats, "rust": repeats}
    result = rounds(calls, reps)
    counts = {r: regions.count(r) for r in PROPORTIONS}
    return {"points": n, "regions": counts, "repeats": reps,
            "seconds": {k: {"first": a, "control": b} for k, (a, b) in result.items()}}


def _case_002_state():
    """The mesh of case 002, psi = 30 degrees, and its plastic end state
    (computed with the Rust variant, which equals the reference: T12)."""
    case = json.loads((ROOT / "validacion/casos/002-salencon-hueco-mohr-coulomb/"
                       "esperado.json").read_text(encoding="utf-8"))
    variant = next(v for v in case["variantes"] if v["psi"] == 30.0)
    mesh_spec, stage = variant["malla"], case["modelo"]["fase"]
    mesh = quarter_annulus(1.0, case["modelo"]["geometria"]["b"], mesh_spec["n_radial"],
                           mesh_spec["n_theta"], mesh_spec["crecimiento"])
    material = mc.MohrCoulomb(E, NU, C, PHI, math.radians(30.0))
    restrained = {2 * n + 1 for n in mesh.x_axis} | {2 * n for n in mesh.y_axis}
    for n in mesh.outer:
        restrained |= {2 * n, 2 * n + 1}
    model = solver.Model(mesh.nodes, mesh.elements, [material] * len(mesh.elements),
                         frozenset(restrained))
    field = (-30.0, -30.0, -30.0, 0.0)
    n_points = 3 * len(mesh.elements)
    result = solver.solve_stage(model, [field] * n_points, [0.0] * (2 * len(mesh.nodes)),
                                stage["escalones"], stage["tolerancia"],
                                stage["iteraciones_max"], 0, _variants()["rust"])
    return model, result


def measure_mesh(repeats: int) -> dict:
    model, result = _case_002_state()
    points = solver.integration_points(model)
    g = solver.geometry(model, points)
    n_dofs = g.n_dofs
    free = np.array([i for i in range(n_dofs) if i not in model.restrained])
    start = np.array([(-30.0, -30.0, -30.0, 0.0)] * len(points))
    du = np.array(result.displacement)          # the whole stage as one increment
    prepared = {name: v.prepare(g) for name, v in _variants().items()}
    calls = {name: (lambda p=p: p.update(start, du)) for name, p in prepared.items()}
    reps = {"reference": max(1, repeats // 3), "numpy": repeats, "rust": repeats}
    update = rounds(calls, reps)
    up = prepared["rust"].update(start, du)
    rows, cols = interface.stiffness_pattern(g)

    def assemble():
        return coo_matrix((up.stiffness.ravel(), (rows, cols)),
                          shape=(n_dofs, n_dofs)).tocsr()[free][:, free].tocsc()

    k = assemble()
    lu = splu(k)
    rhs = up.internal_forces[free]
    linear = rounds({"assembly": assemble, "factorisation": lambda: splu(k),
                     "solve": lambda: lu.solve(rhs)},
                    {"assembly": repeats, "factorisation": repeats, "solve": repeats})
    plastic = int(np.count_nonzero(up.plastic))
    return {"elements": len(model.elements), "points": len(points), "dofs": len(free),
            "plastic_points": plastic, "repeats": reps,
            "update_seconds": {k_: {"first": a, "control": b} for k_, (a, b) in update.items()},
            "linear_seconds": {k_: {"first": a, "control": b} for k_, (a, b) in linear.items()}}


def _spread(entry) -> float:
    a, b = entry["first"], entry["control"]
    return abs(a - b) / min(a, b)


def report(integration: dict, mesh: dict) -> str:
    lines = []
    sec = integration["seconds"]
    n = integration["points"]
    lines.append(f"Constitutive integration, {n} points {integration['regions']}")
    for name in ("reference", "numpy", "rust"):
        a, b = sec[name]["first"], sec[name]["control"]
        lines.append(f"  {name:9s} {a * 1e3:10.2f} ms  control {b * 1e3:10.2f} ms  "
                     f"({a / n * 1e9:8.1f} ns/point, rounds differ {_spread(sec[name]) * 100:.1f} %)")
    ratio = [sec["numpy"][k] / sec["rust"][k] for k in ("first", "control")]
    lines.append(f"  NumPy / Rust = {ratio[0]:.1f} (control {ratio[1]:.1f}); "
                 f"criterion 5 asks >= 10")
    lines.append(f"Mesh of case 002 (psi = 30), {mesh['elements']} elements, "
                 f"{mesh['points']} points ({mesh['plastic_points']} plastic), {mesh['dofs']} dofs")
    for name, e in mesh["update_seconds"].items():
        lines.append(f"  update {name:9s} {e['first'] * 1e3:10.2f} ms  control {e['control'] * 1e3:10.2f} ms")
    for name, e in mesh["linear_seconds"].items():
        lines.append(f"  {name:16s} {e['first'] * 1e3:10.2f} ms  control {e['control'] * 1e3:10.2f} ms")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--points", type=int, default=100_000)
    parser.add_argument("--repeats", type=int, default=9)
    parser.add_argument("--out", type=Path, default=ROOT / "poc" / "resultados")
    args = parser.parse_args(argv)
    integration = measure_integration(args.points, args.repeats)
    mesh = measure_mesh(args.repeats)
    text = report(integration, mesh)
    print(text)
    record = {"date": datetime.datetime.now().isoformat(timespec="seconds"),
              "machine": {"platform": platform.platform(), "processor": platform.processor(),
                          "python": sys.version.split()[0], "numpy": np.__version__,
                          "scipy": scipy.__version__,
                          "threads": {k: os.environ.get(k) for k in
                                      ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}},
              "seed": SEED, "proportions": PROPORTIONS,
              "integration": integration, "mesh": mesh}
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.date.today().isoformat()
    (args.out / f"benchmark_{stamp}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    (args.out / f"benchmark_{stamp}.txt").write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
