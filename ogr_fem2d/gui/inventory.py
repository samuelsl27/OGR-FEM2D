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
    "import_slip2d": "project_open",
    "import_dxf": "project_open",
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
    "project_settings": "project_settings",
    "stage_insert": "stage_add",
    "stage_rename": "stage_rename",
    "stage_delete": "stage_delete",
    "field_stress": "field_set",
    "mesh_setup": "mesh_settings",
    "mesh_discretize": "mesh_discretize",
    "mesh_generate": "mesh_generate",
    "mesh_reset": "mesh_reset",
    "define_materials": "material_set",
    "assign": "material_assign",
    "restrain_x": "condition_set",
    "restrain_y": "condition_set",
    "restrain_xy": "condition_set",
    "release": "condition_set",
    "impose": "condition_set",
    "default_restraint": "condition_default",
    "delete_condition": "condition_delete",
    "add_distributed": "load_set",
    "add_point": "load_set",
    "delete_load": "load_delete",
    "stage_factors": "load_stage",
    "segment_divisions": "boundary_edit",
    "compute": "analysis_run",
    "interpret": "results_open",
    "report": "results_report",
}

#: action key -> why it calls no operation
UI_ONLY = {
    "prefs": "the language and the theme of this window, kept on this machine",
    "exit": "closes the window",
    "clear_recent": "empties the list of recent models kept on this machine",
    "about": "shows who made the program and its licences",
    "help": "shows the help, written in the program, with the validation cases (RF-21)",
    "window_main": "brings this window to the front",
    "agent_bridge": "serves this window's model to the MCP server, whose calls are the "
                    "operations themselves (D8)",
    "window_compute": "shows the calculation's window, which follows the jobs by job_get",
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
