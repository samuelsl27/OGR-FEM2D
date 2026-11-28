# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The diagnosis of spec 007, T2 (D5, 1; rule 6): where and why Newton fails
with psi = 0 in the two meshes that spec 001 left without convergence, and
what more load steps and more cuts of the increment do. It changes no code
of the program; it watches the engine from outside.

    .venv/Scripts/python spec/features/007-convergencia-y-colapso/comprobaciones/diagnostico_robustez.py [quick]

The two problems (spec 001, changelog v0.0.1; validacion/casos/002):

* case 002 with psi = 0 on its 16 x 64 mesh (n_theta = 16, n_radial = 64,
  growth 1.69^(1/8)), b = 100 m;
* the 21 m ring of tests/test_ring_identity_v001.py on 16 x 48 (n_theta =
  16, n_radial = 48, growth 1.2^(1/4)), the next of its nested family.

Both: the excavation of the hole from p0 = 30 MPa, Mohr-Coulomb E = 10 GPa,
nu = 0.2, c = 3.45 MPa, phi = 30 degrees, psi = 0; tolerance 1e-10 and 25
iterations, as the cases.

How it watches: a variant that wraps the Rust one (the default, the same
numbers as the reference to 1e-14, spec 001 T12) and records, for each
update call (one per iteration), whether it was refused (the apex with
psi = 0) and, from the returned stresses, the region of every point: elastic,
plane, an edge (two principal stresses equal) or apex. The increments of a
stage that fails, and its history, are read from the locals of solve_stage
in the traceback (a StateUpdateError does not carry them).

And, to tell whether it is psi = 0, the same meshes with psi = 1 and 5
degrees, where the apex is admissible.

Output: one line per run (steps, cuts allowed, result, cuts used, the load
factor reached, the increment that failed and why), and for the failed
increment of each run the iterations with their residual, the number of
plastic points and of points that changed region since the previous
iteration.
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(_ROOT), str(_ROOT / "tests")]

import _hole  # noqa: E402
from ogr_fem2d.engine.compiled import RUST  # noqa: E402
from ogr_fem2d.engine.reference import mohr_coulomb as mc  # noqa: E402
from ogr_fem2d.engine.reference import solver  # noqa: E402
from ogr_fem2d.engine.reference.elastic import stress_increment  # noqa: E402

closed = _hole.closed
MATERIAL = mc.MohrCoulomb(closed.E, closed.NU, closed.COH, closed.PHI, 0.0)
PROBLEMS = {
    "caso 002, 16 x 64": (100.0, 64, 16, 1.69 ** (1 / 8)),
    "anillo 21 m, 16 x 48": (21.0, 48, 16, 1.2 ** 0.25),
}
TOL, MAX_IT = 1e-10, 25


def regions(stresses: np.ndarray) -> np.ndarray:
    """0 elastic-or-plane is not decidable from the stress alone, so: 0 for
    a point with three distinct principal stresses, 1 left edge (s1 = s2),
    2 right edge (s2 = s3), 3 apex; the plastic flag says which of the
    distinct ones are on the plane."""
    sxx, syy, szz, txy = stresses.T
    c, r = 0.5 * (sxx + syy), np.hypot(0.5 * (sxx - syy), txy)
    p = np.sort(np.column_stack([c + r, c - r, szz]), axis=1)[:, ::-1]
    tol = 1e-9 * np.abs(p).max(axis=1).clip(min=1.0)
    left, right = p[:, 0] - p[:, 1] <= tol, p[:, 1] - p[:, 2] <= tol
    out = np.zeros(len(p), dtype=np.int64)
    out[left] = 1
    out[right] = 2
    out[left & right] = 3
    return out


def trial_of(g, k, start, du):
    """What the point k that was refused sees: its radius, its starting
    stress and its trial principal stresses (s1 >= s2 >= s3, tension
    positive, the zz one marked), and what the plane and the edge return
    give (mohr_coulomb.return_principal steps (iv.a) and (iv.c))."""
    nodes = g.nodes[k]
    ux, uy = du[2 * nodes], du[2 * nodes + 1]
    strain = (float(g.dndx[k] @ ux), float(g.dndy[k] @ uy),
              float(g.dndy[k] @ ux + g.dndx[k] @ uy))
    s0 = tuple(float(x) for x in start[k])
    d = stress_increment(MATERIAL.young, MATERIAL.poisson, strain)
    t = [a + b for a, b in zip(s0, d)]
    hi, lo, _ = mc.principal_in_plane(t[0], t[1], t[3])
    trial = sorted([(hi, "hi"), (lo, "lo"), (t[2], "zz")], reverse=True)
    return {"r": float(np.hypot(*g.xy[k])),
            "theta": float(np.degrees(np.arctan2(g.xy[k][1], g.xy[k][0]))),
            "start": s0, "strain": strain,
            "trial": [(round(v, 4), n) for v, n in trial]}


class Watch:
    """A variant around Rust that records every update call."""
    name = "rust (watched)"

    def __init__(self):
        self.calls: list[dict] = []

    def prepare(self, g):
        inner = RUST.prepare(g)
        watch = self

        class Prepared:
            def internal_forces(self, stresses):
                return inner.internal_forces(stresses)

            def integrate(self, start, strains):
                return inner.integrate(start, strains)

            def update(self, start, du):
                try:
                    result = inner.update(start, du)
                except solver.StateUpdateError as err:
                    k = int(np.flatnonzero((g.element == err.element) & (g.index == err.point))[0])
                    watch.calls.append({"refused": (err.element, err.point, err.reason),
                                        "trial": trial_of(g, k, start, du),
                                        "du": float(np.abs(du).max())})
                    raise
                kind = regions(np.asarray(result.stresses))
                plastic = np.asarray(result.plastic, dtype=bool)
                kind = np.where(plastic, kind + 10, -1)      # -1 elastic, 10 plane, 11/12 edges, 13 apex
                watch.calls.append({"kind": kind, "du": float(np.abs(du).max())})
                return result

        return Prepared()


