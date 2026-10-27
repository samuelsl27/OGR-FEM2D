# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The variants of the engine the tests run (spec 001, RF-3), and the ones they
must find (not a test file: the runner only collects test_*.py).

EXPECTED is the list the repository promises at this point of spec 001: a
variant that should be there and is not importable fails the tests that use
it, instead of being skipped in silence. The Rust one is the compiled module
``ogr_fem2d._engine``, built into the project's environment with
``maturin develop``.
"""
from __future__ import annotations

from ogr_fem2d.engine.reference import solver

#: Variants the repository provides now (tasks.md: T10 reference, T11 NumPy,
#: T12 Rust).
EXPECTED = ("reference", "numpy", "rust")


def available() -> dict:
    """name -> variant, for every variant that imports."""
    out = {"reference": solver.REFERENCE}
    try:
        from poc.vectorized import NUMPY
        out["numpy"] = NUMPY
    except ImportError:
        pass
    try:
        from ogr_fem2d.engine.compiled import RUST
        out["rust"] = RUST
    except ImportError:
        pass
    return out
