# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The ``.ogrfem2d`` file (spec 004, RF-13; ADR-0004; section by section in
docs/modelo/formato.md).

JSON in UTF-8 with these sections, in this order: ``format`` ("ogr-fem2d"),
``format_version``, ``written_by``, ``summary``, ``units``, ``analysis``,
``boundaries``, ``materials``, ``stages``, ``assignments``,
``field_stress``, ``default_restraint``, ``conditions``, ``loads``,
``mesh_settings``, ``mesh``. Everything that depends on the stage is written
as an object keyed by the stage ids, so a file says which stage each value
belongs to. Every key is always written (null when it has nothing).

Reading is strict: a key the file should have and does not, a key it should
not have (a later version, or a mistake), a value of another type, or a
later ``format_version`` is an error that names it (FileFormatError, every
problem at once). Nothing is ever dropped in silence; then the model is
validated by its own rules AS A DOCUMENT (``model.validate_document``,
ModelError): a model being drawn (no external yet, boundaries that still
cross, a region without its material) is written and read back, and
``model.problems`` says what is unfinished; calculating it is refused
(spec 004, modified by spec 006, T11: until then a file had to hold a
model ready to calculate, and the engineer could not save the work of an
afternoon until the model was finished).

Writing is deterministic and keeps the file readable and comparable with
git: objects one key per line, a list of numbers on one line, and a list of
such lists one per line (the vertices, and the nodes and elements of the
mesh, D3). Floats are written as Python writes them, the shortest text that
reads back to the same number, so writing what was read gives the same
bytes.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import __version__
from ..engine.initial_stress import Stratum
from ..engine.model import Problem
from ..mesh import geometry as g
from ..mesh.mesher import Boundary as MeshBoundary
from . import model as md

FORMAT = "ogr-fem2d"
FORMAT_VERSION = 1
SUFFIX = ".ogrfem2d"

RULES = ("format", "format_version", "key", "type")


class FileFormatError(ValueError):
    """The file is not a ``.ogrfem2d`` this version can read: every
    problem found."""

    def __init__(self, problems: list[Problem]):
        self.problems = problems
        super().__init__("the file cannot be read:\n" + "\n".join(f"  {p}" for p in problems))


# ------------------------------------------------------------------ write
def _stage_map(m: md.Model, values) -> dict | None:
    if values is None:
        return None
    return {s.id: v for s, v in zip(m.stages, values)}


def _pt(p):
    return None if p is None else [p[0], p[1]]


def _span(s: md.Span | None):
    if s is None:
        return None
    return {"boundary": s.boundary, "start": _pt(s.start), "end": _pt(s.end)}


