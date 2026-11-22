# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The closed forms of spec 003 (comprobaciones/soluciones_cerradas.py), loaded
by their path under a name of their own: specs 001 and 002 have modules of
the same name (tests/_hole.py, tests/_sphere.py), and whichever came first
would take it.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_PATH = (Path(__file__).resolve().parents[1] / "spec" / "features" / "003-malla"
         / "comprobaciones" / "soluciones_cerradas.py")
_NAME = "soluciones_cerradas_003"
if _NAME in sys.modules:
    closed = sys.modules[_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_NAME, _PATH)
    closed = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = closed
    _spec.loader.exec_module(closed)
