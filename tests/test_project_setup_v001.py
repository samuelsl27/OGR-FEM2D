# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.1 (spec 001, T3) — the repository measures the tree it says, against the
core it pins, and says one version.

Invariants protected:

* **the trees**: ``ogr_fem2d`` resolves inside this repository; ``ogr_core``
  resolves outside it, to a core that is not a copy in this tree nor OGR
  Slip2D's old one (ADR-0002); and a Python where nothing answers for
  ``ogr_core`` is refused with the reason, not with a traceback (v0.0.3);
* **the run measures the core its runner was held to** (v0.0.4): in an
  ordinary run that is exactly the pinned version (``v0.2.13`` since v0.0.15),
  and anything else fails, a ``.devN`` too; in a run with ``--dev-core``
  (which says so in ``OGR_DEV_CORE=1``, ``runner.dev_core_run()``) it is
  the development version of a later release that the run accepted, and
  nothing else: not an older core, not a candidate, not another release.
  The banner names the core imported, whichever run it is. The Python
  without a core is refused in both kinds of run: it starts without the
  run's ``PYTHONPATH``, which in a development run is what brings the core
  in, and with and without the variable. Until v0.0.4 these tests compared
  with the pin in every run, so the run of the suite that a change of the
  core asks for could only end red (three failures by construction);
* **the pin is a pin**: a git tag reference, read as the version it names;
* **one version**: ``pyproject.toml`` and ``ogr_fem2d.__version__`` agree,
  and that version has its changelog (rule of the suite: every version
  records what was found);
* **licence headers**: every Python file carries the SPDX identifier and the
  copyright line near its top (rule 4), those in hidden folders too: the
  ones with code are declared and walked, the others are declared with their
  reason, and a hidden folder with a ``.py`` in neither list fails (v0.0.5).