def to_dict(m: md.Model) -> dict:
    """The content of the file, as JSON values."""
    f = m.field
    if isinstance(f, md.ConstantField):
        fd = {"kind": "constant", "sigma_1": f.sigma_1, "sigma_3": f.sigma_3,
              "sigma_z": f.sigma_z, "angle": f.angle}
    else:
        fd = {"kind": "gravitational", "surface": f.surface,
              "strata": [{"bottom": s.bottom, "unit_weight": s.unit_weight, "k": s.k,
                          "kz": s.kz} for s in f.strata]}
    st = m.mesh_settings
    out = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "written_by": f"OGR FEM2D {__version__}",
        "summary": {"title": m.summary.title, "author": m.summary.author,
                    "date": m.summary.date, "notes": m.summary.notes},
        "units": m.units,
        "analysis": m.analysis,
        "boundaries": [{"id": b.id, "kind": b.kind, "name": b.name, "closed": b.closed,
                        "vertices": [_pt(v) for v in b.vertices],
                        "segments": [{"index": s.index, "arc": _pt(s.arc),
                                      "divisions": s.divisions} for s in b.segments]}
                       for b in m.boundaries],
        "materials": [{"id": x.id, "name": x.name, "color": x.color, "E": x.E, "nu": x.nu,
                       "unit_weight": x.unit_weight, "initial_loading": x.initial_loading}
                      for x in m.materials],
        "stages": [{"id": s.id, "name": s.name} for s in m.stages],
        "assignments": [{"point": _pt(a.point), "material": a.material,
                         "excavated": _stage_map(m, a.excavated)} for a in m.assignments],
        "field_stress": fd,
        "default_restraint": m.default_restraint,
        "conditions": [{"kind": c.kind, "name": c.name, "span": _span(c.span),
                        "vertex": _pt(c.vertex),
                        "active": _stage_map(m, c.active) if c.kind != md.DISPLACEMENT else None,
                        "ux": c.ux, "uy": c.uy,
                        "factors": _stage_map(m, c.factors) if c.kind == md.DISPLACEMENT else None}
                       for c in m.conditions],
        "loads": [_load(m, ld) for ld in m.loads],
        "mesh_settings": {"kind": st.kind, "nodes_per_element": st.nodes_per_element,
                          "quality_bound": st.quality_bound, "boundary_nodes": st.boundary_nodes,
                          "max_size": st.max_size, "size": st.size, "elements": st.elements,
                          "windows": [{"polygon": [_pt(p) for p in w.polygon], "size": w.size}
                                      for w in st.windows]},
        "mesh": None if m.mesh is None else {
            "source": m.mesh.source,
            "nodes": [_pt(p) for p in m.mesh.nodes],
            "elements": [list(e) for e in m.mesh.elements],
            "element_region": list(m.mesh.element_region),
            "boundaries": [{"name": b.name, "nodes": list(b.nodes),
                            "sides": [[list(s) for s in piece] for piece in b.sides],
                            "mids": list(b.mids)} for b in m.mesh.boundaries],
            "warnings": list(m.mesh.warnings),
            "notes": m.mesh.notes,
        },
    }
    return out


def _load(m: md.Model, ld) -> dict:
    if isinstance(ld, md.DistributedLoad):
        return {"type": "distributed", "name": ld.name, "span": _span(ld.span),
                "start_value": ld.start_value, "end_value": ld.end_value,
                "orientation": ld.orientation, "angle": ld.angle,
                "factors": _stage_map(m, ld.factors)}
    return {"type": "point", "name": ld.name, "vertex": _pt(ld.vertex),
            "magnitude": ld.magnitude, "orientation": ld.orientation, "angle": ld.angle,
            "factors": _stage_map(m, ld.factors)}


def _scalar(v) -> bool:
    return not isinstance(v, (list, dict))


def _flat(v) -> bool:
    """A list that goes on one line: of numbers, or of lists of numbers."""
    return isinstance(v, list) and all(_scalar(x) or (isinstance(x, list) and all(map(_scalar, x)))
                                       for x in v)


def _dump(value, indent: str) -> str:
    inner = indent + "  "
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = [f"{inner}{json.dumps(k, ensure_ascii=False)}: {_dump(v, inner)}"
                 for k, v in value.items()]
        return "{\n" + ",\n".join(items) + "\n" + indent + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        if all(map(_scalar, value)):
            return "[" + ", ".join(_dump(v, inner) for v in value) + "]"
        if all(map(_flat, value)):
            return ("[\n" + ",\n".join(inner + _inline(v) for v in value) + "\n" + indent + "]")
        return "[\n" + ",\n".join(inner + _dump(v, inner) for v in value) + "\n" + indent + "]"
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _inline(value) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(_inline(v) for v in value) + "]"
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def dumps(m: md.Model) -> str:
    """The text of the file of a model valid as a document."""
    md.validate_document(m)
    return _dump(to_dict(m), "") + "\n"


def write(m: md.Model, path) -> Path:
    path = Path(path)
    path.write_bytes(dumps(m).encode("utf-8"))
    return path


