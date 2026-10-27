# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Freeze poc/freeze/casos.py with PyInstaller and check the executable
(spec 001, RF-10, task T15; ADR-0001, criterion 3, second part).

    .venv/Scripts/python poc/freeze/build.py           # build and check
    .venv/Scripts/python poc/freeze/build.py --check   # check the last build

The build needs the compiled engine (ogr_fem2d._engine: maturin develop, or
the wheel installed) and PyInstaller, which is only a tool of the project's
environment (spec 001, D6). It goes to build/freeze/ (ignored by git); the
program, to build/freeze/dist/ogr-fem2d-casos/ (one folder, PyInstaller's
default), with the esperado.json of both validation cases inside.

The check runs the executable from a temporary folder OUTSIDE the source
tree, with PYTHONPATH and PYTHONHOME removed, so it cannot fall back on the
sources or on an installed Python: it must say it is frozen, solve both
cases within their tolerances with the compiled engine that travels inside
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
CASES = ("001-kirsch-hueco-elastico", "002-salencon-hueco-mohr-coulomb")


def executable() -> Path:
    suffix = ".exe" if sys.platform == "win32" else ""
    return WORK / "dist" / NAME / f"{NAME}{suffix}"


def build() -> int:
    data = []
    for case in CASES:
        source = ROOT / "validacion" / "casos" / case / "esperado.json"
        data += ["--add-data", f"{source}{os.pathsep}casos/{case}"]
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
               "--name", NAME, "--console",
               "--paths", str(ROOT),
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
          and "BOTH CASES PASS" in done.stdout)
    size = sum(f.stat().st_size for f in program.parent.rglob("*") if f.is_file())
    print(f"executable {program.name}: exit {done.returncode} in {elapsed:.1f} s, "
          f"folder {size / 2 ** 20:.0f} MB -> {'FROZEN PROGRAM OK' if ok else 'FAILS'}")
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="only check the last build")
    args = parser.parse_args(argv)
    if not args.check:
        code = build()
        if code:
            return code
    return check()


if __name__ == "__main__":
    sys.exit(main())
