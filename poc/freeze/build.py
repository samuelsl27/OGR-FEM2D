# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Freeze poc/freeze/casos.py with PyInstaller and check the executable
(spec 001, RF-10, task T15; ADR-0001, criterion 3, second part).

    .venv/Scripts/python poc/freeze/build.py               # build and check both
    .venv/Scripts/python poc/freeze/build.py --check       # check the last builds
    .venv/Scripts/python poc/freeze/build.py --only gui    # one of them (casos, gui)

Two programs (spec 006, T36, adds the second):

* ``ogr-fem2d-casos`` (spec 001): the validation cases solved by the engine,
  in a console;
* ``ogr-fem2d`` (spec 006): the program with its interface, windowed, with
  the validation cases inside (the help's, ``validacion/casos``) and the
  closed forms its self-test compares against. Its check runs
  ``--self-test REPORT`` without a screen (``QT_QPA_PLATFORM=offscreen``):
  case 007 opened, meshed, calculated and queried through the window
  (poc/freeze/gui.py), and reads the report.

The build needs the compiled engine (ogr_fem2d._engine: maturin develop, or
the wheel installed) and PyInstaller, which is only a tool of the project's
environment (spec 001, D6). It goes to build/freeze/ (ignored by git); the
program, to build/freeze/dist/ogr-fem2d-casos/ (one folder, PyInstaller's
default), with the esperado.json of the validation cases inside and, for
cases 003 and 004 (spec 002, T14), the modules that build them
(tests/_sphere.py, tests/_strip.py) and the closed forms they compare
against.

The check runs the executable from a temporary folder OUTSIDE the source
tree, with PYTHONPATH and PYTHONHOME removed, so it cannot fall back on the
sources or on an installed Python: it must say it is frozen, solve all
the cases within their tolerances with the compiled engine that travels inside
it (not one found elsewhere), and exit with 0.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAME = "ogr-fem2d-casos"
WORK = ROOT / "build" / "freeze"
#: The cases of poc/freeze/casos.py, whose esperado.json go inside.
CASES = ("001-kirsch-hueco-elastico", "002-salencon-hueco-mohr-coulomb",
         "003-cavidad-esferica-elastica", "004-carga-en-faja-elastica")
CLOSED_FORMS = ROOT / "spec" / "features" / "002-motor-elastico" / "comprobaciones"


GUI_NAME = "ogr-fem2d"


def executable(name: str = NAME) -> Path:
    suffix = ".exe" if sys.platform == "win32" else ""
    return WORK / "dist" / name / f"{name}{suffix}"


def build_gui() -> int:
    sep = os.pathsep
    data = ["--add-data", f"{ROOT / 'validacion' / 'casos'}{sep}validacion/casos",
            "--add-data", f"{CLOSED_FORMS / 'soluciones_cerradas.py'}{sep}comprobaciones_002"]
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
               "--name", GUI_NAME, "--windowed",
               "--paths", str(ROOT),
               # the calculation's and the mesher's child find their targets by name
               "--hidden-import", "ogr_fem2d.api.worker",
               "--collect-submodules", "ogr_fem2d",
               "--collect-submodules", "ogr_core",
               "--collect-data", "ogr_ui", "--collect-data", "qtawesome",
               "--distpath", str(WORK / "dist"), "--workpath", str(WORK / "work"),
               "--specpath", str(WORK),
               *data, str(ROOT / "poc" / "freeze" / "gui.py")]
    print(" ".join(command))
    t = time.perf_counter()
    done = subprocess.run(command)
    print(f"PyInstaller finished with {done.returncode} in {time.perf_counter() - t:.0f} s")
    return done.returncode


def check_gui() -> int:
    program = executable(GUI_NAME)
    if not program.exists():
        print(f"no executable at {program}: build it first")
        return 1
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
    env["QT_QPA_PLATFORM"] = "offscreen"
    with tempfile.TemporaryDirectory() as outside:
        report = Path(outside) / "self-test.txt"
        t = time.perf_counter()
        done = subprocess.run([str(program), "--self-test", str(report)], cwd=outside, env=env,
                              capture_output=True, text=True, timeout=900)
        elapsed = time.perf_counter() - t
        said = report.read_text(encoding="utf-8") if report.exists() else "(no report)\n"
    print(said, end="")
    if done.stdout or done.stderr:
        print((done.stdout or "") + (done.stderr or ""), end="", file=sys.stderr)
    lines = said.splitlines()
    ok = (done.returncode == 0 and bool(lines) and lines[-1] == "SELF-TEST PASSES"
          and ", frozen" in lines[0])
    size = sum(f.stat().st_size for f in program.parent.rglob("*") if f.is_file())
    print(f"executable {program.name}: exit {done.returncode} in {elapsed:.1f} s, "
          f"folder {size / 2 ** 20:.0f} MB -> {'FROZEN PROGRAM OK' if ok else 'FAILS'}")
    return 0 if ok else 1


def build() -> int:
    data = []
    for case in CASES:
        source = ROOT / "validacion" / "casos" / case / "esperado.json"
        data += ["--add-data", f"{source}{os.pathsep}casos/{case}"]
    data += ["--add-data",
             f"{CLOSED_FORMS / 'soluciones_cerradas.py'}{os.pathsep}comprobaciones_002"]
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
               "--name", NAME, "--console",
               "--paths", str(ROOT), "--paths", str(ROOT / "tests"),
               "--distpath", str(WORK / "dist"), "--workpath", str(WORK / "work"),
               "--specpath", str(WORK),
               *data, str(ROOT / "poc" / "freeze" / "casos.py")]
    print(" ".join(command))
    t = time.perf_counter()
    done = subprocess.run(command)
    print(f"PyInstaller finished with {done.returncode} in {time.perf_counter() - t:.0f} s")
    return done.returncode


def check() -> int:
    program = executable()
    if not program.exists():
        print(f"no executable at {program}: build it first")
        return 1
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
    with tempfile.TemporaryDirectory() as outside:
        t = time.perf_counter()
        done = subprocess.run([str(program)], cwd=outside, env=env,
                              capture_output=True, text=True)
        elapsed = time.perf_counter() - t
    print(done.stdout, end="")
    if done.stderr:
        print(done.stderr, end="", file=sys.stderr)
    engine = next((line.split("engine: ", 1)[1] for line in done.stdout.splitlines()
                   if line.startswith("engine: ")), "")
    inside = bool(engine) and program.parent.resolve() in Path(engine).resolve().parents
    if not inside:
        print(f"the engine it loaded, {engine or '(none)'}, is not the one inside the program")
    ok = (done.returncode == 0 and ", frozen;" in done.stdout and inside
          and f"ALL {len(CASES)} CASES PASS" in done.stdout)
    size = sum(f.stat().st_size for f in program.parent.rglob("*") if f.is_file())
    print(f"executable {program.name}: exit {done.returncode} in {elapsed:.1f} s, "
          f"folder {size / 2 ** 20:.0f} MB -> {'FROZEN PROGRAM OK' if ok else 'FAILS'}")
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="only check the last build")
    parser.add_argument("--only", choices=("casos", "gui"), default=None,
                        help="one of the two programs")
    args = parser.parse_args(argv)
    programs = [("casos", build, check), ("gui", build_gui, check_gui)]
    failed = 0
    for name, make, test in programs:
        if args.only not in (None, name):
            continue
        code = 0 if args.check else make()
        failed |= code or test()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
