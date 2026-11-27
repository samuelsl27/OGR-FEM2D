# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The program with its interface, frozen with PyInstaller (spec 006, T36).

    python poc/freeze/gui.py [model]                 # from the source tree
    dist/ogr-fem2d/ogr-fem2d[.exe] [model]           # frozen (poc/freeze/build.py)
    ... --self-test REPORT                           # the check, without a screen

Without ``--self-test`` it is the program: its window, with the model
given opened.

**The calculation's process.** The core's jobs start their child as
``sys.executable -m ogr_core.api.jobs.worker FOLDER``. Frozen,
``sys.executable`` is this program, which takes no ``-m``: it takes that
command here, first thing, and runs the core's worker itself, so that
meshing and calculating work frozen as they do from the sources. Nothing
of the core is copied or changed: its worker is called as it is.

**The self-test** (``--self-test REPORT``, with ``QT_QPA_PLATFORM=offscreen``):
case 007 (the spherical cavity, VER-STR-09) through the window, as a person
would do it. A copy of the case's model, which travels inside the program
with the other cases (``validacion/casos``, the help's), is opened; its mesh
is made again with Mesh > Discretize and Mesh and must be the case's, bit
for bit; it is calculated with Analysis > Compute; and it is queried in the
interpretation as its ``comparaciones_consulta`` says, every row within the
tolerance fixed before measuring, against Lamé's hollow sphere with u_R(b)
= 0 (Lamé 1852, in Timoshenko and Goodier 1951, §121, Eqs. 197-198; the
closed form of spec 002, ``soluciones_cerradas.sphere_fixed_outer``). What
it did, line by line, goes to REPORT (the frozen program has no console on
Windows); the last line says SELF-TEST PASSES or SELF-TEST FAILS, and the
exit code is 0 only when it passes.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
CASE = "007-cavidad-esferica-malla-general"
KPA = 1000.0                                   # kPa per MPa: the closed form is in MPa


def _job_child(argv) -> None:
    """The core's job child, when this program was started as one."""
    if len(argv) >= 4 and argv[1:3] == ["-m", "ogr_core.api.jobs.worker"]:
        from ogr_core.api.jobs import worker
        sys.exit(worker.main(argv[3:]))


def _bundle() -> Path:
    return Path(getattr(sys, "_MEIPASS", _ROOT))


def _closed_forms():
    import importlib.util
    where = (_bundle() / "comprobaciones_002" if getattr(sys, "frozen", False) else
             _ROOT / "spec" / "features" / "002-motor-elastico" / "comprobaciones")
    spec = importlib.util.spec_from_file_location("soluciones_cerradas_002",
                                                  where / "soluciones_cerradas.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def self_test(report: Path) -> int:
    import json
    import math
    import shutil
    import tempfile

    lines: list[str] = []

    def say(text: str) -> None:
        lines.append(text)
        report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok = True
    try:
        import ogr_fem2d
        from ogr_fem2d.gui import help as hp
        from ogr_fem2d.gui.app import application
        from ogr_fem2d.gui.main_window import MainWindow
        from ogr_fem2d.model import ogr_file
        frozen = getattr(sys, "frozen", False)
        say(f"OGR FEM2D {ogr_fem2d.__version__}, {'frozen' if frozen else 'from the sources'}")
        closed = _closed_forms()
        folder = hp.cases_folder()
        case = next(c for c in hp.cases() if c.id == CASE)
        expected = json.loads((case.folder / "esperado.json").read_text(encoding="utf-8"))
        say(f"cases: {folder} ({len(hp.cases())})")
        app = application()
        w = MainWindow()
        w.confirm_save_to_compute = lambda: True
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / "caso-007.ogrfem2d"
            shutil.copyfile(case.model, copy)
            w.open_path(str(copy))
            stored = ogr_file.read(case.model).mesh
            w.session.call("mesh_reset")
            assert w.session.model.mesh is None
            w.act_mesh()                                   # Mesh > Discretize and Mesh
            made = w.session.model.mesh
            same = made is not None and (made.nodes, made.elements) == (stored.nodes,
                                                                          stored.elements)
            say(f"mesh: {0 if made is None else len(made.elements)} elements, "
                f"{'the case' if same else 'NOT the case'}'s bit for bit")
            ok &= same
            w.act_save()
            assert w.compute() is None                     # Analysis > Compute
            w.compute_window.wait()
            state = w.session.ws.jobs.get(w.compute_window.followed).status()["state"]
            from ogr_fem2d.results import calculate as calc
            opened = calc.open_results(copy)
            variant = opened.results.header.engine_variant if opened.status == calc.VALID else "-"
            say(f"calculation: {state}, results {opened.status}, engine {variant}; "
                f"{w.compute_window.summary_text()}")
            ok &= state == "done" and opened.status == calc.VALID
            w.interpret()                                  # Analysis > Interpret
            win = w.interpret_window
            spec = expected["comparaciones_consulta"]
            win.set_stage(spec["fase"])
            b = expected["modelo"]["geometria"]["b"]
            u_a = closed.sphere_fixed_outer(closed.A, b)[2]
            for query in spec["consultas"]:
                for mq in query["magnitudes"]:
                    q = mq["magnitud"]
                    win.set_quantity(q)
                    qw = (win.query_line([query["desde"], query["hasta"]], query["n"])
                          if query["tipo"] == "linea" else
                          win.query_boundary(query["contorno"], query["n_por_segmento"],
                                             query["distancia"]))
                    worst, n = 0.0, 0
                    for r in qw.got["rows"]:
                        radius = math.hypot(r["x"], r["y"])
                        if query["tipo"] != "linea" and abs(radius - closed.A) > 1e-9:
                            continue                       # the straight stretches: excavated
                        s_r, s_t, u = closed.sphere_fixed_outer(radius, b)
                        if r["value"] is None:
                            worst = math.inf
                            continue
                        if q == "u":
                            e = abs(r["value"] - u) / u_a
                        else:
                            want = {"sigma_1": s_t, "sigma_z": s_t, "sigma_3": s_r}[q]
                            e = abs(r["value"] / KPA - want) / closed.P0
                        worst, n = max(worst, e), n + 1
                    passes = n > 0 and worst <= mq["tolerancia_absoluta"]
                    ok &= passes
                    say(f"{query['tipo']} {q}: {n} points, worst {worst:.5f} "
                        f"{mq['unidad_tolerancia']} (tolerance {mq['tolerancia_absoluta']}) "
                        f"{'ok' if passes else 'FAILS'}")
            w.confirm_discard = lambda: True
            w.close()
        app.processEvents()
    except BaseException as err:                       # noqa: BLE001 - said in the report
        import traceback
        say("".join(traceback.format_exception(err)).rstrip())
        ok = False
    say("SELF-TEST PASSES" if ok else "SELF-TEST FAILS")
    return 0 if ok else 1


def main(argv=None) -> int:
    argv = sys.argv if argv is None else argv
    _job_child(argv)
    if not getattr(sys, "frozen", False):              # from the source tree
        sys.path[:0] = [str(_ROOT)]
    if len(argv) >= 3 and argv[1] == "--self-test":
        return self_test(Path(argv[2]))
    from ogr_fem2d.gui.app import main as program
    return program(argv[1:])


if __name__ == "__main__":
    sys.exit(main())
