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
    # -- the names of the undo steps (the Edit menu, project_history) -------
    _spec("fem.step.project_settings", "Project settings"),
]

#: Every message of the operations of this program, by code.
FEM_MESSAGES: dict = {s.code: s for s in _ENTRIES}


def say(code: str, **args):
    """The message ``code`` of :data:`FEM_MESSAGES` with ``args``."""
    return coded(FEM_MESSAGES, code, **args)


def part(code: str, **args) -> dict:
    """The message ``code`` as the value of another message's field."""
    return as_nested(say(code, **args))