# ------------------------------------------------------------------- read
class _Reader:
    def __init__(self):
        self.problems: list[Problem] = []

    def add(self, rule, where, message):
        self.problems.append(Problem(rule, where, message))

    def obj(self, data, where, keys) -> dict | None:
        """``data`` as an object with exactly ``keys``."""
        if not isinstance(data, dict):
            self.add("type", where, f"is {type(data).__name__}, not an object")
            return None
        missing = [k for k in keys if k not in data]
        extra = [k for k in data if k not in keys]
        if missing:
            self.add("key", where, f"lacks {missing}")
        if extra:
            self.add("key", where, f"has {extra}, which this version does not know: a later "
                                   "version of the format, or a mistake (nothing is dropped "
                                   "in silence)")
        return None if missing or extra else data

    def typed(self, value, where, kinds, nullable=False):
        if value is None and nullable:
            return True
        allowed = kinds if isinstance(kinds, tuple) else (kinds,)
        ok = (bool in allowed) if isinstance(value, bool) else isinstance(value, allowed)
        if not ok:
            self.add("type", where, f"{value!r} is not of the expected type")
        return ok

    def lst(self, value, where) -> list:
        if not isinstance(value, list):
            self.add("type", where, f"is {type(value).__name__}, not a list")
            return []
        return value

    def point(self, value, where, nullable=False):
        if value is None and nullable:
            return None
        if (isinstance(value, list) and len(value) == 2
                and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value)):
            return (value[0], value[1])
        self.add("type", where, f"{value!r} is not a point [x, y]")
        return None

    def stage_map(self, value, where, stages, kind, nullable_values=False):
        if not isinstance(value, dict):
            self.add("type", where, "is not an object keyed by stage ids")
            return None
        if set(value) != set(stages):
            self.add("key", where, f"has the stages {sorted(value)}, the model has {stages}")
            return None
        out = []
        for sid in stages:
            v = value[sid]
            if v is None and nullable_values:
                out.append(None)
            elif self.typed(v, f"{where}, stage {sid!r}", kind):
                out.append(v)
            else:
                return None
        return tuple(out)


_TOP = ("format", "format_version", "written_by", "summary", "units", "analysis", "boundaries",
        "materials", "stages", "assignments", "field_stress", "default_restraint",
        "conditions", "loads", "mesh_settings", "mesh")
_NUM = (int, float)


def from_dict(data) -> md.Model:
    """The model of the content of a file (FileFormatError, or ModelError
    after the shape is right)."""
    r = _Reader()
    if not isinstance(data, dict):
        raise FileFormatError([Problem("type", "file", "is not a JSON object")])
    if data.get("format") != FORMAT:
        raise FileFormatError([Problem("format", "file",
                                       f"format {data.get('format')!r} is not {FORMAT!r}")])
    version = data.get("format_version")
    if not (isinstance(version, int) and not isinstance(version, bool)):
        raise FileFormatError([Problem("format_version", "file", f"{version!r} is not a version")])
    if version > FORMAT_VERSION:
        raise FileFormatError([Problem("format_version", "file",
                                       f"version {version} is later than this program's "
                                       f"({FORMAT_VERSION}): open it with a later OGR FEM2D")])
    if version < 1:
        raise FileFormatError([Problem("format_version", "file", f"version {version} does not exist")])
    top = r.obj(data, "file", _TOP)
    if top is None:
        raise FileFormatError(r.problems)
    model = _model(r, top)
    if r.problems:
        raise FileFormatError(r.problems)
    return md.validate_document(model)


