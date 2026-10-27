# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.1 (spec 001, T3) — the repository measures the tree it says, against the
core it pins, and says one version.

Invariants protected:

* **the trees**: ``ogr_fem2d`` resolves inside this repository; ``ogr_core``
  resolves to the ``ogr-core`` distribution at the version ``pyproject.toml``
  pins (``v0.1.0``), so a run can never measure OGR Slip2D's own copy of the
  core, which has the same package name (ADR-0002, modification);
* **the pin is a pin**: a git tag reference, read as the version it names;
* **one version**: ``pyproject.toml`` and ``ogr_fem2d.__version__`` agree,
  and that version has its changelog (rule of the suite: every version
  records what was found);
* **licence headers**: every Python file carries the SPDX identifier and the
  copyright line near its top (rule 4).
"""
from __future__ import annotations

import contextlib
import glob
import io
import re
import tomllib
from pathlib import Path

import _runner

_ROOT = Path(__file__).resolve().parent.parent
_SPDX = "SPDX-License-Identifier: AGPL-3.0-or-later"


class TestTheTrees:
    def test_the_own_package_is_this_tree(self):
        origins = _runner.runner.package_origins(_runner.OWN)
        assert origins["ogr_fem2d"] == _ROOT / "ogr_fem2d", origins
        assert _runner.runner.foreign_packages(origins, _ROOT) == []

    def test_the_core_is_the_pinned_distribution(self):
        origins = _runner.runner.package_origins(_runner.SHARED)
        where = origins["ogr_core"]
        assert where is not None, "ogr_core is not importable"
        # Not this repository's, and not OGR Slip2D's tree.
        assert not str(where).startswith(str(_ROOT / "ogr_core")), where
        assert "OGR-Slip2D" not in str(where), where
        assert _runner.runner.shared_problems(origins, _runner.pinned()) == []

    def test_the_pin_is_read_from_pyproject(self):
        assert _runner.pinned() == {"ogr_core": "0.1.0"}

    def test_the_banner_names_both_trees(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = _runner.main(patterns=["no-such-file-anywhere"])
        text = buf.getvalue()
        assert code == 2, text            # nothing selected: nothing run
        assert f"tree: {_ROOT}" in text, text
        assert "shared: ogr_core 0.1.0" in text, text


class TestOneVersion:
    def _version(self) -> str:
        return tomllib.loads((_ROOT / "pyproject.toml").read_text(
            encoding="utf-8"))["project"]["version"]

    def test_pyproject_and_package_agree(self):
        src = (_ROOT / "ogr_fem2d" / "__init__.py").read_text(encoding="utf-8")
        m = re.search(r'^__version__\s*=\s*"([^"]+)"', src, re.MULTILINE)
        assert m and m.group(1) == self._version(), (m and m.group(1))

    def test_the_changelog_of_this_version_exists(self):
        path = _ROOT / "docs" / "changelog" / f"CHANGELOG_v{self._version()}.md"
        assert path.exists(), path


class TestLicenceHeaders:
    def _sources(self):
        for f in glob.glob(str(_ROOT / "**" / "*.py"), recursive=True):
            p = Path(f)
            if {"__pycache__", ".venv", "target"} & set(p.parts):
                continue
            yield p

    def test_every_source_file_has_the_spdx_line_near_the_top(self):
        missing = [str(p.relative_to(_ROOT)) for p in self._sources()
                   if not any(_SPDX in ln for ln in
                              p.read_text(encoding="utf-8").split("\n")[:6])]
        assert not missing, missing

    def test_every_source_file_has_the_copyright_line(self):
        missing = [str(p.relative_to(_ROOT)) for p in self._sources()
                   if "Copyright (C) 2026 Samuel Sáez López"
                   not in p.read_text(encoding="utf-8")]
        assert not missing, missing

    def test_the_census_looked_at_something(self):
        names = {p.name for p in self._sources()}
        assert {"__init__.py", "_runner.py"} <= names, names
