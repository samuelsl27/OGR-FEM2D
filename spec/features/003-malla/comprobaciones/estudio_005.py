# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The mesh study of case 005 (spec 003, D12, task T15): the case and its two
identities on the graded six-node mesh with a window of size h around the
hole (tests/_kirsch_mesh.py), the worst relative error of each, the size of
the mesh and the time. With ``--hole`` the first study, which varied only
the nodes of the hole (no window) and did not converge.

Run it with the project's environment, alone on the machine:

    .venv/Scripts/python spec/features/003-malla/comprobaciones/estudio_005.py

The spec asked for 16, 32, 64 and 128 divisions of the hole: with pieces of
at most 10 degrees (D15) a circle needs 36 at least. That study (36, 64, 128,
256, no window) stalled at -0.5 % in u_r and 3 to 6 % in the anisotropic
identity; the owner chose (2026-11-23) a window around the hole, and the
study is made with its size h = 0.2, 0.1 and 0.05 m.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from dataclasses import replace  # noqa: E402

import _kirsch_mesh as k  # noqa: E402
from ogr_fem2d.mesh import mesher  # noqa: E402


def _no_window(n):
    m = k.geometry(0.1)
    return replace(m, settings=replace(m.settings, boundary_nodes=n, windows=()))


def main(values, hole=False, max_size=None) -> None:
    print(f"{'N/h':>5} {'nodes':>7} {'elem':>7} {'mesh s':>7} {'solve s':>8} "
          f"{'case sθ':>9} {'case ur':>9} {'id30 sθ':>9} {'id30 ur':>9} "
          f"{'id15 sθ':>9} {'id15 ur':>9}")
    for n in values:
        t0 = time.perf_counter()
        mesh = mesher.mesh(_no_window(int(n)) if hole else k.geometry(n, max_size))
        t1 = time.perf_counter()
        row = []
        for run in (lambda: k.run_case(mesh), lambda: k.run_identity(mesh, 30.0, 30.0),
                    lambda: k.run_identity(mesh, 30.0, 15.0)):
            model, out = run()
            s1 = 30.0
            s2 = 15.0 if len(row) == 4 else 30.0
            w = k.worst_errors(mesh, model, out, s1, s2)
            row += [w["sigma_theta"], w["u_r"]]
        t2 = time.perf_counter()
        print(f"{n:>5g} {len(mesh.nodes):>7} {len(mesh.elements):>7} {t1 - t0:>7.2f} "
              f"{t2 - t1:>8.2f} " + " ".join(f"{100 * e:>8.4f}%" for e in row))


if __name__ == "__main__":
    args = sys.argv[1:]
    cap = None
    if "--max" in args:
        i = args.index("--max")
        cap = float(args[i + 1])
        args = args[:i] + args[i + 2:]
    if "--hole" in args:
        args.remove("--hole")
        main(tuple(int(a) for a in args) or (36, 64, 128, 256), hole=True)
    else:
        main(tuple(float(a) for a in args) or (0.2, 0.1, 0.05), max_size=cap)
