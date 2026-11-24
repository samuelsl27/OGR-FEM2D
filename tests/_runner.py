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
installed from the tag ``pyproject.toml`` pins, as in CI. Another Python may
give ``ogr_core`` from somewhere else, at another version, or nothing. This
runner refuses anything that is not the pinned version.

``ogr_fem2d`` is this repository's own package and must resolve inside it.
``ogr_core`` is shared: it comes from the ``ogr-core`` distribution, pinned in
``pyproject.toml``, and the runner names its tree and version on every run
and refuses any other version.

Against a core that is being changed (a ``X.Y.Z.devN`` of a later release),
from the core's tree or worktree, without installing anything::

    PYTHONPATH=<OGR-Core tree> .venv/Scripts/python tests/_runner.py --dev-core

Such a run says ``DEV CORE`` before and after its totals, and is not
evidence for a release of this program.
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
    # that distribution (a copy of the core older than it, say).
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


from ogr_core.testing import leaks  # noqa: E402

#: The folder every run gets, empty and of its own: the saved preferences
#: of the interface (ogr_ui.user_prefs reads OGR_SETTINGS_DIR) and the
#: bridge's discovery files (OGR_BRIDGE_DIR).
RUN_FOLDERS = {"OGR_SETTINGS_DIR": "settings", "OGR_BRIDGE_DIR": "bridge"}

#: This repository's part of the leak check's allow-list (the suite's own
#: is in ``ogr_core.testing.leaks.ALLOWED``): the entries of OGR-GUI's own
#: runner for the pieces of ``ogr_ui`` (spec 006, T19). Every one says why.
ALLOWED = (
    leaks.Allow("mod:*.icon", leaks.ANY,
                "ogr_ui.resources.icons.icon, an lru_cache of icons, under every module "
                "that imports it; a change of theme empties it on purpose"),
    leaks.Allow("mod:ogr_ui.gc_guard._kept", leaks.ANY,
                "garbage the collector found on another thread, waiting to be freed on the "
                "main one: the runner frees it before every file"),
    leaks.Allow("mod:ogr_ui.wheel_guard._guard", leaks.INSTALLED,
                "the wheel guard, installed once in the application by the first window"),
    leaks.Allow("mod:ogr_ui.button_floor._floor", leaks.INSTALLED,
                "the button floor, installed in the application by the first theme applied"),
    leaks.Allow("mod:ogr_ui.themes._ORIGINAL_PALETTE", leaks.INSTALLED,
                "the application's palette, captured the first time a theme is applied, to "
                "go back to"),
    leaks.Allow("mpl.rcParams", leaks.from_value("[]", to="['backend_fallback']"),
                "matplotlib.use(), which ogr_ui.xy_chart calls before its first chart, sets "
                "backend_fallback to False; only that key, and only from a clean rcParams"),
)


def _install_gc_guard() -> None:
    # cyclic garbage found on a worker thread is held for the main thread
    # (ogr_ui/gc_guard.py, OGR Slip2D D310). Installed at the start of every
    # run (it imports no Qt, and installing it twice does nothing): installed
    # only when Qt was already loaded, a run inside a test (test_project_setup
    # drives one) put it in after the outer run had looked, and the outer one
    # counted it as a leak of that file.
    from ogr_ui import gc_guard
    gc_guard.install()


def _release_garbage() -> None:
    from ogr_ui import gc_guard
    gc_guard.release()


def _release_windows() -> int:
    """Delete the windows with no parent the tests left alive, before the
    interpreter's shutdown (OGR Slip2D D370: at shutdown PySide deletes
    every wrapped object in no order a window's children can rely on)."""
    if "PySide6.QtWidgets" not in sys.modules:
        return 0
    import shiboken6
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return 0
    released = 0
    for window in [w for w in app.topLevelWidgets() if w.parent() is None]:
        if shiboken6.isValid(window):
            shiboken6.delete(window)
            released += 1
    return released


HOOKS = runner.Hooks(before_run=_install_gc_guard, before_file=_release_garbage,
                     after_run=_release_windows)


def pinned() -> dict:
    """``{"ogr_core": version}`` as ``pyproject.toml`` pins it."""
    version = runner.pinned_from_pyproject(_ROOT / "pyproject.toml", "ogr-core")
    return {"ogr_core": version} if version else {}


def config() -> dict:
    return {"own": OWN, "shared": SHARED, "pinned": pinned(), "hooks": HOOKS,
            "allowed": ALLOWED, "run_folders": RUN_FOLDERS}


def main(patterns=(), k=None, list_only=False) -> int:
    """This repository's run, for a test that wants to drive it."""
    return runner.main(_TESTS, patterns, k, list_only, **config())


if __name__ == "__main__":
    if not pinned():
        print("pyproject.toml does not pin ogr-core to a tag or an exact "
              "version: nothing to check the shared core against.")
        sys.exit(2)
    sys.exit(runner.cli(_TESTS, **config()))
