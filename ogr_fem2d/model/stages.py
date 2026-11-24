# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The stages of a model and the edits that depend on them (spec 004, RF-3,
RF-4, D10).

Every stage has a stable id and a name; everything that depends on the stage
is kept in the model once per stage, in the order of the stages, so the file
holds the whole table (D10). Whether a change goes on to the later stages or
stays in "this stage only" is the edit's, not the file's (P20, D03 §2 of the
interface analysis): an edit in stage k writes stages k to N, or k alone.

* ``insert_stage``: the new stage copies the one before it, or the first one
  when it goes in front of it (D10: OWN PROPOSAL, the reference program does
  not document what an inserted stage inherits, M04a:278);
* ``delete_stage``, ``rename_stage``;
* ``set_excavated``, ``assign_material``: by a point inside the region;
* ``set_condition_active``, ``set_condition_factor``, ``set_load_factor``.

RF-4: an excavated region coming back, or a region changing material between
stages, is refused with ModelError (until spec 012). The material of a
region is one for the whole analysis, the initial state included.

Every edit returns a new model; none changes the one it was given. An edit
is refused when it adds a problem to the model (``refuse_new_problems``),
not when the model had one before it: a model being drawn is edited too
(spec 006, T5; until then they asked the whole model to be valid).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import replace

from ..engine.model import Problem
from ..mesh import geometry as g
from . import model as md
from . import regions

#: The rule of the edits that RF-4 refuses besides ``reactivated``.
RULES = ("material_change",)


def _insert(values: tuple, index: int, source: int) -> tuple:
    return values[:index] + (values[source],) + values[index:]


def _drop(values: tuple, index: int) -> tuple:
    return values[:index] + values[index + 1:]


def _write(values: tuple, k: int, value, only: bool) -> tuple:
    """Stages k..N take ``value`` (or k alone)."""
    end = k + 1 if only else len(values)
    return values[:k] + (value,) * (end - k) + values[end:]


def _each_stage_table(m: md.Model, change) -> md.Model:
    """``m`` with ``change`` applied to every per-stage tuple."""
    assignments = tuple(replace(a, excavated=change(a.excavated)) for a in m.assignments)
    conditions = tuple(replace(c, active=change(c.active)) if c.kind != md.DISPLACEMENT
                       else replace(c, factors=change(c.factors)) for c in m.conditions)
    loads = tuple(replace(ld, factors=change(ld.factors)) for ld in m.loads)
    return replace(m, assignments=assignments, conditions=conditions, loads=loads)


def insert_stage(m: md.Model, index: int, stage_id: str, name: str = "") -> md.Model:
    """A new stage at position ``index`` (0 is in front of the first),
    copying the stage before it, or the first one when it goes in front."""
    if not 0 <= index <= len(m.stages):
        raise IndexError(index)
    source = index - 1 if index > 0 else 0
    out = _each_stage_table(m, lambda v: _insert(v, index, source))
    stages = m.stages[:index] + (md.Stage(stage_id, name),) + m.stages[index:]
    return md.refuse_new_problems(m, replace(out, stages=stages))


def delete_stage(m: md.Model, stage_id: str) -> md.Model:
    if len(m.stages) == 1:
        raise md.ModelError([Problem("stage", f"stage {stage_id!r}",
                                     "the only stage cannot be deleted")])
    k = m.stage_index(stage_id)
    out = _each_stage_table(m, lambda v: _drop(v, k))
    return md.refuse_new_problems(m, replace(out, stages=_drop(m.stages, k)))


def rename_stage(m: md.Model, stage_id: str, name: str) -> md.Model:
    k = m.stage_index(stage_id)
    stages = m.stages[:k] + (replace(m.stages[k], name=name),) + m.stages[k + 1:]
    return replace(m, stages=stages)


