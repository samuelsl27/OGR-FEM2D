# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The operations that edit a model (spec 006, T12; RF-6 to RF-8): every edit
of ``model/edit.py``, ``stages.py``, ``cuts.py`` and ``shapes.py`` as a named
operation, each one undo step.

The names are those of OGR Slip2D where they do the same (``boundary_add``,
``boundary_edit``, ``material_set``, ``material_assign``,
``material_delete``, ``load_set``, ``load_delete``); what Slip2D does not
have takes the same form (``stage_add``, ``field_set``, ``condition_set``).

A stretch of a boundary is given by the boundary and two of its vertices
(``start``, ``end``, forward in its order of vertices), or by the boundary
alone for all of it (spec 004, ``Span``). Points are ``[x, y]`` in metres;
values in kN, kPa and kN/m3, as the model keeps them; the field stress
compression positive, and a normal load positive into the ground (spec
004, D6).

Drawing a boundary or moving one puts the vertices of its cuts with the
others (``cuts.cut``, RF-2) unless ``cut`` is false, and the answer lists
them.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Any, Optional

from ogr_core.api import InvalidArgument, unknown
from ogr_core.api.coerce import coerce_value, point, points

from ...engine.initial_stress import Stratum
from ...model import cuts, shapes, stages
from ...model import edit as ed
from ...model import model as md
from ..messages import say
from ..registry import OPERATIONS
from ..workspace import edit, model_errors

BOUNDARY_OPS = ("delete", "rename", "change_type", "set_closed", "translate", "move_vertex",
                "insert_vertex", "delete_vertex", "set_arc", "set_divisions")


def _opt(value, hint, where):
    return None if value is None else coerce_value(value, hint, where)


def _span(boundary, start, end) -> md.Span:
    if not isinstance(boundary, str) or not boundary:
        raise InvalidArgument(say("fem.argument.text", where="boundary"))
    if (start is None) != (end is None):
        raise InvalidArgument(say("fem.span.both"))
    return md.Span(boundary, None if start is None else point(start, "start"),
                   None if end is None else point(end, "end"))


def _where(boundary, start, end, vertex):
    """(span, vertex): a stretch of a boundary, or a vertex."""
    if (boundary is None) == (vertex is None):
        raise InvalidArgument(say("fem.where.one"))
    if vertex is not None:
        return None, point(vertex, "vertex")
    return _span(boundary, start, end), None


def _stage_id(m: md.Model, stage) -> str | None:
    if stage is None:
        return None
    ids = [s.id for s in m.stages]
    if stage not in ids:
        raise unknown("stage", stage, ids)
    return stage


def _cut(m: md.Model, bid: str, do: bool, added: list) -> md.Model:
    if not do:
        return m
    c = cuts.cut(m, bid)
    added.extend({"boundary": b, "point": list(p)} for b, p in c.added)
    return c.model


# ------------------------------------------------------------ boundaries
@OPERATIONS.operation("boundary_add", toolset="model", mutates=True)
def boundary_add(ws, type: str, points_xy: list, project_id: Optional[str] = None,
                 name: str = "", closed: Optional[bool] = None, arcs: Optional[list] = None,
                 boundary: Optional[str] = None, cut: bool = True) -> dict:
    """Draw a boundary (external, material, excavation or stage) through
    ``points_xy``; ``arcs`` gives the centre of the segments that are arcs
    ([{"segment": k, "centre": [x, y]}]). Its cuts with the others become
    vertices of both, unless cut is false."""
    if type not in md.BOUNDARY_KINDS:
        raise unknown("boundary type", type, list(md.BOUNDARY_KINDS))
    pts = points(points_xy, "points_xy")
    closed = _opt(closed, bool, "closed")
    do_cut = coerce_value(cut, bool, "cut")
    attrs = []
    for k, a in enumerate(arcs or ()):
        if not isinstance(a, dict) or set(a) != {"segment", "centre"}:
            raise InvalidArgument(say("fem.arcs.shape", index=k))
        attrs.append(md.SegmentAttr(coerce_value(a["segment"], int, f"arcs[{k}].segment"),
                                    point(a["centre"], f"arcs[{k}].centre")))
    added: list = []
    out: dict = {}

    def change(m):
        bid = boundary or ed.next_id(m, type)
        out["boundary"] = bid
        m = ed.add_boundary(m, type, pts, closed, tuple(sorted(attrs, key=lambda s: s.index)),
                            bid, name)
        return _cut(m, bid, do_cut, added)

    handle, _m = edit(ws, project_id, say("fem.step.boundary_add"), change)
    return {"project_id": handle.id, "boundary": out["boundary"], "cuts": added}


