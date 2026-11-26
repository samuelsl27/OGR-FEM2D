# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A problem of the model, said in the reader's language (spec 006, decided on
2026-11-25; rule 2).

A problem (``model.problems``) is a rule, where, and an English message;
the rule is the stable key the interface translates by (``api/messages``).
Here each rule of the model and of its regions has its sentence, which says
what is wrong and how to go on, and ``where`` is said with the words of the
program's objects in the reader's language (a boundary, a material, a
stage...), its ids and coordinates as they are. A rule without its sentence
keeps the English message (a test holds every rule of the model to one).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import re

from ogr_ui.i18n import tr

#: rule -> what it means for the user, and how to go on
RULE_TEXT = {
    "analysis": "The kind of analysis is not one the program knows.",
    "units": "The unit system is not one the program knows.",
    "boundary": "A boundary is not well formed: draw it again.",
    "boundary_id": "Two boundaries share an id, or one has none.",
    "segment_attr": "An arc or the divisions of a segment are not well given.",
    "external": "A model has exactly one external boundary: Boundaries > Add External.",
    "left_of_axis": "In axisymmetry the model lies on x ≥ 0: move the vertex, or choose plane "
                    "strain.",
    "material": "A material is not well given: Properties > Define Materials.",
    "material_id": "Two materials share an id, or one has none.",
    "stage": "A stage is not well given: Analysis > Project Settings.",
    "assignment": "An assignment is not well given: Properties > Assign Properties.",
    "reactivated": "An excavated region cannot come back in a later stage.",
    "field": "The field stress is not well given: Loading > Field Stress.",
    "default_restraint": "The default restraint of the external is not one the program knows.",
    "condition": "A condition is not well given: Displacements.",
    "load": "A load is not well given: Loading.",
    "mesh": "The mesh is not well formed: Mesh > Discretize and Mesh.",
    "arc": "An arc is not well given: its centre must make an arc of its segment.",
    "segment_conflict": "Two boundaries share a segment with different attributes.",
    "crossing": "Two boundaries cross where neither has a vertex.",
    "dangling": "A boundary ends inside the model without meeting another.",
    "outside_external": "A boundary goes outside the external.",
    "region_unassigned": "A region has no material yet: Properties > Assign Properties.",
    "region_twice": "A region has two assignments: keep one.",
    "assignment_outside": "An assignment point is in no region.",
}

#: the words a problem names the model's objects with, as the reader says them
_WHERE = (
    (re.compile(r"^the region with outline through (.*)$"), "the region with outline through %s"),
    (re.compile(r"^segment (\S+) of boundary (.*)$"), "segment %s of boundary %s"),
    (re.compile(r"^boundary (.*)$"), "boundary %s"),
    (re.compile(r"^material (.*)$"), "material %s"),
    (re.compile(r"^stage (.*)$"), "stage %s"),
    (re.compile(r"^assignment at (.*)$"), "assignment at %s"),
    (re.compile(r"^condition (.*)$"), "condition %s"),
    (re.compile(r"^load (.*)$"), "load %s"),
    (re.compile(r"^stratum (.*)$"), "stratum %s"),
    (re.compile(r"^point (.*)$"), "point %s"),
)
_PLAIN = {"model": "the model", "settings": "the mesh settings",
          "field stress": "the field stress", "mesh": "the mesh"}


def where_text(where: str) -> str:
    for pattern, template in _WHERE:
        found = pattern.match(where)
        if found:
            return tr(template) % found.groups()
    return tr(_PLAIN[where]) if where in _PLAIN else where


def problem_text(problem: dict) -> str:
    """``where: what``, in the reader's language."""
    rule = problem.get("rule", "")
    what = tr(RULE_TEXT[rule]) if rule in RULE_TEXT else problem.get("message", "")
    return f"{where_text(problem.get('where', ''))}: {what}"