"""
from __future__ import annotations

import contextlib
import glob
import io
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

import _runner

_ROOT = Path(__file__).resolve().parent.parent
_SPDX = "SPDX-License-Identifier: AGPL-3.0-or-later"

#: The version ``pyproject.toml`` pins. The version lists of
#: ``TestWhatTheRunIsHeldTo`` are written for it: raising the pin is a
#: commit of its own (AGENTS.md, «Un núcleo y varios programas»), and these
#: lists move with it.
_PIN = "0.2.13"


def _problems(origins: dict, dev: bool) -> list:
    """What the runner of this repository holds the shared core to: against
    the pin, accepting a development version only in a development run.
    The one check both the real core and the made-up ones go through."""
    return _runner.runner.shared_problems(origins, _runner.pinned(),
                                          dev_core=dev)


def _child_env(core_home=None, dev=None) -> dict:
    """The environment of a child Python: this one's, without the run's
    ``PYTHONPATH`` (what brings the core in, in a development run) and
    without its ``OGR_DEV_CORE``, then with the ones given."""
    drop = {"PYTHONPATH", _runner.runner.DEV_CORE_ENV}
    env = {k: v for k, v in os.environ.items() if k.upper() not in drop}
    if core_home is not None:
        homes = core_home if isinstance(core_home, (list, tuple)) else [core_home]
        env["PYTHONPATH"] = os.pathsep.join(str(h) for h in homes)
    if dev is not None:
        env[_runner.runner.DEV_CORE_ENV] = dev
    return env


def _list_in_a_bare_python(env: dict) -> subprocess.CompletedProcess:
    # -S leaves site-packages out, where the .venv has the core installed.
    return subprocess.run([sys.executable, "-S", str(_ROOT / "tests" / "_runner.py"),
                           "--list"], capture_output=True, text=True, cwd=_ROOT,
                          env=env)


class TestTheTrees:
    def test_the_own_package_is_this_tree(self):
        origins = _runner.runner.package_origins(_runner.OWN)
        assert origins["ogr_fem2d"] == _ROOT / "ogr_fem2d", origins
        assert _runner.runner.foreign_packages(origins, _ROOT) == []

    def test_the_core_is_the_one_the_run_was_held_to(self):
        origins = _runner.runner.package_origins(_runner.SHARED)
        where = origins["ogr_core"]
        assert where is not None, "ogr_core is not importable"
        # Not a copy in this repository, and not OGR Slip2D's tree. The core
        # installed in .venv lives under _ROOT, but not under _ROOT/ogr_core.
        assert not str(where).startswith(str(_ROOT / "ogr_core")), where
        assert "OGR-Slip2D" not in str(where), where
        assert _problems(origins, _runner.runner.dev_core_run()) == [], where

    def test_a_python_without_the_core_is_refused(self):
        # In both kinds of run: without the variable, and with it.
        for dev in (None, "1"):
            done = _list_in_a_bare_python(_child_env(dev=dev))
            assert done.returncode == 2, (dev, done.returncode, done.stdout, done.stderr)
            assert "WRONG SHARED TREE - ogr_core resolves to (nothing)" in done.stdout, \
                (dev, done.stdout)
            assert ".venv/Scripts/python tests/_runner.py" in done.stdout, done.stdout

    def test_and_given_back_the_core_of_the_run_it_runs(self):
        # The control of the one above: the same bare Python, given the
        # folder this run's core comes from and this run's variable, runs.
        # So what refuses it there is that the core was taken away.
        # And the folder ogr_ui comes from, after the core's: the runner
        # needs it (its gc guard). In an ordinary run both are site-packages;
        # with --dev-core the core is a tree of OGR-Core, without ogr_ui
        # (OGR-Core's changelog 0.2.13 found it: the child did not start).
        import ogr_ui
        where = _runner.runner.package_origins(_runner.SHARED)["ogr_core"]
        assert where is not None, "ogr_core is not importable"
        homes = [where.parent] + ([] if Path(ogr_ui.__file__).parents[1] == where.parent
                                  else [Path(ogr_ui.__file__).parents[1]])
        done = _list_in_a_bare_python(_child_env(
            core_home=homes, dev=os.environ.get(_runner.runner.DEV_CORE_ENV)))
        assert done.returncode == 0, (done.returncode, done.stdout, done.stderr)
        assert "Nothing was run." in done.stdout, done.stdout

    def test_the_child_starts_without_the_run_s_pythonpath(self):
        saved = {k: os.environ.get(k) for k in ("PYTHONPATH", _runner.runner.DEV_CORE_ENV)}
        try:
            os.environ["PYTHONPATH"] = str(_ROOT / "somewhere")
            os.environ[_runner.runner.DEV_CORE_ENV] = "1"
            env = _child_env()
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        assert "PYTHONPATH" not in env and _runner.runner.DEV_CORE_ENV not in env, env
        assert _child_env(dev="1")[_runner.runner.DEV_CORE_ENV] == "1"

    def test_the_pin_is_read_from_pyproject(self):
        assert _runner.pinned() == {"ogr_core": _PIN}

    def test_the_banner_names_both_trees(self):
        import ogr_core
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = _runner.main(patterns=["no-such-file-anywhere"])
        text = buf.getvalue()
        assert code == 2, text            # nothing selected: nothing run
        assert f"tree: {_ROOT}" in text, text
        # The core it measures: the pinned one in an ordinary run, the one
        # accepted with --dev-core in a development run.
        assert f"shared: ogr_core {ogr_core.__version__} " in text, text


class TestWhatTheRunIsHeldTo:
    """``_problems`` with made-up cores: a folder whose ``ogr_core`` declares
    a version (the runner reads it from the source, never runs it)."""

    def _verdicts(self, versions, dev: bool) -> dict:
        out = {}
        with tempfile.TemporaryDirectory(prefix="ogr_fem2d_pin_") as home:
            for i, version in enumerate(versions):
                pkg = Path(home) / str(i) / "ogr_core"
                pkg.mkdir(parents=True)
                (pkg / "__init__.py").write_text(
                    f'__version__ = "{version}"\n'
                    "raise RuntimeError('this __init__ was executed')\n",
                    encoding="utf-8")
                out[version] = _problems({"ogr_core": pkg}, dev) == []
        return out

    def test_the_versions_are_written_for_the_pin(self):
        assert _runner.pinned() == {"ogr_core": _PIN}

    def test_an_ordinary_run_takes_the_pin_and_nothing_else(self):
        got = self._verdicts(["0.2.13", "0.2.14", "0.2.14.dev0", "0.2.13.dev0", "0.2.12"],
                             dev=False)
        assert got == {"0.2.13": True, "0.2.14": False, "0.2.14.dev0": False,
                       "0.2.13.dev0": False, "0.2.12": False}, got

    def test_a_development_run_takes_a_later_dev_and_the_pin_only(self):
        got = self._verdicts(["0.2.14.dev0", "0.2.13", "0.2.12", "0.2.13.dev0", "0.2.14rc1",
                              "0.2.14+local", "0.2.14"], dev=True)
        assert got == {"0.2.14.dev0": True, "0.2.13": True, "0.2.12": False,
                       "0.2.13.dev0": False, "0.2.14rc1": False, "0.2.14+local": False,
                       "0.2.14": False}, got

    def test_a_core_that_does_not_resolve_fails_in_both(self):
        for dev in (False, True):
            assert _problems({"ogr_core": None}, dev) != [], dev


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


#: Hidden folders (name starting with a dot) that carry code of this program.
#: ``glob("**")`` does not go into them, so the census walks each one itself
#: (v0.0.5: until then ``.github/scripts/wheel_check.py`` was never looked at).
_HIDDEN_WITH_CODE = (".github",)

#: Hidden folders that are not this program's code, each with its reason.
_HIDDEN_NOT_OURS = {
    ".git": "git's own store",
    ".venv": "the environment: installed packages, the core among them",
    ".claude": "the agent's local settings",
}


def _hidden_folders_with_python(root: Path) -> list:
    """Every folder under ``root`` whose name starts with a dot and that
    holds some ``.py`` below it, outside the folders already accounted for.
    Its own walk, not ``glob``: it has to see what ``glob`` does not."""
    found = []
    for here, dirs, files in os.walk(root):
        here = Path(here)
        for d in list(dirs):
            if d in _HIDDEN_NOT_OURS or d == "__pycache__":
                dirs.remove(d)
            elif d.startswith(".") and any(
                    f.endswith(".py") for _, _, fs in os.walk(here / d) for f in fs):
                found.append((here / d).relative_to(root).as_posix())
    return found


class TestLicenceHeaders:
    def _sources(self):
        tops = [_ROOT] + [_ROOT / h for h in _HIDDEN_WITH_CODE]
        for top in tops:
            for f in glob.glob(str(top / "**" / "*.py"), recursive=True):
                p = Path(f)
                if {"__pycache__", ".venv", "target"} & set(p.parts):
                    continue
                yield p

    def test_every_hidden_folder_with_python_is_declared(self):
        found = _hidden_folders_with_python(_ROOT)
        stray = [d for d in found if d not in _HIDDEN_WITH_CODE]
        assert not stray, (f"hidden folders with .py that the census does not see: {stray}; "
                           "add them to _HIDDEN_WITH_CODE or _HIDDEN_NOT_OURS with a reason")

    def test_the_hidden_folder_scan_sees_what_glob_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".tools" / "deep").mkdir(parents=True)
            (root / ".tools" / "deep" / "x.py").write_text("", encoding="utf-8")
            (root / ".empty").mkdir()
            (root / ".git").mkdir()
            (root / ".git" / "hook.py").write_text("", encoding="utf-8")
            assert glob.glob(str(root / "**" / "*.py"), recursive=True) == []
            assert _hidden_folders_with_python(root) == [".tools"]

    def test_the_census_sees_the_hidden_code(self):
        names = {p.relative_to(_ROOT).as_posix() for p in self._sources()}
        assert ".github/scripts/wheel_check.py" in names, sorted(names)

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
