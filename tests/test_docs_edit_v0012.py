# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.12 (spec 006, T9) — the example of ``docs/modelo/edicion.md`` runs.

Invariant protected: **the script the documentation shows builds a model
that is valid and goes to the engine**, so the page cannot drift from the
code. (Writing it found that a graded mesh has no default number of nodes:
spec 003 decided none, and the example sets it.)
"""
from __future__ import annotations

import re
from pathlib import Path

from ogr_fem2d.model import model as md
from ogr_fem2d.model import translate

DOC = Path(__file__).resolve().parents[1] / "docs" / "modelo" / "edicion.md"


class TestTheExample:
    def test_it_runs(self):
        code = re.search(r"```python\n(.*?)```", DOC.read_text(encoding="utf-8"), re.S).group(1)
        space: dict = {}
        exec(compile(code, str(DOC), "exec"), space)
        m = space["m"]
        assert md.problems(m) == [] and m.mesh is not None
        assert len(translate.to_engine(m).elements) == len(m.mesh.elements)
