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

The state of the machine is part of the measure (the owner's rule, 2026-10-27:
other programs may be running, or the computer more loaded during one of the
runs). It is recorded with every result and decides whether the result is
valid:

* the load of the whole system (busy share of all the logical cores, from
  the operating system: GetSystemTimes on Windows, /proc/stat on Linux) and
  the free memory, sampled for a moment before the measure and after each
  block of it, while the benchmark itself is idle;
* the CPU share of every timing: the process's CPU time over the wall time of
  the timed calls. Close to 1 means the process had its core all the time;
  below 1 the system gave the core to someone else in the middle of the
  measure; above 1 some library used more than one thread.

A measure is VALID when the other programs used at most ``--max-load`` per
cent of the machine at every sample, and every CPU share is within
[0.95, 1.05]. By default the benchmark refuses to start on a loaded machine
(``--force`` measures anyway, and the result says it is not valid).

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
import ctypes  # noqa: E402
import datetime  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import platform  # noqa: E402
import statistics  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from dataclasses import dataclass  # noqa: E402
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


# ------------------------------------------------- the state of the machine
def _system_times():
    """(idle, total) CPU times of the whole machine, all cores, or None
    where the platform has no way known here."""
    if sys.platform == "win32":
        idle, kernel, user = (ctypes.c_ulonglong(), ctypes.c_ulonglong(),
                              ctypes.c_ulonglong())
        # kernel time includes the idle time (GetSystemTimes, Win32 API)
        if ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel),
                                                 ctypes.byref(user)):
            return float(idle.value), float(kernel.value + user.value)
        return None
    stat = Path("/proc/stat")
    if stat.exists():
        fields = [float(x) for x in stat.read_text().split("\n")[0].split()[1:]]
        return fields[3] + fields[4], sum(fields)         # idle + iowait, total
    return None


def _free_memory_gb():
    if sys.platform == "win32":
        class Status(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong),
                        ("total", ctypes.c_ulonglong), ("available", ctypes.c_ulonglong),
                        ("page_total", ctypes.c_ulonglong), ("page_free", ctypes.c_ulonglong),
                        ("virtual_total", ctypes.c_ulonglong),
                        ("virtual_free", ctypes.c_ulonglong), ("extended", ctypes.c_ulonglong)]
        status = Status()
        status.length = ctypes.sizeof(Status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return status.available / 2 ** 30
        return None
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return float(line.split()[1]) / 2 ** 20
    except OSError:
        pass
    return None


def machine_state(seconds: float = 2.0) -> dict:
    """Busy share of the whole machine over ``seconds`` while this process
    waits (so it is the load of the OTHER programs), and the free memory."""
    before = _system_times()
    time.sleep(seconds)
    after = _system_times()
    busy = None
    if before and after and after[1] > before[1]:
        busy = 100.0 * (1.0 - (after[0] - before[0]) / (after[1] - before[1]))
    return {"other_load_percent": busy, "logical_cores": os.cpu_count(),
            "free_memory_gb": _free_memory_gb()}


@dataclass(frozen=True)
class Timing:
    """Median wall time of the calls, and the CPU share of the process over
    all of them (CPU time / wall time)."""
    seconds: float
    cpu_share: float


def timed(call, repeats: int) -> Timing:
    """``repeats`` calls after one warm-up call."""
    call()
    times = []
    cpu_0, wall_0 = time.process_time(), time.perf_counter()
    for _ in range(repeats):
        t = time.perf_counter()
        call()
        times.append(time.perf_counter() - t)
    cpu, wall = time.process_time() - cpu_0, time.perf_counter() - wall_0
    return Timing(statistics.median(times), cpu / wall if wall > 0 else float("nan"))


def rounds(calls: dict, repeats: dict) -> dict:
    """The A/B of the suite: every call timed one after the other, then the
    whole round again as the control. name -> (first, control) Timing."""
    first = {name: timed(call, repeats[name]) for name, call in calls.items()}
    control = {name: timed(call, repeats[name]) for name, call in calls.items()}
    return {name: (first[name], control[name]) for name in calls}


def _entry(pair) -> dict:
    a, b = pair
    return {"first": a.seconds, "control": b.seconds,
            "cpu_share": [a.cpu_share, b.cpu_share]}


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
            "seconds": {k: _entry(v) for k, v in result.items()},
            "machine_after": machine_state()}


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
            "update_seconds": {k_: _entry(v) for k_, v in update.items()},
            "linear_seconds": {k_: _entry(v) for k_, v in linear.items()},
            "machine_after": machine_state()}


def _spread(entry) -> float:
    a, b = entry["first"], entry["control"]
    return abs(a - b) / min(a, b)


CPU_SHARE = (0.95, 1.05)