def _assignment_at(m: md.Model, point) -> int | None:
    """The assignment of the region that holds ``point``."""
    geo = regions.build(m)
    arcs = regions._arcs(geo.points, geo.segments)
    for r in geo.regions:
        if g._inside_region((float(point[0]), float(point[1])), g.Region(r.outline, r.holes),
                            geo.points, arcs):
            return r.assignment
    return None


def set_excavated(m: md.Model, point, stage_id: str, excavated: bool,
                  this_stage_only: bool = False) -> md.Model:
    """The region that holds ``point`` excavated (or not) from stage
    ``stage_id`` on, or in that stage only. Refused if it makes an
    excavated region come back (RF-4)."""
    k = m.stage_index(stage_id)
    a = _assignment_at(m, point)
    if a is None:
        raise md.ModelError([Problem("assignment_outside", f"point {point}",
                                     "lies in no region with an assignment")])
    old = m.assignments[a]
    new = replace(old, excavated=_write(old.excavated, k, excavated, this_stage_only))
    assignments = m.assignments[:a] + (new,) + m.assignments[a + 1:]
    return md.refuse_new_problems(m, replace(m, assignments=assignments))


def assign_material(m: md.Model, point, material_id: str, stage_id: str | None = None,
                    this_stage_only: bool = False) -> md.Model:
    """The region that holds ``point`` takes ``material_id``. A region has
    one material for the whole analysis (RF-4): assigning in a later stage,
    or in one stage only of several, a material other than the region's is
    refused. A region with no assignment yet gets one at ``point``."""
    if m.material(material_id) is None:
        raise md.ModelError([Problem("assignment", f"point {point}",
                                     f"material {material_id!r} does not exist")])
    k = 0 if stage_id is None else m.stage_index(stage_id)
    try:
        a = _assignment_at(m, point)
    except md.ModelError:
        a = None
    if a is None:
        if k > 0 or (this_stage_only and len(m.stages) > 1):
            raise md.ModelError([Problem("material_change", f"point {point}",
                                         "a region takes its material for every stage "
                                         "(RF-4, until spec 012)")])
        new = md.Assignment((float(point[0]), float(point[1])), material_id,
                            md.every_stage(m, False))
        return replace(m, assignments=m.assignments + (new,))
    old = m.assignments[a]
    if old.material != material_id and (k > 0 or (this_stage_only and len(m.stages) > 1)):
        raise md.ModelError([Problem(
            "material_change", f"assignment at {old.point}",
            f"from {old.material!r} to {material_id!r} in stage {m.stages[k].id!r} only "
            "or from it on: the engine admits no change of material between stages "
            "(spec 002; RF-4, until spec 012)")])
    assignments = (m.assignments[:a] + (replace(old, material=material_id),)
                   + m.assignments[a + 1:])
    return md.refuse_new_problems(m, replace(m, assignments=assignments))


def set_condition_active(m: md.Model, index: int, stage_id: str, active: bool,
                         this_stage_only: bool = False) -> md.Model:
    k = m.stage_index(stage_id)
    c = m.conditions[index]
    new = replace(c, active=_write(c.active, k, active, this_stage_only))
    return md.refuse_new_problems(m, replace(m, conditions=m.conditions[:index] + (new,)
                                                + m.conditions[index + 1:]))


def set_condition_factor(m: md.Model, index: int, stage_id: str, factor: float | None,
                         this_stage_only: bool = False) -> md.Model:
    k = m.stage_index(stage_id)
    c = m.conditions[index]
    new = replace(c, factors=_write(c.factors, k, factor, this_stage_only))
    return md.refuse_new_problems(m, replace(m, conditions=m.conditions[:index] + (new,)
                                                + m.conditions[index + 1:]))


def set_load_factor(m: md.Model, index: int, stage_id: str, factor: float,
                    this_stage_only: bool = False) -> md.Model:
    k = m.stage_index(stage_id)
    ld = m.loads[index]
    new = replace(ld, factors=_write(ld.factors, k, factor, this_stage_only))
    return md.refuse_new_problems(m, replace(m, loads=m.loads[:index] + (new,) + m.loads[index + 1:]))