@OPERATIONS.operation("boundary_circle", toolset="model", mutates=True)
def boundary_circle(ws, type: str, centre: list, project_id: Optional[str] = None,
                    radius: Optional[float] = None, through: Optional[list] = None,
                    name: str = "", boundary: Optional[str] = None, cut: bool = True) -> dict:
    """Draw a circle as four arcs, by its centre and its radius or a point
    it goes through."""
    c = point(centre, "centre")
    if (radius is None) == (through is None):
        raise InvalidArgument(say("fem.circle.one"))
    with model_errors():
        if radius is not None:
            vertices, segments = shapes.circle(c, coerce_value(radius, float, "radius"))
        else:
            vertices, segments = shapes.circle_through(c, point(through, "through"))
    return boundary_add(ws, type, [list(v) for v in vertices], project_id, name, True,
                        [{"segment": s.index, "centre": list(s.arc)} for s in segments],
                        boundary, cut)


@OPERATIONS.operation("boundary_edit", toolset="model", mutates=True)
def boundary_edit(ws, boundary: str, op: str, project_id: Optional[str] = None,
                  name: Optional[str] = None, new_type: Optional[str] = None,
                  closed: Optional[bool] = None, dx: float = 0.0, dy: float = 0.0,
                  point_xy: Optional[list] = None, to_xy: Optional[list] = None,
                  index: Optional[int] = None, segment: Optional[int] = None,
                  centre: Any = None, divisions: Optional[int] = None,
                  with_dependents: bool = False, cut: bool = True) -> dict:
    """Edit or delete a boundary: delete, rename, change_type, set_closed,
    translate, move_vertex (point_xy to to_xy, in every boundary that has
    it), insert_vertex (point_xy on segment), delete_vertex (index),
    set_arc (segment, centre or null), set_divisions (segment, divisions
    or null)."""
    if op not in BOUNDARY_OPS:
        raise unknown("boundary_edit op", op, list(BOUNDARY_OPS))
    do_cut = coerce_value(cut, bool, "cut")
    added: list = []

    def change(m):
        if op == "delete":
            return ed.delete_boundary(m, boundary, coerce_value(with_dependents, bool,
                                                                "with_dependents"))
        if op == "rename":
            return ed.rename_boundary(m, boundary, name or "")
        if op == "change_type":
            if new_type not in md.BOUNDARY_KINDS:
                raise unknown("boundary type", new_type, list(md.BOUNDARY_KINDS))
            return ed.set_boundary_kind(m, boundary, new_type)
        if op == "set_closed":
            return ed.set_closed(m, boundary, coerce_value(closed, bool, "closed"))
        if op == "translate":
            m = ed.translate_boundary(m, boundary, coerce_value(dx, float, "dx"),
                                      coerce_value(dy, float, "dy"))
            return _cut(m, boundary, do_cut, added)
        if op == "move_vertex":
            m = ed.move_vertex(m, point(point_xy, "point_xy"), point(to_xy, "to_xy"))
            return _cut(m, boundary, do_cut, added)
        if op == "insert_vertex":
            return ed.insert_vertex(m, boundary, coerce_value(segment, int, "segment"),
                                    point(point_xy, "point_xy"))
        if op == "delete_vertex":
            return ed.delete_vertex(m, boundary, coerce_value(index, int, "index"))
        if op == "set_arc":
            return ed.set_arc(m, boundary, coerce_value(segment, int, "segment"),
                              None if centre is None else point(centre, "centre"))
        return ed.set_divisions(m, boundary, coerce_value(segment, int, "segment"),
                                _opt(divisions, int, "divisions"))

    handle, _m = edit(ws, project_id, say("fem.step.boundary_edit", op=op), change)
    return {"project_id": handle.id, "boundary": boundary, "op": op, "cuts": added}


# ------------------------------------------------------------- materials
_MATERIAL = {"name": str, "E": float, "nu": float, "unit_weight": float,
             "initial_loading": str, "color": str}


