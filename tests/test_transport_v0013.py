# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.13 (spec 006, T17) — the same operations by every transport, and the
cases by the operations (RF-6, RF-22; D13).

Invariants protected:

* **identity of transport**: one list of steps that draws a model from
  nothing (two strata cut by a material boundary, gravity, rollers, a
  surface load), meshes it, saves it and calculates it, given in Python
  (``api.call``), to the command line in another process and to the MCP
  server, gives the same model (fingerprint of the file) and the same
  results (every field of every stage of the ``.h5``, bit for bit);
* **the cases 005, 006 and 007 by the operations**: opened, calculated in
  the child process and queried as their ``esperado.json`` says, give bit
  for bit what spec 005 gives in the test's own process — the same results
  file, field by field, and the same rows of every query. That path is the
  one ``test_validation_queries_v0011.py`` checks against Kirsch, Michell
  and Lamé within the tolerances fixed before measuring: so these are within
  them too, by the same numbers.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import _cases_model as cm
from ogr_fem2d import api
from ogr_fem2d.cli.__main__ import run_steps
from ogr_fem2d.model import fingerprint, ogr_file
from ogr_fem2d.results import calculate as calc
from ogr_fem2d.results import queries as qy

ROOT = Path(__file__).resolve().parents[1]
HAVE_MCP = importlib.util.find_spec("mcp") is not None

STEPS = [
    {"op": "project_new", "kwargs": {"name": "Dos estratos"}},
    {"op": "boundary_add", "kwargs": {"type": "external", "boundary": "ext",
                                      "points_xy": [[0, -10], [20, -10], [20, 0], [0, 0]]}},
    {"op": "boundary_add", "kwargs": {"type": "material", "points_xy": [[0, -4], [20, -4]]}},
    {"op": "material_set", "kwargs": {"name": "Arcilla", "E": 3.0e4, "nu": 0.3,
                                      "unit_weight": 18.0,
                                      "initial_loading": "field_stress_and_body_force"}},
    {"op": "material_set", "kwargs": {"name": "Roca", "E": 2.0e6, "nu": 0.25,
                                      "unit_weight": 24.0,
                                      "initial_loading": "field_stress_and_body_force"}},
    {"op": "material_assign", "kwargs": {"material": "m1", "x": 10, "y": -2}},
    {"op": "material_assign", "kwargs": {"material": "m2", "x": 10, "y": -7}},
    {"op": "field_set", "kwargs": {"kind": "gravity", "surface": 0.0, "strata": [
        {"bottom": -4.0, "unit_weight": 18.0, "k": 0.6, "kz": 0.7},
        {"bottom": -11.0, "unit_weight": 24.0, "k": 0.5, "kz": 0.45}]}},
    {"op": "condition_set", "kwargs": {"kind": "free", "boundary": "ext",
                                       "start": [20, 0], "end": [0, 0]}},
    {"op": "condition_set", "kwargs": {"kind": "x", "boundary": "ext",
                                       "start": [20, -10], "end": [20, -4]}},
    {"op": "condition_set", "kwargs": {"kind": "x", "boundary": "ext",
                                       "start": [20, -4], "end": [20, 0]}},
    {"op": "condition_set", "kwargs": {"kind": "x", "boundary": "ext",
                                       "start": [0, 0], "end": [0, -4]}},
    {"op": "condition_set", "kwargs": {"kind": "x", "boundary": "ext",
                                       "start": [0, -4], "end": [0, -10]}},
    {"op": "load_set", "kwargs": {"kind": "distributed", "boundary": "ext",
                                  "start": [20, 0], "end": [0, 0], "magnitude": 100.0}},
    {"op": "mesh_settings", "kwargs": {"boundary_nodes": 40}},
    {"op": "mesh_generate", "kwargs": {}},
    {"op": "project_save", "kwargs": {"path": "modelo"}},
    {"op": "analysis_run", "kwargs": {"wait": 120}},
]


def _outcomes(path: Path) -> list:
    r = calc.open_results(path).results
    return [r.outcome(k) for k in range(r.n_stages)]


def _python(d: Path) -> list:
    ws = api.workspace(workdir=d)
    try:
        return run_steps(ws, STEPS)
    finally:
        ws.shutdown()


