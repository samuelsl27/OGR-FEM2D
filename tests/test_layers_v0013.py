# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.13 (spec 006, plan «Capas») — what each layer may import.

Invariants protected, in a fresh interpreter (``sys.modules`` is what
counts, not what the code text says):

* **the operations and the command line import neither Qt nor the MCP SDK**
  (``tech-stack.md``, «Separaciones»: operations and transport apart): the
  command line, a script and a test use them without either installed;
* **the engine imports nothing of the model, the results, the operations or
  the interface** (rule 11: the engine does not know the interface).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _loaded(module: str) -> set:
    code = ("import json, sys; import " + module + "; "
            "print(json.dumps(sorted(m.split('.')[0] + ('.' + m.split('.')[1] if m.startswith("
            "'ogr_fem2d.') and m.count('.') else '') for m in sys.modules)))")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         cwd=ROOT, env=env, timeout=120)
    assert out.returncode == 0, out.stderr
    return set(json.loads(out.stdout))


class TestLayers:
    def test_operations_and_command_line_without_qt_or_mcp(self):
        for module in ("ogr_fem2d.api", "ogr_fem2d.cli.__main__"):
            got = _loaded(module)
            assert not got & {"PySide6", "mcp", "ogr_ui", "ogr_fem2d.gui", "ogr_fem2d.mcp"}, \
                (module, got & {"PySide6", "mcp", "ogr_ui", "ogr_fem2d.gui", "ogr_fem2d.mcp"})

    def test_the_engine_knows_no_interface(self):
        got = _loaded("ogr_fem2d.engine.analysis")
        assert not got & {"ogr_fem2d.model", "ogr_fem2d.results", "ogr_fem2d.api",
                          "ogr_fem2d.gui", "ogr_fem2d.mcp", "PySide6"}, got
