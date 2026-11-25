# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Every action of the window, with the operation it calls or why it calls
none (spec 006, D13; H5): an agent reaches through the operations what a
person reaches through the menus. A test holds the window's registry to
this table: an action without its entry, or an entry without its action,
fails it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

#: action key -> the operation it calls
MAPPED = {
    "new": "project_new",
    "open": "project_open",
    "save": "project_save",
    "save_as": "project_save",
    "undo": "project_history",
    "redo": "project_history",
    "add_excavation": "boundary_add",
    "add_external": "boundary_add",
    "add_material": "boundary_add",
    "add_stage": "boundary_add",
    "finish_boundary": "boundary_add",
    "add_circle": "boundary_circle",
    "move_vertex": "boundary_edit",
    "insert_vertex": "boundary_edit",
    "delete_vertex": "boundary_edit",
    "delete_boundary": "boundary_edit",
}

#: action key -> why it calls no operation
UI_ONLY = {
    "prefs": "the language and the theme of this window, kept on this machine",
    "exit": "closes the window",
    "about": "shows who made the program and its licences",
    "window_main": "brings this window to the front",
    "zoom_all": "fits the model in the canvas",
    "zoom_in": "zooms the canvas in",
    "zoom_out": "zooms the canvas out",
    "show_grid": "shows or hides the canvas's grid",
    "show_mesh": "shows or hides the mesh in the canvas",
    "draw_arc": "a step of drawing: the boundary goes in by boundary_add when it is finished",
    "coords_table": "a step of drawing: the boundary goes in by boundary_add when it is finished",
    "soon_support": "disabled: says when its phase comes (D4)",
    "soon_groundwater": "disabled: says when its phase comes (D4)",
    "soon_statistics": "disabled: says when its phase comes (D4)",
    "soon_tools": "disabled: says when it comes (D4)",
}
