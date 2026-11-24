# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The menus, in the order of the work (spec 006, RF-13; D4).

``MENUS`` is the menu bar: each menu's English title (shown through
``tr()``) and its entries, action keys of the window's registry, ``"-"``
for a separator. The order is the reference program's and the engineer's:
File, Edit, View, Analysis, Boundaries, Mesh, Loading, Displacements,
Support, Groundwater, Statistics, Properties, Tools, Window, Help.

``FUTURE`` are the menus whose content comes in a later phase (D4): they are
there, in their place, with ONE entry that is disabled and says when it
comes, so the order is the one an engineer knows and nothing is promised
that is not there.

``PENDING`` are the menus of this phase still without their entries, each
with the task that fills it: the list only gets shorter (a test holds it).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

ORDER = ("File", "Edit", "View", "Analysis", "Boundaries", "Mesh", "Loading", "Displacements",
         "Support", "Groundwater", "Statistics", "Properties", "Tools", "Window", "Help")

#: menu -> (the key of its disabled entry, its text, why: when it comes)
FUTURE = {
    "Support": ("soon_support", "Liners and bolts",
                "Liners and bolts come in phase 3 (specs 013 and 014)."),
    "Groundwater": ("soon_groundwater", "Water table and pore pressures",
                    "Pore pressures come in phase 2 (spec 010)."),
    "Statistics": ("soon_statistics", "Probabilistic analysis",
                   "The probabilistic analysis comes in phase 6 (spec 027)."),
    "Tools": ("soon_tools", "Drawing tools and annotations",
              "Annotations and measuring tools come in a later spec."),
}

#: menu -> the task of spec 006 that gives it its entries
PENDING = {
    "View": "T21", "Analysis": "T23", "Boundaries": "T22", "Mesh": "T25", "Loading": "T27",
    "Displacements": "T27", "Properties": "T26",
}

MENUS = {
    "File": ("new", "open", "-", "save", "save_as", "-", "prefs", "-", "exit"),
    "Edit": ("undo", "redo"),
    "Window": ("window_main",),
    "Help": ("about",),
    **{menu: (key,) for menu, (key, _t, _w) in FUTURE.items()},
}
