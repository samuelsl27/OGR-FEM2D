# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What the CI does with a built wheel (spec 001, RF-9, task T14).

    python .github/scripts/wheel_check.py installed    # from OUTSIDE the tree
    python .github/scripts/wheel_check.py extract dist/<wheel>.whl

``installed``: the package installed from the wheel (not the source tree)
imports, its compiled module loads, and the Rust variant gives, on a small
Mohr-Coulomb excavation, what the Python reference of the same installed
package gives (ADR-0001, criterion 1, to 1e-10).

``extract``: copies the compiled module of the wheel into ogr_fem2d/ of the
source tree, so that the test suite, which runs from the tree (tests/
_runner.py refuses a package resolving outside it), runs the validation
cases on the binary of the wheel. The file gets the current time, so the
test that refuses a module older than its sources sees it as built now.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
import zipfile
from pathlib import Path

TREE = Path(__file__).resolve().parents[2]


def installed() -> int:
    import numpy as np

    import ogr_fem2d
    from ogr_fem2d import _engine
    from ogr_fem2d.engine.compiled import RUST
    from ogr_fem2d.engine.mesh_radial import quarter_annulus
    from ogr_fem2d.engine.reference import mohr_coulomb as mc
    from ogr_fem2d.engine.reference import solver

    where = Path(ogr_fem2d.__file__).resolve()
    print(f"ogr_fem2d {ogr_fem2d.__version__} from {where}; engine {Path(_engine.__file__).name}")
    if TREE in where.parents:
        print("the package resolves to the source tree, not to the installed wheel")
        return 1
    mesh = quarter_annulus(1.0, 21.0, 6, 3, 1.3)
    restrained = {2 * n + 1 for n in mesh.x_axis} | {2 * n for n in mesh.y_axis}
    for n in mesh.outer:
        restrained |= {2 * n, 2 * n + 1}
    material = mc.MohrCoulomb(10000.0, 0.2, 3.45, math.radians(30.0), math.radians(15.0))
    model = solver.Model(mesh.nodes, mesh.elements, [material] * len(mesh.elements),
                         frozenset(restrained))
    args = (model, [(-30.0, -30.0, -30.0, 0.0)] * (3 * len(mesh.elements)),
            [0.0] * (2 * len(mesh.nodes)), 5, 1e-10, 25)
    rust = solver.solve_stage(*args, variant=RUST)
    ref = solver.solve_stage(*args)
    u_rust, u_ref = np.array(rust.displacement), np.array(ref.displacement)
    gap = np.abs(u_rust - u_ref).max() / np.abs(u_ref).max()
    print(f"plastic points {sum(ref.plastic)}; Rust vs reference, displacements: {gap:.1e}")
    if not sum(ref.plastic) or gap > 1e-10:
        print("the installed Rust variant does not reproduce the reference")
        return 1
    return 0


def extract(wheel: str) -> int:
    with zipfile.ZipFile(wheel) as archive:
        members = [m for m in archive.namelist()
                   if m.startswith("ogr_fem2d/_engine") and m.endswith((".pyd", ".so"))]
        if len(members) != 1:
            print(f"expected one compiled module in {wheel}, found {members}")
            return 1
        target = TREE / "ogr_fem2d" / Path(members[0]).name
        target.write_bytes(archive.read(members[0]))     # mtime: now
    print(f"{members[0]} -> {target}")
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["installed"]:
        sys.exit(installed())
    if sys.argv[1:2] == ["extract"] and len(sys.argv) == 3:
        sys.exit(extract(sys.argv[2]))
    print(__doc__)
    sys.exit(2)