def _stage_locals(err):
    """The locals of solve_stage when ``err`` left it: its history, its
    increments and the factor reached (a diagnosis reads them from the
    traceback; the engine does not give them with a StateUpdateError)."""
    tb = err.__traceback__
    found = None
    while tb is not None:
        if tb.tb_frame.f_code.co_name == "solve_stage":
            found = tb.tb_frame.f_locals
        tb = tb.tb_next
    return found


def run(name, steps, cuts, detail, material=MATERIAL):
    b, n_r, n_t, g = PROBLEMS[name]
    watch = Watch()
    t0 = time.perf_counter()
    error = None
    try:
        _mesh, result = _hole.excavate(b, n_r, n_t, g, material, steps, TOL, MAX_IT,
                                       max_cuts=cuts, variant=watch)
        history, increments, reached = result.history, list(result.increments), 1.0
    except (solver.NotConvergedError, solver.StateUpdateError) as err:
        error = err
        local = _stage_locals(err)
        history, increments, reached = local["history"], list(local["increments"]), local["factor"]
        target = local["pending"][0]
        why = (f"punto no actualizable (elemento {err.element}, punto {err.point})"
               if isinstance(err, solver.StateUpdateError) else "sin converger en 25 iteraciones")
        increments.append((reached, target, f"FAILED: {why}"))
    except RuntimeError as err:
        # SuperLU on a singular tangent (with psi > 0 the apex has D^ep = 0,
        # Remark 8.3): it is not cut, it leaves solve_stage as it is
        local = _stage_locals(err)
        print(f"  {steps:3d} escalones, {cuts:2d} particiones: SE ESCAPA {type(err).__name__}: {err}, "
              f"en el factor {local['factor']:.6f} -> {local['pending'][0]:.6f}, "
              f"tras {local['cuts']} particiones ({time.perf_counter() - t0:.1f} s)")
        return
    seconds = time.perf_counter() - t0
    n_cuts = sum(1 for inc in increments if inc[2].startswith("cut"))
    status = "converge" if error is None else "FALLA"
    print(f"  {steps:3d} escalones, {cuts:2d} particiones: {status}; particiones usadas {n_cuts}; "
          f"factor alcanzado {reached:.6f}; {len(watch.calls)} actualizaciones ({seconds:.1f} s)")
    if error is not None:
        print(f"      último incremento {reached:.6f} -> {increments[-1][1]:.6f}: {increments[-1][2][8:]}")
    refused = [c["refused"] for c in watch.calls if "refused" in c]
    not_conv = sum(1 for inc in increments if "did not converge" in inc[2] or "sin converger" in inc[2])
    print(f"      incrementos fallidos: {n_cuts + (error is not None)}; de ellos sin converger "
          f"{not_conv}, con un punto que pide el vértice {len(refused)}")
    if not detail or error is None:
        return
    print("      (it k: el residuo de la iteración k y la actualización que sigue a su corrección)")
    # iterations of every increment, matched to the calls: converged at k,
    # k calls; out of iterations, MAX_IT; refused after iteration j, j + 1
    by_number: dict[int, list] = {}
    for number, it, rel in history:
        by_number.setdefault(number, []).append((it, rel))
    position = 0
    numbers = sorted(by_number)
    for number, (f0, f1, why) in zip(numbers, increments):
        its = by_number[number]
        refused_here = "element" in why or "punto no actualizable" in why
        n_calls = len(its) - 1 + (1 if refused_here else 0)
        mine = watch.calls[position:position + n_calls]
        position += n_calls
        if number != numbers[-1]:
            continue
        print(f"      el último incremento, {number} ({f0:.6f} -> {f1:.6f}):")
        previous = None
        for k, call in enumerate(mine):
            it, rel = its[k]
            if "refused" in call:
                tr = call["trial"]
                print(f"        it {it:2d}: residuo {rel:.3e}; tras ella un punto pide el vértice "
                      f"(elemento {call['refused'][0]}, punto {call['refused'][1]}, r = {tr['r']:.4f} m, "
                      f"a {tr['theta']:.2f} grados del eje x; |du| máx {call['du']:.3e} m)")
                print(f"               tensión inicial {tuple(round(x, 4) for x in tr['start'])}, "
                      f"prueba principal {tr['trial']}")
                break
            kind = call["kind"]
            plastic = int((kind >= 10).sum())
            edges = int(((kind == 11) | (kind == 12)).sum())
            changed = "" if previous is None else f", cambian de región {int((kind != previous).sum())}"
            print(f"        it {it:2d}: residuo {rel:.3e}; |du| máx {call['du']:.3e} m; "
                  f"plásticos {plastic} (en arista {edges}){changed}")
            previous = kind


def main(quick: bool):
    grid = [(5, 0), (5, 4)] if quick else [(s, c) for s in (5, 10, 20, 40) for c in (0, 4, 8, 16)]
    for name in PROBLEMS:
        print(name)
        for steps, cuts in grid:
            run(name, steps, cuts, detail=True)
    if quick:
        return
    # is it psi = 0? the same meshes with a small dilatancy (the apex is
    # then admissible, Eq. 8.81), 5 steps and 4 cuts
    for psi in (1.0, 5.0):
        material = mc.MohrCoulomb(closed.E, closed.NU, closed.COH, closed.PHI, math.radians(psi))
        for name in PROBLEMS:
            print(f"{name}, psi = {psi:g} grados")
            run(name, 5, 4, detail=True, material=material)


if __name__ == "__main__":
    main("quick" in sys.argv[1:])
