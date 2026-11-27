# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The messages of the operations of OGR FEM2D, each with a stable code (spec
006, RF-7; rule 2).

The pattern of the core's ``ogr_core.api.messages``: a sentence an
operation writes is an entry here, rendered with ``ogr_core.messages.coded``.
It IS the English sentence, and it also carries its code and values, so the
interface says it in the reader's language (``ogr_core.messages.render``
with this catalogue and the core's ``API_MESSAGES``).

The problems of a model (``model.problems``: a rule, where, and an English
message) travel inside ``fem.model.invalid`` as a list in the error's
details, each with its rule: the rule is the stable key the interface
translates by (spec 006, part C).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.messages import MessageSpec, as_nested, coded

from ..model.import_messages import IMPORT_MESSAGES


def _spec(code: str, english: str, group_by=(), **kw) -> MessageSpec:
    return MessageSpec(code, english, group_by=tuple(group_by), **kw)


_ENTRIES = [
    _spec("fem.model.invalid", "The model refuses it ({count} problems): {first}",
          one="The model refuses it: {first}", count="count"),
    _spec("fem.model.invalid.hint",
          "Every problem, with its rule and where, is in the details."),
    _spec("fem.file.invalid", "The file cannot be read ({count} problems): {first}",
          one="The file cannot be read: {first}", count="count"),
    _spec("fem.file.kind",
          "{name}: OGR FEM2D opens .ogrfem2d, .ogr (OGR Slip2D) and .dxf files."),
    _spec("fem.save.kind", "{name}: a model is saved as .ogrfem2d."),
    _spec("fem.save.no_path", "Model {model} has no file yet."),
    _spec("fem.save.no_path.hint", "Give the path to save it to."),
    _spec("fem.close.unsaved", "Model {model} has unsaved changes."),
    _spec("fem.close.unsaved.hint",
          "Save it (project_save), or close it with discard_changes=true."),
    _spec("fem.history.action", "history action"),
    _spec("fem.history.steps", "steps must be between 1 and 200."),
    _spec("fem.argument.text", "{where} must be text."),
    _spec("fem.argument.of", "argument of {op}"),
    _spec("fem.span.both", "A stretch of a boundary needs both its start and its end, or neither "
                           "(all of it)."),
    _spec("fem.where.one", "Give a stretch of a boundary (boundary, start, end) or a vertex, "
                           "one of the two."),
    _spec("fem.arcs.shape", "arcs[{index}] must be {{\"segment\": k, \"centre\": [x, y]}}."),
    _spec("fem.circle.one", "Give the radius or a point the circle goes through, one of the two."),
    _spec("fem.stage.index", "There is no place {index} for a stage: there are {count} stages, "
                             "from 0 to {count}."),
    _spec("fem.strata.shape", "strata[{index}] must be {{\"bottom\", \"unit_weight\", \"k\", \"kz\"}}."),
    _spec("fem.load.point_vertex", "A point load is at a vertex: give vertex, not boundary."),
    _spec("fem.load.distributed_span", "A distributed load is on a stretch of a boundary: give "
                                       "boundary (and start, end), not vertex."),
    _spec("fem.mesh.clear_and_set", "{name} is both given and cleared."),
    _spec("fem.mesh.not_a_mesh_job", "Job {job} is not one of meshing."),
    _spec("fem.mesh.job_not_done", "Job {job} has not made its mesh: it is {state}."),
    _spec("fem.mesh.model_changed", "Model {model} changed while it was being meshed."),
    _spec("fem.mesh.model_changed.hint", "Mesh it again (mesh_generate)."),
    _spec("fem.windows.shape", "windows[{index}] must be {{\"polygon\": [[x, y], ...], \"size\": h}}."),
    _spec("fem.run.no_file", "Model {model} has no file: the results are written beside it."),
    _spec("fem.run.no_file.hint", "Save it first (project_save)."),
    _spec("fem.run.unsaved", "Model {model} has changes that are not in its file."),
    _spec("fem.run.unsaved.hint", "Save it first (project_save): the results carry the file's "
                                  "fingerprint, and would be stale at once."),
    _spec("fem.results.not_valid", "The results are {status} ({message})."),
    _spec("fem.results.at_needs_xy", "A value at a point needs x and y."),
    _spec("fem.results.not_valid.hint", "Calculate the model again (analysis_run), or read them as "
                                        "they are with allow_invalid=true: every answer then says "
                                        "their state."),
    _spec("fem.field.refused", "The field cannot be drawn so: {what}"),
    _spec("fem.query.refused", "The query cannot be made so: {what}"),
    # -- the names of the undo steps (the Edit menu, project_history) -------
    _spec("fem.step.project_settings", "Project settings"),
    _spec("fem.step.boundary_add", "Add boundary"),
    _spec("fem.step.boundary_edit", "Edit boundary ({op})"),
    _spec("fem.step.material_set", "Material"),
    _spec("fem.step.material_delete", "Delete material"),
    _spec("fem.step.material_assign", "Assign material"),
    _spec("fem.step.region_excavate", "Excavate"),
    _spec("fem.step.stage_add", "Add stage"),
    _spec("fem.step.stage_delete", "Delete stage"),
    _spec("fem.step.stage_rename", "Rename stage"),
    _spec("fem.step.field_set", "Field stress"),
    _spec("fem.step.condition_set", "Condition"),
    _spec("fem.step.condition_delete", "Delete condition"),
    _spec("fem.step.condition_stage", "Condition in a stage"),
    _spec("fem.step.condition_default", "Default condition of the external boundary"),
    _spec("fem.step.load_set", "Load"),
    _spec("fem.step.load_delete", "Delete load"),
    _spec("fem.step.load_stage", "Load in a stage"),
    _spec("fem.step.mesh_settings", "Mesh settings"),
    _spec("fem.step.mesh_generate", "Mesh"),
    _spec("fem.step.mesh_reset", "Remove mesh"),
]

#: Every message of the operations of this program, by code.
#: with the lines of the report of a conversion (model/import_messages.py)
FEM_MESSAGES: dict = {**{s.code: s for s in _ENTRIES}, **IMPORT_MESSAGES}


def say(code: str, **args):
    """The message ``code`` of :data:`FEM_MESSAGES` with ``args``."""
    return coded(FEM_MESSAGES, code, **args)


def part(code: str, **args) -> dict:
    """The message ``code`` as the value of another message's field."""
    return as_nested(say(code, **args))