def _cli(d: Path) -> list:
    (d / "pasos.json").write_text(json.dumps(STEPS), encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    out = subprocess.run([sys.executable, "-m", "ogr_fem2d.cli", "--workdir", str(d), "run",
                          "pasos.json"], capture_output=True, text=True, encoding="utf-8",
                         cwd=d, env=env, timeout=600)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _mcp(d: Path) -> list:
    import anyio
    from mcp import Client
    from ogr_core.testing.leaks import root_logging_kept
    from ogr_fem2d.mcp.server import build_server
    ws = api.workspace(workdir=d)
    try:
        with root_logging_kept():
            srv = build_server(ws)

            async def go():
                answers = []
                async with Client(srv) as c:
                    for step in STEPS:
                        r = await c.call_tool(step["op"], step["kwargs"])
                        assert not r.is_error, (step, r.content[0].text)
                        answers.append(json.loads(r.content[0].text))
                return answers
            return anyio.run(go)
    finally:
        ws.shutdown()


class TestIdentityOfTransport:
    def test_python_command_line_and_mcp(self):
        transports = [("python", _python), ("cli", _cli)] + ([("mcp", _mcp)] if HAVE_MCP else [])
        got = {}
        with tempfile.TemporaryDirectory() as root:
            for name, run in transports:
                d = Path(root) / name
                d.mkdir()
                answers = run(d)
                assert answers[-1]["summary"]["status"] == "complete", (name, answers[-1])
                path = d / "modelo.ogrfem2d"
                got[name] = (fingerprint.model_fingerprint(ogr_file.read(path)), _outcomes(path))
        first = got["python"]
        for name, value in got.items():
            assert value[0] == first[0], f"{name}: another model"
            assert value[1] == first[1], f"{name}: other results"
        assert len(got) == len(transports) and len(first[1]) == 1


def _by_ops(ws, pid, stage, query, quantity):
    kw = ({"kind": "line", "points_xy": [query["desde"], query["hasta"]], "n": query["n"]}
          if query["tipo"] == "linea" else
          {"kind": "boundary", "boundary": query["contorno"], "n": query["n_por_segmento"],
           "distance": query["distancia"]})
    rows = api.call(ws, "results_query", project_id=pid, quantity=quantity, stage=stage,
                    **kw)["rows"]
    return [(r["x"], r["y"], r["distance"], r["value"]) for r in rows]


def _direct(view, m, query, quantity):
    if query["tipo"] == "linea":
        rows = qy.line(view, quantity, [query["desde"], query["hasta"]], query["n"]).rows
    else:
        rows = qy.on_boundary(view, quantity, m, query["contorno"], query["n_por_segmento"],
                              query["distancia"]).rows
    return [(r.x, r.y, r.distance, r.value) for r in rows]


def _case_by_the_operations(name: str):
    spec = cm.case(name)["comparaciones_consulta"]
    with tempfile.TemporaryDirectory() as d:
        ops_dir, own_dir = Path(d) / "ops", Path(d) / "own"
        ops_dir.mkdir()
        own_dir.mkdir()
        shutil.copy(cm.path(name), ops_dir / "modelo.ogrfem2d")
        shutil.copy(cm.path(name), own_dir / "modelo.ogrfem2d")
        ws = api.workspace(workdir=ops_dir)
        try:
            pid = api.call(ws, "project_open", path="modelo.ogrfem2d")["project_id"]
            run = api.call(ws, "analysis_run", project_id=pid, wait=900)
            assert run["summary"]["status"] == "complete", run
            m = ogr_file.read(own_dir / "modelo.ogrfem2d")
            # the same engine as the operation's, its default (the compiled one since 2026-11-28)
            from ogr_fem2d.api import worker
            from ogr_fem2d.api.ops.analysis import DEFAULT_VARIANT
            calc.calculate(m, own_dir / "modelo.ogrfem2d", worker.variant(DEFAULT_VARIANT))
            assert _outcomes(ops_dir / "modelo.ogrfem2d") == _outcomes(own_dir / "modelo.ogrfem2d")
            view = qy.View(calc.open_results(own_dir / "modelo.ogrfem2d").results, spec["fase"])
            stage = api.call(ws, "results_open", project_id=pid)["stages"][spec["fase"]]["id"]
            compared = 0
            for query in spec["consultas"]:
                for mq in query["magnitudes"]:
                    ours = _by_ops(ws, pid, stage, query, mq["magnitud"])
                    assert ours and ours == _direct(view, m, query, mq["magnitud"]),                         (name, query["tipo"], mq["magnitud"])
                    compared += 1
            assert compared == sum(len(q["magnitudes"]) for q in spec["consultas"])
        finally:
            ws.shutdown()


class TestTheCasesByTheOperations:
    def test_005(self):
        _case_by_the_operations("005-kirsch-malla-general")

    def test_006(self):
        _case_by_the_operations("006-carga-en-faja-malla-general")

    def test_007(self):
        _case_by_the_operations("007-cavidad-esferica-malla-general")
