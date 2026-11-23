# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The convergence studies of cases 006 and 007 (spec 004, T16 and T17), and
the writing of the ``modelo.ogrfem2d`` of cases 005, 006 and 007.

    .venv/Scripts/python spec/features/004-modelo-y-proyecto/comprobaciones/estudio_006_007.py study 006
    .venv/Scripts/python spec/features/004-modelo-y-proyecto/comprobaciones/estudio_006_007.py study 007
    .venv/Scripts/python spec/features/004-modelo-y-proyecto/comprobaciones/estudio_006_007.py write

``study`` meshes and solves each case with the window of size h and the
bound 50 h for h halving, and prints the worst errors of its esperado.json
(tests/_cases_model.py). ``write`` writes every model with its mesh: 005
with the mesh of its esperado.json, 006 and 007 with the h their esperado.json
fixes.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import _cases_model as cm                                      # noqa: E402
from ogr_fem2d.engine import analysis                          # noqa: E402
from ogr_fem2d.model import ogr_file, translate                # noqa: E402

STUDY = {"006": (0.25, 0.125, 0.0625), "007": (0.2, 0.1, 0.05)}


def run(which: str, h: float):
    model = translate.mesh(cm.model_006(h) if which == "006" else cm.model_007(h))
    engine = translate.to_engine(model)
    t = time.perf_counter()
    out = analysis.run(engine)[0]
    seconds = time.perf_counter() - t
    if which == "006":
        e1, e3, n = cm.errors_006(engine, out)
        return len(engine.elements), seconds, f"sigma_1 {e1:.5f} q, sigma_3 {e3:.5f} q ({n} points)"
    st, u, n, k = cm.errors_007(model, engine, out)
    return len(engine.elements), seconds, f"sigma_t {100 * st:.3f} %, u_R {100 * u:.3f} % ({n} points, {k} nodes)"


def write():
    m = translate.mesh(cm.model_005())
    ogr_file.write(m, cm.path("005-kirsch-malla-general"))
    for which, name in (("006", "006-carga-en-faja-malla-general"),
                        ("007", "007-cavidad-esferica-malla-general")):
        mesh = cm.case(name)["modelo"]["malla"]
        builder = cm.model_006 if which == "006" else cm.model_007
        m = translate.mesh(builder(mesh["ventana"]["h"], mesh["ventana"]["semilado"],
                                   mesh["cota_maxima"] / mesh["ventana"]["h"]))
        ogr_file.write(m, cm.path(name))


if __name__ == "__main__":
    if sys.argv[1] == "study":
        for h in STUDY[sys.argv[2]]:
            print(sys.argv[2], h, *run(sys.argv[2], h), flush=True)
    elif sys.argv[1] == "write":
        write()