@OPERATIONS.operation("material_set", toolset="model", mutates=True)
def material_set(ws, project_id: Optional[str] = None, material: Optional[str] = None,
                 name: Optional[str] = None, E: Optional[float] = None,
                 nu: Optional[float] = None, unit_weight: Optional[float] = None,
                 initial_loading: Optional[str] = None, color: Optional[str] = None) -> dict:
    """Create a material (without ``material``) or change one: name, E and
    nu (kPa; none until given), unit weight (kN/m3), initial loading
    (field_stress, field_stress_and_body_force, body_force, none), colour."""
    given = {k: coerce_value(v, _MATERIAL[k], k) for k, v in
             (("name", name), ("E", E), ("nu", nu), ("unit_weight", unit_weight),
              ("initial_loading", initial_loading), ("color", color)) if v is not None}
    if "initial_loading" in given and given["initial_loading"] not in md.INITIAL_LOADINGS:
        raise unknown("initial loading", given["initial_loading"], list(md.INITIAL_LOADINGS))
    out: dict = {}

    def change(m):
        if material is None:
            out["material"] = ed.next_material_id(m)
            return ed.add_material(m, out["material"], **given)
        out["material"] = material
        return ed.set_material(m, material, **given)

    handle, _m = edit(ws, project_id, say("fem.step.material_set"), change)
    return {"project_id": handle.id, "material": out["material"]}


@OPERATIONS.operation("material_delete", toolset="model", mutates=True)
def material_delete(ws, material: str, project_id: Optional[str] = None) -> dict:
    """Delete a material no region has."""
    handle, _m = edit(ws, project_id, say("fem.step.material_delete"),
                      lambda m: ed.delete_material(m, material))
    return {"project_id": handle.id, "deleted": material}


@OPERATIONS.operation("material_assign", toolset="model", mutates=True)
def material_assign(ws, material: str, x: float, y: float, project_id: Optional[str] = None,
                    stage: Optional[str] = None, this_stage_only: bool = False) -> dict:
    """The region that holds (x, y) takes ``material`` (one material per
    region for the whole analysis until spec 012)."""
    xy = (coerce_value(x, float, "x"), coerce_value(y, float, "y"))
    only = coerce_value(this_stage_only, bool, "this_stage_only")
    handle, _m = edit(ws, project_id, say("fem.step.material_assign"),
                      lambda m: stages.assign_material(m, xy, material, _stage_id(m, stage), only))
    return {"project_id": handle.id, "material": material, "point": list(xy)}


@OPERATIONS.operation("region_excavate", toolset="model", mutates=True)
def region_excavate(ws, x: float, y: float, stage: str, project_id: Optional[str] = None,
                    excavated: bool = True, this_stage_only: bool = False) -> dict:
    """Excavate (or fill) the region that holds (x, y) from ``stage`` on,
    or in that stage only."""
    xy = (coerce_value(x, float, "x"), coerce_value(y, float, "y"))
    exc = coerce_value(excavated, bool, "excavated")
    only = coerce_value(this_stage_only, bool, "this_stage_only")
    handle, _m = edit(ws, project_id, say("fem.step.region_excavate"),
                      lambda m: stages.set_excavated(m, xy, _stage_id(m, stage), exc, only))
    return {"project_id": handle.id, "point": list(xy), "stage": stage, "excavated": exc}


# ---------------------------------------------------------------- stages
@OPERATIONS.operation("stage_add", toolset="model", mutates=True)
def stage_add(ws, project_id: Optional[str] = None, index: Optional[int] = None,
              name: str = "", stage: Optional[str] = None) -> dict:
    """Insert a stage at ``index`` (0 is in front; by default the end). It
    copies the stage before it, or the first one in front of it."""
    out: dict = {}

    def change(m):
        k = len(m.stages) if index is None else coerce_value(index, int, "index")
        out["stage"] = stage or ed.next_stage_id(m)
        if not 0 <= k <= len(m.stages):
            raise InvalidArgument(say("fem.stage.index", index=k, count=len(m.stages)))
        return stages.insert_stage(m, k, out["stage"], name)

    handle, _m = edit(ws, project_id, say("fem.step.stage_add"), change)
    return {"project_id": handle.id, "stage": out["stage"]}


@OPERATIONS.operation("stage_delete", toolset="model", mutates=True)
def stage_delete(ws, stage: str, project_id: Optional[str] = None) -> dict:
    """Delete a stage, and its column of every table."""
    handle, _m = edit(ws, project_id, say("fem.step.stage_delete"),
                      lambda m: stages.delete_stage(m, _stage_id(m, stage)))
    return {"project_id": handle.id, "deleted": stage}


@OPERATIONS.operation("stage_rename", toolset="model", mutates=True)
def stage_rename(ws, stage: str, name: str, project_id: Optional[str] = None) -> dict:
    """Give a stage another name (its id stays)."""
    handle, _m = edit(ws, project_id, say("fem.step.stage_rename"),
                      lambda m: stages.rename_stage(m, _stage_id(m, stage), name))
    return {"project_id": handle.id, "stage": stage, "name": name}