def _model(r: _Reader, d: dict) -> md.Model | None:
    r.typed(d["written_by"], "written_by", str)
    s = r.obj(d["summary"], "summary", ("title", "author", "date", "notes"))
    summary = md.Summary()
    if s is not None and all(r.typed(s[k], f"summary, {k}", str) for k in s):
        summary = md.Summary(s["title"], s["author"], s["date"], s["notes"])
    r.typed(d["units"], "units", str)
    r.typed(d["analysis"], "analysis", str)
    stages = []
    for k, st in enumerate(r.lst(d["stages"], "stages")):
        o = r.obj(st, f"stages, {k}", ("id", "name"))
        if o is not None and r.typed(o["id"], f"stages, {k}, id", str) \
                and r.typed(o["name"], f"stages, {k}, name", str):
            stages.append(md.Stage(o["id"], o["name"]))
    ids = [s.id for s in stages]
    return md.Model(
        analysis=d["analysis"], units=d["units"], summary=summary,
        boundaries=tuple(_boundaries(r, d["boundaries"])),
        materials=tuple(_materials(r, d["materials"])),
        stages=tuple(stages),
        assignments=tuple(_assignments(r, d["assignments"], ids)),
        field=_field(r, d["field_stress"]),
        default_restraint=d["default_restraint"] if r.typed(d["default_restraint"],
                                                            "default_restraint", str) else "",
        conditions=tuple(_conditions(r, d["conditions"], ids)),
        loads=tuple(_loads(r, d["loads"], ids)),
        mesh_settings=_mesh_settings(r, d["mesh_settings"]),
        mesh=_mesh(r, d["mesh"]))


def _boundaries(r, value):
    out = []
    for k, b in enumerate(r.lst(value, "boundaries")):
        w = f"boundaries, {k}"
        o = r.obj(b, w, ("id", "kind", "name", "closed", "vertices", "segments"))
        if o is None:
            continue
        ok = (r.typed(o["id"], f"{w}, id", str) & r.typed(o["kind"], f"{w}, kind", str)
              & r.typed(o["name"], f"{w}, name", str) & r.typed(o["closed"], f"{w}, closed", bool))
        vertices = tuple(r.point(v, f"{w}, vertex {i}") for i, v in enumerate(r.lst(o["vertices"], w)))
        segs = []
        for i, s in enumerate(r.lst(o["segments"], f"{w}, segments")):
            so = r.obj(s, f"{w}, segments, {i}", ("index", "arc", "divisions"))
            if so is None:
                continue
            if r.typed(so["index"], f"{w}, segments, {i}, index", int) and \
                    r.typed(so["divisions"], f"{w}, segments, {i}, divisions", int, nullable=True):
                segs.append(md.SegmentAttr(so["index"], r.point(so["arc"], f"{w}, segments, {i}, arc",
                                                                nullable=True), so["divisions"]))
        if ok:
            out.append(md.Boundary(o["id"], o["kind"], vertices, o["closed"], tuple(segs), o["name"]))
    return out


def _materials(r, value):
    out = []
    for k, x in enumerate(r.lst(value, "materials")):
        w = f"materials, {k}"
        o = r.obj(x, w, ("id", "name", "color", "E", "nu", "unit_weight", "initial_loading"))
        if o is None:
            continue
        if (r.typed(o["id"], f"{w}, id", str) & r.typed(o["name"], f"{w}, name", str)
                & r.typed(o["color"], f"{w}, color", str)
                & r.typed(o["E"], f"{w}, E", _NUM, nullable=True)
                & r.typed(o["nu"], f"{w}, nu", _NUM, nullable=True)
                & r.typed(o["unit_weight"], f"{w}, unit_weight", _NUM)
                & r.typed(o["initial_loading"], f"{w}, initial_loading", str)):
            out.append(md.Material(o["id"], o["name"], o["E"], o["nu"], o["unit_weight"],
                                   o["initial_loading"], o["color"]))
    return out


def _assignments(r, value, stages):
    out = []
    for k, a in enumerate(r.lst(value, "assignments")):
        w = f"assignments, {k}"
        o = r.obj(a, w, ("point", "material", "excavated"))
        if o is None:
            continue
        p = r.point(o["point"], f"{w}, point")
        exc = r.stage_map(o["excavated"], f"{w}, excavated", stages, bool)
        if r.typed(o["material"], f"{w}, material", str) and p is not None and exc is not None:
            out.append(md.Assignment(p, o["material"], exc))
    return out


