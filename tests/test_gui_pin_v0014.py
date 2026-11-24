# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.14 (spec 006, T19) — the interface pieces are the ones pinned.

Invariant protected: **the ``ogr_ui`` imported is the version
``pyproject.toml`` pins** (``ogr-gui @ git+…@vX.Y.Z``, ADR-0005), installed
in the environment and not a tree of OGR-GUI: raising the pin is a commit of
its own, as with the core, and an environment that did not follow it is
said. And **it does not bring the core with it**: ogr-gui does not depend
on ogr-core (ADR-0005, modified), so this program's pin of the core is the
only one.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _deps() -> list[str]:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "dependencies"]


class TestThePin:
    def test_the_installed_one(self):
        import ogr_ui
        pins = [d for d in _deps() if d.startswith("ogr-gui")]
        assert len(pins) == 1, pins
        tag = re.search(r"@v(\d+\.\d+\.\d+)$", pins[0])
        assert tag, pins[0]
        assert ogr_ui.__version__ == tag.group(1), (ogr_ui.__version__, pins[0])
        assert "site-packages" in Path(ogr_ui.__file__).parts, ogr_ui.__file__

    def test_ogr_gui_asks_for_no_core(self):
        from importlib.metadata import requires
        assert not [r for r in requires("ogr-gui") or () if r.lower().startswith("ogr-core")
                    and "extra" not in r]