def verdict(before: dict, integration: dict, mesh: dict, max_load: float) -> list[str]:
    """Why the measure is not valid; empty when it is."""
    reasons = []
    for where, state in (("before", before), ("after the integration", integration["machine_after"]),
                         ("after the mesh", mesh["machine_after"])):
        load = state["other_load_percent"]
        if load is None:
            reasons.append(f"the load of the machine {where} could not be read")
        elif load > max_load:
            reasons.append(f"other programs used {load:.0f} % of the machine {where} "
                           f"(at most {max_load:.0f} %)")
    for block, entries in (("integration", integration["seconds"]),
                           ("update", mesh["update_seconds"]), ("linear", mesh["linear_seconds"])):
        for name, e in entries.items():
            for share in e["cpu_share"]:
                if not CPU_SHARE[0] <= share <= CPU_SHARE[1]:
                    reasons.append(f"{block} {name}: CPU share {share:.2f} outside {CPU_SHARE}")
    return reasons


def _state_line(label: str, state: dict) -> str:
    load = state["other_load_percent"]
    memory = state["free_memory_gb"]
    return (f"Machine {label}: other programs {'?' if load is None else f'{load:.0f}'} % of "
            f"{state['logical_cores']} logical cores, "
            f"{'?' if memory is None else f'{memory:.1f}'} GB free")


def report(integration: dict, mesh: dict, before: dict | None = None,
           reasons: list[str] | None = None) -> str:
    lines = []
    if before is not None:
        lines.append(_state_line("before", before))
    sec = integration["seconds"]
    n = integration["points"]
    lines.append(f"Constitutive integration, {n} points {integration['regions']}")
    for name in ("reference", "numpy", "rust"):
        a, b = sec[name]["first"], sec[name]["control"]
        share = "/".join(f"{x:.2f}" for x in sec[name]["cpu_share"])
        lines.append(f"  {name:9s} {a * 1e3:10.2f} ms  control {b * 1e3:10.2f} ms  "
                     f"({a / n * 1e9:8.1f} ns/point, rounds differ {_spread(sec[name]) * 100:.1f} %, "
                     f"CPU share {share})")
    ratio = [sec["numpy"][k] / sec["rust"][k] for k in ("first", "control")]
    lines.append(f"  NumPy / Rust = {ratio[0]:.1f} (control {ratio[1]:.1f}); "
                 f"criterion 5 asks >= 10")
    lines.append(_state_line("after the integration", integration["machine_after"]))
    lines.append(f"Mesh of case 002 (psi = 30), {mesh['elements']} elements, "
                 f"{mesh['points']} points ({mesh['plastic_points']} plastic), {mesh['dofs']} dofs")
    for name, e in mesh["update_seconds"].items():
        lines.append(f"  update {name:9s} {e['first'] * 1e3:10.2f} ms  control {e['control'] * 1e3:10.2f} ms")
    for name, e in mesh["linear_seconds"].items():
        lines.append(f"  {name:16s} {e['first'] * 1e3:10.2f} ms  control {e['control'] * 1e3:10.2f} ms")
    lines.append(_state_line("after the mesh", mesh["machine_after"]))
    if reasons is not None:
        lines.append("VALID MEASURE" if not reasons else
                     "NOT A VALID MEASURE: " + "; ".join(reasons))
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--points", type=int, default=100_000)
    parser.add_argument("--repeats", type=int, default=9)
    parser.add_argument("--out", type=Path, default=ROOT / "poc" / "resultados")
    parser.add_argument("--max-load", type=float, default=10.0,
                        help="per cent of the machine the other programs may use")
    parser.add_argument("--force", action="store_true",
                        help="measure on a loaded machine (the result says it is not valid)")
    args = parser.parse_args(argv)
    before = machine_state(3.0)
    print(_state_line("before", before))
    load = before["other_load_percent"]
    if (load is None or load > args.max_load) and not args.force:
        print(f"The machine is not idle (at most {args.max_load:.0f} % allowed): close what "
              "is running, or measure with --force and get a result marked not valid.")
        return 3
    integration = measure_integration(args.points, args.repeats)
    mesh = measure_mesh(args.repeats)
    reasons = verdict(before, integration, mesh, args.max_load)
    text = report(integration, mesh, before, reasons)
    print(text)
    record = {"date": datetime.datetime.now().isoformat(timespec="seconds"),
              "machine": {"platform": platform.platform(), "processor": platform.processor(),
                          "python": sys.version.split()[0], "numpy": np.__version__,
                          "scipy": scipy.__version__,
                          "threads": {k: os.environ.get(k) for k in
                                      ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}},
              "seed": SEED, "proportions": PROPORTIONS,
              "machine_before": before, "max_load_percent": args.max_load,
              "valid": not reasons, "not_valid_because": reasons,
              "integration": integration, "mesh": mesh}
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.date.today().isoformat()
    (args.out / f"benchmark_{stamp}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    (args.out / f"benchmark_{stamp}.txt").write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