def _field(r, value):
    if not isinstance(value, dict) or "kind" not in value:
        r.add("type", "field_stress", "is not an object with a kind")
        return md.ConstantField()
    if value["kind"] == "constant":
        o = r.obj(value, "field_stress", ("kind", "sigma_1", "sigma_3", "sigma_z", "angle"))
        if o is not None and all(r.typed(o[k], f"field_stress, {k}", _NUM)
                                 for k in ("sigma_1", "sigma_3", "sigma_z", "angle")):
            return md.ConstantField(o["sigma_1"], o["sigma_3"], o["sigma_z"], o["angle"])
        return md.ConstantField()
    if value["kind"] == "gravitational":
        o = r.obj(value, "field_stress", ("kind", "surface", "strata"))
        if o is None or not r.typed(o["surface"], "field_stress, surface", _NUM):
            return md.ConstantField()
        strata = []
        for k, s in enumerate(r.lst(o["strata"], "field_stress, strata")):
            so = r.obj(s, f"field_stress, strata, {k}", ("bottom", "unit_weight", "k", "kz"))
            if so is not None and all(r.typed(so[x], f"field_stress, strata, {k}, {x}", _NUM)
                                      for x in so):
                strata.append(Stratum(so["bottom"], so["unit_weight"], so["k"], so["kz"]))
        return md.GravityField(o["surface"], tuple(strata))
    r.add("type", "field_stress", f"kind {value['kind']!r} is not constant nor gravitational")
    return md.ConstantField()


def _span_of(r, value, where):
    if value is None:
        return None
    o = r.obj(value, where, ("boundary", "start", "end"))
    if o is None or not r.typed(o["boundary"], f"{where}, boundary", str):
        return None
    return md.Span(o["boundary"], r.point(o["start"], f"{where}, start", nullable=True),
                   r.point(o["end"], f"{where}, end", nullable=True))


def _conditions(r, value, stages):
    out = []
    keys = ("kind", "name", "span", "vertex", "active", "ux", "uy", "factors")
    for k, c in enumerate(r.lst(value, "conditions")):
        w = f"conditions, {k}"
        o = r.obj(c, w, keys)
        if o is None or not (r.typed(o["kind"], f"{w}, kind", str) & r.typed(o["name"], f"{w}, name", str)):
            continue
        disp = o["kind"] == md.DISPLACEMENT
        active = factors = ()
        if disp:
            if o["active"] is not None:
                r.add("type", f"{w}, active", "an imposed displacement has factors, not active flags")
            factors = r.stage_map(o["factors"], f"{w}, factors", stages, _NUM, nullable_values=True)
        else:
            if o["factors"] is not None:
                r.add("type", f"{w}, factors", "a restraint has active flags, not factors")
            active = r.stage_map(o["active"], f"{w}, active", stages, bool)
        if not (r.typed(o["ux"], f"{w}, ux", _NUM, nullable=True)
                & r.typed(o["uy"], f"{w}, uy", _NUM, nullable=True)):
            continue
        if active is None or factors is None:
            continue
        out.append(md.Condition(o["kind"], _span_of(r, o["span"], f"{w}, span"),
                                r.point(o["vertex"], f"{w}, vertex", nullable=True),
                                active, o["ux"], o["uy"], factors, o["name"]))
    return out


def _loads(r, value, stages):
    out = []
    for k, x in enumerate(r.lst(value, "loads")):
        w = f"loads, {k}"
        kind = x.get("type") if isinstance(x, dict) else None
        if kind == "distributed":
            o = r.obj(x, w, ("type", "name", "span", "start_value", "end_value", "orientation",
                             "angle", "factors"))
            if o is None:
                continue
            factors = r.stage_map(o["factors"], f"{w}, factors", stages, _NUM)
            span = _span_of(r, o["span"], f"{w}, span")
            if (all(r.typed(o[y], f"{w}, {y}", _NUM) for y in ("start_value", "end_value", "angle"))
                    and r.typed(o["orientation"], f"{w}, orientation", str)
                    and r.typed(o["name"], f"{w}, name", str)
                    and factors is not None and span is not None):
                out.append(md.DistributedLoad(span, o["start_value"], o["end_value"],
                                              o["orientation"], o["angle"], factors, o["name"]))
        elif kind == "point":
            o = r.obj(x, w, ("type", "name", "vertex", "magnitude", "orientation", "angle",
                             "factors"))
            if o is None:
                continue
            factors = r.stage_map(o["factors"], f"{w}, factors", stages, _NUM)
            vertex = r.point(o["vertex"], f"{w}, vertex")
            if (all(r.typed(o[y], f"{w}, {y}", _NUM) for y in ("magnitude", "angle"))
                    and r.typed(o["orientation"], f"{w}, orientation", str)
                    and r.typed(o["name"], f"{w}, name", str)
                    and factors is not None and vertex is not None):
                out.append(md.PointLoad(vertex, o["magnitude"], o["orientation"], o["angle"],
                                        factors, o["name"]))
        else:
            r.add("type", w, f"type {kind!r} is not distributed nor point")
    return out


