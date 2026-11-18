# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The test runner of OGR FEM2D: the suite's runner (``ogr_core.testing.runner``),
pointed at this repository.

    python tests/_runner.py            # everything; what CI runs
    python tests/_runner.py t6         # files whose name contains it
    python tests/_runner.py -k patch   # tests whose name contains it
    python tests/_runner.py --list     # show the selection, run nothing

Run it with the project's environment (``.venv``), where ``ogr-core`` is
installed at the version ``pyproject.toml`` pins. Another Python may give
``ogr_core`` from somewhere else, or nothing: what the system Python gives
depends on what OGR Slip2D, installed there in editable mode, has checked
out (its own copy of the core, while its ``main`` carries one; nothing, on
its branch that adopts ``ogr-core``). This runner refuses anything that is
not the pinned distribution.

``ogr_fem2d`` is this repository's own package and must resolve inside it.
``ogr_core`` is shared: it comes from the ``ogr-core`` distribution, pinned in
``pyproject.toml``, and the runner names its tree and version on every run
and refuses any other version.
"""
from __future__ import annotations

import sys
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
_ROOT = _TESTS.parent
# This tree first, before any editable install can answer for it (see
# foreign_packages in the runner).
sys.path.insert(0, str(_ROOT))

try:
    from ogr_core.testing import runner  # noqa: E402
except ImportError:
    # The runner lives in the core since ogr-core 0.1.0. Without it, either
    # nothing answers for ogr_core in this Python, or what answers is not
    # that distribution (OGR Slip2D's own copy, say).
    import importlib.util
    _spec = importlib.util.find_spec("ogr_core")
    # ASCII only: this prints before the runner widens the console encoding.
    print("WRONG SHARED TREE - ogr_core resolves to "
          f"{_spec.origin if _spec else '(nothing)'}, which is not the "
          "ogr-core distribution this repository pins (no "
          "ogr_core.testing there). Run with the project's environment: "
          ".venv/Scripts/python tests/_runner.py")
    sys.exit(2)

#: The packages this repository contains, and the one it takes from the core.
OWN = ("ogr_fem2d",)
SHARED = ("ogr_core",)


def pinned() -> dict:
    """``{"ogr_core": version}`` as ``pyproject.toml`` pins it."""
    version = runner.pinned_from_pyproject(_ROOT / "pyproject.toml", "ogr-core")
    return {"ogr_core": version} if version else {}


def config() -> dict:
    return {"own": OWN, "shared": SHARED, "pinned": pinned()}


def main(patterns=(), k=None, list_only=False) -> int:
    """This repository's run, for a test that wants to drive it."""
    return runner.main(_TESTS, patterns, k, list_only, **config())


if __name__ == "__main__":
    if not pinned():
        print("pyproject.toml does not pin ogr-core to a tag or an exact "
              "version: nothing to check the shared core against.")
        sys.exit(2)
    sys.exit(runner.cli(_TESTS, **config()))