# ----------------------------------------------------------------- field
@OPERATIONS.operation("field_set", toolset="model", mutates=True)
def field_set(ws, kind: str, project_id: Optional[str] = None, sigma_1: float = 0.0,
              sigma_3: float = 0.0, sigma_z: float = 0.0, angle: float = 0.0,
              surface: Optional[float] = None, strata: Optional[list] = None) -> dict:
    """The field stress, compression positive (kPa): constant (sigma_1,
    sigma_3, sigma_z, angle of sigma_1 from x in degrees), or gravity
    (surface, strata [{bottom, unit_weight, k, kz}] from the top down)."""
    if kind not in ("constant", "gravity"):
        raise unknown("field kind", kind, ["constant", "gravity"])
    if kind == "constant":
        f = md.ConstantField(*(coerce_value(v, float, k) for k, v in (
            ("sigma_1", sigma_1), ("sigma_3", sigma_3), ("sigma_z", sigma_z), ("angle", angle))))
    else:
        layers = []
        for k, s in enumerate(strata or ()):
            if not isinstance(s, dict) or set(s) != {"bottom", "unit_weight", "k", "kz"}:
                raise InvalidArgument(say("fem.strata.shape", index=k))
            layers.append(Stratum(*(coerce_value(s[n], float, f"strata[{k}].{n}")
                                    for n in ("bottom", "unit_weight", "k", "kz"))))
        f = md.GravityField(coerce_value(surface, float, "surface"), tuple(layers))
    handle, _m = edit(ws, project_id, say("fem.step.field_set"), lambda m: ed.set_field(m, f))
    return {"project_id": handle.id, "kind": kind}


# ------------------------------------------------------------ conditions
@OPERATIONS.operation("condition_set", toolset="model", mutates=True)
def condition_set(ws, kind: str, project_id: Optional[str] = None,
                  boundary: Optional[str] = None, start: Optional[list] = None,
                  end: Optional[list] = None, vertex: Optional[list] = None,
                  ux: Optional[float] = None, uy: Optional[float] = None, name: str = "",
                  condition: Optional[int] = None) -> dict:
    """A restraint (x, y, xy), a release (free) or an imposed displacement
    (displacement: ux and/or uy in m) on a stretch of a boundary or at a
    vertex, in every stage; with ``condition`` (its index), that one is
    changed instead."""
    if kind not in md.CONDITION_KINDS:
        raise unknown("condition kind", kind, list(md.CONDITION_KINDS))
    span, v = _where(boundary, start, end, vertex)
    dux, duy = _opt(ux, float, "ux"), _opt(uy, float, "uy")
    out: dict = {}

    def change(m):
        if condition is None:
            out["condition"] = len(m.conditions)
            return ed.add_condition(m, kind, span, v, dux, duy, name)
        k = coerce_value(condition, int, "condition")
        out["condition"] = k
        old = m.conditions[k] if 0 <= k < len(m.conditions) else None
        n = len(m.stages)
        active = old.active if old is not None and old.active else (True,) * n
        factors = old.factors if old is not None and old.factors else (1.0,) * n
        return ed.set_condition(m, k, kind=kind, span=span, vertex=v, ux=dux, uy=duy, name=name,
                                active=() if kind == md.DISPLACEMENT else active,
                                factors=factors if kind == md.DISPLACEMENT else ())

    handle, _m = edit(ws, project_id, say("fem.step.condition_set"), change)
    return {"project_id": handle.id, "condition": out["condition"]}


@OPERATIONS.operation("condition_delete", toolset="model", mutates=True)
def condition_delete(ws, condition: int, project_id: Optional[str] = None) -> dict:
    """Delete a condition, by its index (project_summary counts them)."""
    k = coerce_value(condition, int, "condition")
    handle, _m = edit(ws, project_id, say("fem.step.condition_delete"),
                      lambda m: ed.delete_condition(m, k))
    return {"project_id": handle.id, "deleted": k}


@OPERATIONS.operation("condition_stage", toolset="model", mutates=True)
def condition_stage(ws, condition: int, stage: str, project_id: Optional[str] = None,
                    active: Optional[bool] = None, factor: Any = "unchanged",
                    this_stage_only: bool = False) -> dict:
    """A restraint active or not from ``stage`` on (or in it only); the
    factor of an imposed displacement there (null: it does not act)."""
    k = coerce_value(condition, int, "condition")
    only = coerce_value(this_stage_only, bool, "this_stage_only")

    def change(m):
        sid = _stage_id(m, stage)
        if active is not None:
            m = stages.set_condition_active(m, k, sid, coerce_value(active, bool, "active"), only)
        if factor != "unchanged":
            m = stages.set_condition_factor(m, k, sid, _opt(factor, float, "factor"), only)
        return m

    handle, _m = edit(ws, project_id, say("fem.step.condition_stage"), change)
    return {"project_id": handle.id, "condition": k, "stage": stage}