def _mesh_settings(r, value):
    keys = ("kind", "nodes_per_element", "quality_bound", "boundary_nodes", "max_size", "size",
            "elements", "windows")
    o = r.obj(value, "mesh_settings", keys)
    if o is None:
        return g.MeshSettings()
    ok = (r.typed(o["kind"], "mesh_settings, kind", str)
          & r.typed(o["nodes_per_element"], "mesh_settings, nodes_per_element", int)
          & r.typed(o["quality_bound"], "mesh_settings, quality_bound", _NUM)
          & r.typed(o["boundary_nodes"], "mesh_settings, boundary_nodes", int, nullable=True)
          & r.typed(o["max_size"], "mesh_settings, max_size", _NUM, nullable=True)
          & r.typed(o["size"], "mesh_settings, size", _NUM, nullable=True)
          & r.typed(o["elements"], "mesh_settings, elements", int, nullable=True))
    windows = []
    for k, wv in enumerate(r.lst(o["windows"], "mesh_settings, windows")):
        wo = r.obj(wv, f"mesh_settings, windows, {k}", ("polygon", "size"))
        if wo is not None and r.typed(wo["size"], f"mesh_settings, windows, {k}, size", _NUM):
            windows.append(g.Window(tuple(r.point(p, f"mesh_settings, windows, {k}, point {i}")
                                          for i, p in enumerate(r.lst(wo["polygon"], "window"))),
                                    wo["size"]))
    if not ok:
        return g.MeshSettings()
    return g.MeshSettings(o["kind"], o["nodes_per_element"], o["quality_bound"],
                          o["boundary_nodes"], o["max_size"], o["size"], o["elements"],
                          tuple(windows))


def _mesh(r, value):
    if value is None:
        return None
    keys = ("source", "nodes", "elements", "element_region", "boundaries", "warnings", "notes")
    o = r.obj(value, "mesh", keys)
    if o is None:
        return None
    nodes = tuple(r.point(p, f"mesh, node {i}") for i, p in enumerate(r.lst(o["nodes"], "mesh, nodes")))
    elements = tuple(tuple(e) for e in r.lst(o["elements"], "mesh, elements") if isinstance(e, list))
    boundaries = []
    for k, b in enumerate(r.lst(o["boundaries"], "mesh, boundaries")):
        bo = r.obj(b, f"mesh, boundaries, {k}", ("name", "nodes", "sides", "mids"))
        if bo is None:
            continue
        boundaries.append(MeshBoundary(bo["name"], tuple(bo["nodes"]),
                                       tuple(tuple(tuple(s) for s in piece) for piece in bo["sides"]),
                                       tuple(bo["mids"])))
    r.typed(o["source"], "mesh, source", str)
    if not isinstance(o["notes"], dict):
        r.add("type", "mesh, notes", "is not an object")
    return md.StoredMesh(nodes, elements, tuple(r.lst(o["element_region"], "mesh, element_region")),
                         tuple(boundaries), o["notes"], tuple(r.lst(o["warnings"], "mesh, warnings")),
                         o["source"])


def loads(text: str) -> md.Model:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        raise FileFormatError([Problem("format", "file", f"is not JSON: {err}")]) from None
    return from_dict(data)


def read(path) -> md.Model:
    return loads(Path(path).read_bytes().decode("utf-8"))
