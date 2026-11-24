# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The command line of OGR FEM2D (spec 006, T15; RF-6): the operations of
``ogr_fem2d.api``, from a terminal or a script, without Qt.

    python -m ogr_fem2d.cli info modelo.ogrfem2d
    python -m ogr_fem2d.cli calculate modelo.ogrfem2d
    python -m ogr_fem2d.cli call results_query --open modelo.ogrfem2d \\
        --json '{"quantity": "sigma_1", "kind": "line", "points_xy": [[0, 0], [0, -5]], "n": 20}'
    python -m ogr_fem2d.cli run pasos.json

* ``call OP``: one operation, its arguments as ``--json`` (an object) and
  ``--arg name=value`` (a value read as JSON when it is JSON, as text
  otherwise); ``--open FILE`` opens a model first, so ``project_id`` may be
  left out;
* ``run FILE``: the operations of a JSON list ``[{"op": …, "kwargs": {…}}]``,
  one after the other on one workspace; what each answers, in a list;
* ``info FILE``: the report of the model and its results, as text;
* ``calculate FILE``: open, calculate in a child process, wait, and the
  job's state.

The answers are JSON on the standard output. An error of an operation is
JSON on the standard error, ``{"error": {"code": …, "message": …}}``, with
exit status 2; any other failure, status 1. Relative paths mean
``--workdir`` (the current folder by default).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ogr_core.api import OgrApiError

from .. import api


def _value(text: str):
    try:
        return json.loads(text)
    except ValueError:
        return text


def _kwargs(ns) -> dict:
    out = {}
    if ns.json:
        given = json.loads(ns.json)
        if not isinstance(given, dict):
            raise SystemExit("--json must be a JSON object")
        out.update(given)
    for item in ns.arg or ():
        if "=" not in item:
            raise SystemExit(f"--arg {item!r}: name=value")
        k, v = item.split("=", 1)
        out[k] = _value(v)
    return out


def _print(value) -> None:
    sys.stdout.write(json.dumps(value, ensure_ascii=False, default=str) + "\n")


def _workspace(ns):
    return api.workspace(workdir=Path(ns.workdir).resolve())


def cmd_call(ns) -> int:
    ws = _workspace(ns)
    try:
        if ns.open:
            api.call(ws, "project_open", path=ns.open)
        _print(api.call(ws, ns.op, **_kwargs(ns)))
    finally:
        ws.shutdown()
    return 0


def run_steps(ws, steps) -> list:
    """What each step of ``steps`` answers, in order."""
    if not isinstance(steps, list):
        raise SystemExit("the steps must be a JSON list of {\"op\": ..., \"kwargs\": {...}}")
    out = []
    for k, step in enumerate(steps):
        if not isinstance(step, dict) or "op" not in step or set(step) - {"op", "kwargs"}:
            raise SystemExit(f"step {k}: {{\"op\": ..., \"kwargs\": {{...}}}}")
        out.append(api.call(ws, step["op"], **(step.get("kwargs") or {})))
    return out


def cmd_run(ns) -> int:
    steps = json.loads(Path(ns.file).read_text(encoding="utf-8"))
    ws = _workspace(ns)
    try:
        _print(run_steps(ws, steps))
    finally:
        ws.shutdown()
    return 0


def cmd_info(ns) -> int:
    ws = _workspace(ns)
    try:
        pid = api.call(ws, "project_open", path=ns.file)["project_id"]
        sys.stdout.write(api.call(ws, "results_report", project_id=pid)["report"])
    finally:
        ws.shutdown()
    return 0


def cmd_calculate(ns) -> int:
    ws = _workspace(ns)
    try:
        pid = api.call(ws, "project_open", path=ns.file)["project_id"]
        _print(api.call(ws, "analysis_run", project_id=pid, variant=ns.variant,
                        wait=float(ns.timeout)))
    finally:
        ws.shutdown()
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ogr-fem2d", description="OGR FEM2D, the operations of a "
                                "model from the command line (JSON in, JSON out).")
    p.add_argument("--workdir", default=".", help="the folder relative paths mean")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("call", help="one operation")
    c.add_argument("op")
    c.add_argument("--open", help="a model to open first")
    c.add_argument("--json", help="the arguments, as a JSON object")
    c.add_argument("--arg", action="append", help="one argument, name=value")
    c.set_defaults(fn=cmd_call)
    r = sub.add_parser("run", help="the operations of a JSON list, in order")
    r.add_argument("file")
    r.set_defaults(fn=cmd_run)
    i = sub.add_parser("info", help="the report of a model and its results")
    i.add_argument("file")
    i.set_defaults(fn=cmd_info)
    k = sub.add_parser("calculate", help="calculate a model and wait")
    k.add_argument("file")
    k.add_argument("--variant", default="reference", choices=("reference", "rust"))
    k.add_argument("--timeout", default="3600", help="seconds to wait")
    k.set_defaults(fn=cmd_calculate)
    return p


def main(argv=None) -> int:
    ns = parser().parse_args(argv)
    try:
        return ns.fn(ns)
    except OgrApiError as err:
        sys.stderr.write(json.dumps({"error": err.to_dict()}, ensure_ascii=False, default=str)
                         + "\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