@OPERATIONS.operation("condition_default", toolset="model", mutates=True)
def condition_default(ws, kind: str, project_id: Optional[str] = None) -> dict:
    """The condition of the external boundary where nothing else is said
    (x, y, xy or free)."""
    if kind not in md.RESTRAINTS:
        raise unknown("restraint", kind, list(md.RESTRAINTS))
    handle, _m = edit(ws, project_id, say("fem.step.condition_default"),
                      lambda m: ed.set_default_restraint(m, kind))
    return {"project_id": handle.id, "default_restraint": kind}


# ----------------------------------------------------------------- loads
@OPERATIONS.operation("load_set", toolset="loads", mutates=True)
def load_set(ws, kind: str, magnitude: float, project_id: Optional[str] = None,
             boundary: Optional[str] = None, start: Optional[list] = None,
             end: Optional[list] = None, vertex: Optional[list] = None,
             magnitude_end: Optional[float] = None, orientation: Optional[str] = None,
             angle: float = 0.0, name: str = "", load: Optional[int] = None) -> dict:
    """A distributed load on a stretch of a boundary (kPa, from magnitude to
    magnitude_end; normal by default, positive into the ground) or a point
    load at a vertex (kN per metre out of plane; vertical by default), with
    factor 1 in every stage; with ``load`` (its index), that one is changed."""
    if kind not in ("distributed", "point"):
        raise unknown("load kind", kind, ["distributed", "point"])
    value = coerce_value(magnitude, float, "magnitude")
    a = coerce_value(angle, float, "angle")
    if kind == "distributed":
        if vertex is not None:
            raise InvalidArgument(say("fem.load.distributed_span"))
        span = _span(boundary, start, end)
        orient = orientation or md.NORMAL
        options = md.ORIENTATIONS
    else:
        if boundary is not None or vertex is None:
            raise InvalidArgument(say("fem.load.point_vertex"))
        v = point(vertex, "vertex")
        orient = orientation or md.VERTICAL
        options = md.POINT_ORIENTATIONS
    if orient not in options:
        raise unknown("orientation", orient, list(options))
    out: dict = {}

    def change(m):
        if load is None:
            out["load"] = len(m.loads)
            if kind == "distributed":
                return ed.add_distributed_load(m, span, value, _opt(magnitude_end, float,
                                                                    "magnitude_end"), orient, a, name)
            return ed.add_point_load(m, v, value, orient, a, name)
        k = coerce_value(load, int, "load")
        out["load"] = k
        if kind == "distributed":
            end_value = value if magnitude_end is None else coerce_value(magnitude_end, float,
                                                                          "magnitude_end")
            return ed.set_load(m, k, span=span, start_value=value, end_value=end_value,
                               orientation=orient, angle=a, name=name)
        return ed.set_load(m, k, vertex=v, magnitude=value, orientation=orient, angle=a, name=name)

    handle, _m = edit(ws, project_id, say("fem.step.load_set"), change)
    return {"project_id": handle.id, "load": out["load"]}


@OPERATIONS.operation("load_delete", toolset="loads", mutates=True)
def load_delete(ws, load: int, project_id: Optional[str] = None) -> dict:
    """Delete a load, by its index (project_summary counts them)."""
    k = coerce_value(load, int, "load")
    handle, _m = edit(ws, project_id, say("fem.step.load_delete"), lambda m: ed.delete_load(m, k))
    return {"project_id": handle.id, "deleted": k}


@OPERATIONS.operation("load_stage", toolset="loads", mutates=True)
def load_stage(ws, load: int, stage: str, factor: float, project_id: Optional[str] = None,
               this_stage_only: bool = False) -> dict:
    """The factor of a load from ``stage`` on (or in it only): the total
    there is factor x magnitude, 0 takes it off."""
    k = coerce_value(load, int, "load")
    f = coerce_value(factor, float, "factor")
    only = coerce_value(this_stage_only, bool, "this_stage_only")
    handle, _m = edit(ws, project_id, say("fem.step.load_stage"),
                      lambda m: stages.set_load_factor(m, k, _stage_id(m, stage), f, only))
    return {"project_id": handle.id, "load": k, "stage": stage, "factor": f}
