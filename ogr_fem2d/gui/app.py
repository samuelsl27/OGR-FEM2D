# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Starting the interface (spec 006, T20): the application, the theme and the
language kept on this machine, the guards of the suite, and the window.

    python -m ogr_fem2d            # the window
    python -m ogr_fem2d modelo.ogrfem2d

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import sys


def application():
    """The QApplication, made once, with the language and the theme saved
    (light and the system's language the first time)."""
    from PySide6.QtWidgets import QApplication
    from ogr_ui import button_floor, qt_catalog, wheel_guard
    from ogr_ui.i18n import available_languages, set_language
    from ogr_ui.themes import apply_theme

    from .main_window import PREFERENCES
    app = QApplication.instance() or QApplication(sys.argv[:1])
    lang = PREFERENCES.saved_language()
    if lang in available_languages():
        set_language(lang)
        qt_catalog.install_qt_translator(app, lang)   # Qt's own Yes, No, Save
    apply_theme(app, PREFERENCES.saved_theme() or "light")
    wheel_guard.install(app)
    button_floor.install(app)
    return app


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    app = application()
    from .main_window import MainWindow
    window = MainWindow()
    if argv:
        window.open_path(argv[0])
    window.show()
    return app.exec()
