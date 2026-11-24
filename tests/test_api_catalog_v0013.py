# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.13 (spec 006, T18) — the catalogue of the operations is the code's.

Invariants protected: **``docs/operaciones/catalogo.md`` is what the
registry writes** (``api.catalog.markdown``), every operation in it with its
description and its arguments, so the page cannot fall behind the code; and
**every operation has a description** (it is what an agent reads).
"""
from __future__ import annotations

from pathlib import Path

from ogr_fem2d import api
from ogr_fem2d.api import catalog

DOC = Path(__file__).resolve().parents[1] / "docs" / "operaciones" / "catalogo.md"


class TestTheCatalogue:
    def test_the_page_is_the_codes(self):
        assert DOC.read_text(encoding="utf-8") == catalog.markdown(), \
            "regenerate it: python -c \"from ogr_fem2d.api import catalog; ...\""
        text = DOC.read_text(encoding="utf-8")
        for name, op in api.OPERATIONS.items():
            assert f"### `{name}`" in text and op.func.__doc__, name
