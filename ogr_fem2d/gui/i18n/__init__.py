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
from .es_help import ES as _HELP
from .es_messages import ES as _MESSAGES
from .es_report import ES as _REPORT

#: every Spanish text of this program, by area
AREAS = {"menus": _MENUS, "canvas": _CANVAS, "dialogs": _DIALOGS, "messages": _MESSAGES,
         "report": _REPORT, "help": _HELP}


def spanish() -> dict[str, str]:
    out: dict[str, str] = {}
    for table in AREAS.values():
        out.update(table)
    return out


def install() -> list[str]:
    """Add this program's Spanish to ``tr()``; the keys of ``ogr_ui`` it
    changed (none, normally)."""
    return add_translations("es", spanish())


def catalogues() -> dict:
    """Every coded catalogue a message said here can come from: the core's
    (the operations', the mesher's, the files', the geometry's, the DXF's,
    the steps of the history) and this program's. Their Spanish is
    ``ogr_ui``'s for the core's (OGR GUI 0.1.2) and this program's for its
    own; a test holds that every template of the core pinned has it."""
    from ogr_core.api import API_MESSAGES
    from ogr_core.dxf.messages import EXPORT_MESSAGES
    from ogr_core.fem.messages import REFINE_MESSAGES
    from ogr_core.file_messages import FILE_MESSAGES
    from ogr_core.geometry.messages import GEOMETRY_MESSAGES
    from ogr_core.project.step_names import STEP_NAMES

    from ...api.messages import FEM_MESSAGES
    out: dict = {}
    for cat in (API_MESSAGES, REFINE_MESSAGES, FILE_MESSAGES, GEOMETRY_MESSAGES,
                EXPORT_MESSAGES, STEP_NAMES, FEM_MESSAGES):
        clash = set(out) & set(cat)
        if clash:
            raise RuntimeError(f"a code in two catalogues: {sorted(clash)}")
        out.update(cat)
    return out


def say(text) -> str:
    """A message for the reader: a coded one (the operations', the core's:
    ``ogr_core.messages.Coded``) rendered from its code in the reader's
    language, its values put back; a plain one through ``tr()``."""
    from ogr_core.messages import render
    from ogr_ui.i18n import tr

    code = getattr(text, "code", "")
    if not code:
        return tr(str(text))
    return render(catalogues(), code, getattr(text, "args", None), str(text), translate=tr)
