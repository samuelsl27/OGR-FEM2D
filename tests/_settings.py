# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What a test of the window keeps of this machine's settings, put back as it
was (rule 5): the list of recent models (spec 006, T28), which opening or
saving a model through the window changes, and the application's style,
which choosing a theme changes.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from contextlib import contextmanager


@contextmanager
def recent_kept():
    """The recent models as they were before the block."""
    from ogr_fem2d.gui import main_window as mw
    s = mw.PREFERENCES.settings()
    had, value = s.contains(mw.RECENT_KEY), s.value(mw.RECENT_KEY)
    try:
        yield
    finally:
        s = mw.PREFERENCES.settings()
        if had:
            s.setValue(mw.RECENT_KEY, value)
        else:
            s.remove(mw.RECENT_KEY)
        s.sync()


@contextmanager
def style_kept(app):
    """The application's style and style sheet as they were."""
    name, sheet = app.style().name(), app.styleSheet()
    try:
        yield
    finally:
        app.setStyle(name)
        app.setStyleSheet(sheet)
