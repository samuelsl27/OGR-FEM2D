# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.13 (spec 006, T15) — the command line (RF-6).

Invariants protected:

* **the command line is the operations**: a list of steps run by it in
  another process answers what the same steps answer here, the numbers of
  a query bit for bit (JSON keeps a float's repr);
* **its commands do what they say**: ``calculate`` writes the results and
  says the job's state; ``info`` writes the report the operation gives;
  ``call`` takes its arguments as JSON and as name=value;
* **an error says its code, and its exit status is 2**.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import _results
from ogr_fem2d import api
from ogr_fem2d.cli.__main__ import run_steps
from ogr_fem2d.model import ogr_file
from ogr_fem2d.results import calculate as calc

ROOT = Path(__file__).resolve().parents[1]
LINE = {"quantity": "sigma_1", "kind": "line", "points_xy": [[2.0, 0.0], [2.0, -10.0]], "n": 7}


def _cli(*args, cwd):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, "-m", "ogr_fem2d.cli", "--workdir", str(cwd), *args],
                          capture_output=True, text=True, encoding="utf-8", cwd=cwd, env=env,
                          timeout=300)


def _saved(d) -> Path:
    path = Path(d) / "modelo.ogrfem2d"
    ogr_file.write(_results.loaded_layers(), path)
    return path


class TestTheOperations:
    def test_the_same_steps_the_same_answers(self):
        steps = [{"op": "project_open", "kwargs": {"path": "modelo.ogrfem2d"}},
                 {"op": "analysis_run", "kwargs": {"wait": 120}},
                 {"op": "results_query", "kwargs": LINE}]
        with tempfile.TemporaryDirectory() as d:
            _saved(d)
            (Path(d) / "pasos.json").write_text(json.dumps(steps), encoding="utf-8")
            out = _cli("run", "pasos.json", cwd=d)
            assert out.returncode == 0, out.stderr
            theirs = json.loads(out.stdout)
        with tempfile.TemporaryDirectory() as d:
            _saved(d)
            ws = api.workspace(workdir=d)
            try:
                ours = run_steps(ws, steps)
            finally:
                ws.shutdown()
        assert theirs[1]["summary"]["status"] == ours[1]["summary"]["status"] == "complete"
        assert theirs[2]["rows"] == json.loads(json.dumps(ours[2]["rows"]))
        assert [r["value"] for r in theirs[2]["rows"]] == [r["value"] for r in ours[2]["rows"]]


class TestTheCommands:
    def test_calculate_info_call(self):
        with tempfile.TemporaryDirectory() as d:
            path = _saved(d)
            out = _cli("calculate", "modelo.ogrfem2d", cwd=d)
            assert out.returncode == 0, out.stderr
            assert json.loads(out.stdout)["summary"]["status"] == "complete"
            assert calc.open_results(path).status == calc.VALID
            out = _cli("info", "modelo.ogrfem2d", cwd=d)
            ws = api.workspace(workdir=d)
            try:
                pid = api.call(ws, "project_open", path="modelo.ogrfem2d")["project_id"]
                assert out.stdout == api.call(ws, "results_report", project_id=pid)["report"]
            finally:
                ws.shutdown()
            out = _cli("call", "results_query", "--open", "modelo.ogrfem2d",
                       "--json", json.dumps({"kind": "line", "n": 7}),
                       "--arg", "quantity=sigma_1",
                       "--arg", "points_xy=" + json.dumps(LINE["points_xy"]), cwd=d)
            assert out.returncode == 0, out.stderr
            got = json.loads(out.stdout)
            assert len(got["rows"]) == 7 and got["state"] == "valid"


class TestErrors:
    def test_code_and_status(self):
        with tempfile.TemporaryDirectory() as d:
            out = _cli("call", "project_nope", cwd=d)
            assert out.returncode == 2 and out.stdout == ""
            err = json.loads(out.stderr)["error"]
            assert err["code"] == "E_NOT_FOUND" and "project_open" in err["hint"]
