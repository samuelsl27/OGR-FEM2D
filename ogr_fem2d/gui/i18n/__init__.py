# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The Spanish of this program's interface (spec 006, D3; rule 2), by area,
added to the suite's ``tr()`` (``ogr_ui.i18n.add_translations``). The
texts of the pieces of ``ogr_ui`` are its own; the key is the English text.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_ui.i18n import add_translations

from .es_menus import ES as _MENUS
from .es_canvas import ES as _CANVAS
from .es_dialogs import ES as _DIALOGS
from .es_messages import ES as _MESSAGES
from .es_report import ES as _REPORT

#: every Spanish text of this program, by area
AREAS = {"menus": _MENUS, "canvas": _CANVAS, "dialogs": _DIALOGS, "messages": _MESSAGES,
         "report": _REPORT}


def spanish() -> dict[str, str]:
    out: dict[str, str] = {}
    for table in AREAS.values():
        out.update(table)
    return out


def install() -> list[str]:
    """Add this program's Spanish to ``tr()``; the keys of ``ogr_ui`` it
    changed (none, normally)."""
    return add_translations("es", spanish())


def say(text) -> str:
    """A message for the reader: a coded one (the operations', the core's:
    ``ogr_core.messages.Coded``) rendered from its code in the reader's
    language, its values put back; a plain one through ``tr()``."""
    from ogr_core.api import API_MESSAGES
    from ogr_core.messages import render
    from ogr_ui.i18n import tr

    from ...api.messages import FEM_MESSAGES
    code = getattr(text, "code", "")
    if not code:
        return tr(str(text))
    return render({**API_MESSAGES, **FEM_MESSAGES}, code, getattr(text, "args", None), str(text),
                  translate=tr)
