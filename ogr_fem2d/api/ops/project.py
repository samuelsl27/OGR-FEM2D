# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The operations on a whole model: new, open, save, close, list, its summary
and its settings (spec 006, T11; RF-6 to RF-8).

The names are those of OGR Slip2D where they do the same (``project_new``,
``project_open``, ``project_save``, ``project_close``, ``project_list``,
``project_summary``, ``project_validate``): an agent that knows one program
knows the other.

* ``project_open`` opens a ``.ogrfem2d``, and also a ``.ogr`` of OGR Slip2D
  or a ``.dxf``, converting them (spec 004, D13 and D16): those come as a
  new model without a file, with the report of what was brought, what not,
  what was set by default and what was changed;
* ``project_save`` writes a ``.ogrfem2d``, also of a model being drawn (a
  file holds a model valid as a document, spec 004 as modified in T11), and
  never replaces another file unless told to; ``project_close`` refuses to lose unsaved changes unless
  told to;
* ``project_settings`` edits the kind of analysis, the units shown and the
  summary, as one undo step.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Optional

from ogr_core.api import Conflict, InvalidArgument, unknown
from ogr_core.api.coerce import coerce_value
from ogr_core.units.unit_system import SYSTEMS

from ...model import edit as ed
from ...model import import_dxf, import_slip2d, ogr_file, translate
from ...model import model as md
from ..messages import say
from ..registry import OPERATIONS
from ..workspace import Held, edit, model_errors

SUFFIX = ".ogrfem2d"
OPENS = (SUFFIX, ".ogr", ".dxf")


def _text(value, where: str) -> str:
    if not isinstance(value, str):
        raise InvalidArgument(say("fem.argument.text", where=where))
    return value


def _one_of(value, options, kind: str) -> str:
    if value not in options:
        raise unknown(kind, value, list(options))
    return value


def mesh_state(m: md.Model) -> str:
    """``none``, ``stale`` (of another geometry or settings) or ``current``."""
    if m.mesh is None:
        return "none"
    return "current" if m.mesh.source == translate.source_of(m) else "stale"


def summary_of(handle) -> dict:
    m = handle.project.model
    return {
        "project_id": handle.id, "name": m.summary.title,
        "path": str(handle.path) if handle.path else None,
        "unsaved": handle.unsaved(),
        "analysis": m.analysis, "units": m.units,
        "boundaries": [{"id": b.id, "kind": b.kind, "name": b.name, "closed": b.closed,
                        "vertices": len(b.vertices)} for b in m.boundaries],
        "materials": [{"id": x.id, "name": x.name, "complete": x.E is not None and x.nu is not None}
                      for x in m.materials],
        "stages": [{"id": s.id, "name": s.name} for s in m.stages],
        "assignments": len(m.assignments), "conditions": len(m.conditions),
        "loads": len(m.loads),
        "mesh": {"state": mesh_state(m),
                 "nodes": len(m.mesh.nodes) if m.mesh else 0,
                 "elements": len(m.mesh.elements) if m.mesh else 0},
        "problems": [{"rule": p.rule, "where": p.where, "message": p.message}
                     for p in md.problems(m)],
    }


def _report(rep: import_slip2d.Report) -> dict:
    return asdict(rep)


# ---------------------------------------------------------------- open
@OPERATIONS.operation("project_new", toolset="core")
def project_new(ws, name: str = "", analysis: str = md.ANALYSES[0],
                units: str = md.DEFAULT_UNITS) -> dict:
    """Create an empty model and return its project_id."""
    name = _text(name, "name")
    _one_of(analysis, md.ANALYSES, "analysis")
    _one_of(units, tuple(SYSTEMS), "unit system")
    m = md.Model(analysis=analysis, units=units, summary=md.Summary(title=name))
    handle = ws.add(Held(m))
    return {"project_id": handle.id, "name": name, "analysis": analysis, "units": units}


@OPERATIONS.operation("project_open", toolset="core")
def project_open(ws, path: str) -> dict:
    """Open a .ogrfem2d file, or convert a .ogr of OGR Slip2D or a .dxf
    into a new model; return its project_id, what is still unfinished in it
    (its problems) and, for a conversion, the report of what it did."""
    p = ws.resolve_path(_text(path, "path"))
    suffix = p.suffix.lower()
    if suffix not in OPENS:
        raise InvalidArgument(say("fem.file.kind", name=p.name))
    report = None
    with model_errors():
        if suffix == SUFFIX:
            m = ogr_file.read(p)
        elif suffix == ".ogr":
            m, rep = import_slip2d.open_slip2d(p)
            report = _report(rep)
        else:
            boundaries, rep = import_dxf.boundaries_from_dxf(p)
            m = md.Model(boundaries=boundaries, summary=md.Summary(title=p.stem))
            report = _report(rep)
    handle = ws.add(Held(m), path=p if suffix == SUFFIX else None)
    out = {"project_id": handle.id, "name": m.summary.title,
           "path": str(p) if suffix == SUFFIX else None, "converted_from": None,
           "problems": [{"rule": x.rule, "where": x.where, "message": x.message}
                        for x in md.problems(m)]}
    if report is not None:
        out["converted_from"] = str(p)
        out["report"] = report
    return out


# ---------------------------------------------------------------- save
@OPERATIONS.operation("project_save", toolset="core")
def project_save(ws, project_id: Optional[str] = None, path: Optional[str] = None,
                 overwrite: bool = False) -> dict:
    """Write the model to its .ogrfem2d (or to ``path``); another existing
    file is never replaced unless ``overwrite``."""
    handle = ws.get(project_id)
    overwrite = coerce_value(overwrite, bool, "overwrite")
    if path is None:
        if handle.path is None:
            raise InvalidArgument(say("fem.save.no_path", model=handle.id),
                                  hint=say("fem.save.no_path.hint"))
        target = Path(handle.path)
    else:
        name = Path(_text(path, "path")).name
        if Path(path).suffix and Path(path).suffix.lower() != SUFFIX:
            raise InvalidArgument(say("fem.save.kind", name=name))
        target = ws.resolve_path(path, for_write=True, overwrite=overwrite, suffix=SUFFIX,
                                 own_file=handle.path)
    with ws.reading(handle.id, "save") as held, model_errors():
        ogr_file.write(held.model, target)
        handle.path = target
        handle.saved_hash = handle.document_hash()
    return {"project_id": handle.id, "path": str(target)}


@OPERATIONS.operation("project_close", toolset="core")
def project_close(ws, project_id: Optional[str] = None, discard_changes: bool = False) -> dict:
    """Close a model, refusing to lose unsaved changes unless told to."""
    handle = ws.get(project_id)
    discard = coerce_value(discard_changes, bool, "discard_changes")
    dirty = handle.unsaved()
    if dirty and not discard:
        raise Conflict(say("fem.close.unsaved", model=handle.id),
                       hint=say("fem.close.unsaved.hint"))
    ws.close(handle.id)
    return {"closed": handle.id, "discarded_changes": bool(dirty)}


@OPERATIONS.operation("project_list", toolset="core")
def project_list(ws) -> dict:
    """Every open model."""
    return {"projects": [{"project_id": h.id, "name": h.project.name,
                          "path": str(h.path) if h.path else None, "unsaved": h.unsaved()}
                         for h in ws.projects.values()]}


# ------------------------------------------------------------- the model
@OPERATIONS.operation("project_summary", toolset="core")
def project_summary(ws, project_id: Optional[str] = None) -> dict:
    """What the model holds, the state of its mesh, and its problems."""
    handle = ws.get(project_id)
    with ws.reading(handle.id, "summary"):
        return summary_of(handle)


@OPERATIONS.operation("project_validate", toolset="core")
def project_validate(ws, project_id: Optional[str] = None) -> dict:
    """Whether the model can be calculated, and every reason it cannot:
    its problems, the state of its mesh, the materials without E or nu."""
    handle = ws.get(project_id)
    with ws.reading(handle.id, "validate") as held:
        m = held.model
        found = [{"rule": p.rule, "where": p.where, "message": p.message} for p in md.problems(m)]
        mesh = mesh_state(m)
        missing = [x.id for x in m.materials if x.E is None or x.nu is None]
        return {"project_id": handle.id, "ready": not found and mesh == "current" and not missing,
                "problems": found, "mesh": mesh, "materials_incomplete": missing}


@OPERATIONS.operation("project_settings", toolset="core", mutates=True)
def project_settings(ws, project_id: Optional[str] = None, analysis: Optional[str] = None,
                     units: Optional[str] = None, title: Optional[str] = None,
                     author: Optional[str] = None, date: Optional[str] = None,
                     notes: Optional[str] = None) -> dict:
    """Change the kind of analysis, the unit system shown (the values do
    not change) or the summary, as one undo step."""
    summary = {k: _text(v, k) for k, v in (("title", title), ("author", author), ("date", date),
                                           ("notes", notes)) if v is not None}
    if analysis is not None:
        _one_of(analysis, md.ANALYSES, "analysis")
    if units is not None:
        _one_of(units, tuple(SYSTEMS), "unit system")

    def change(m):
        if analysis is not None:
            m = ed.set_analysis(m, analysis)
        if units is not None:
            m = ed.set_units(m, units)
        if summary:
            m = ed.set_summary(m, **summary)
        return m

    handle, m = edit(ws, project_id, say("fem.step.project_settings"), change)
    return {"project_id": handle.id, "analysis": m.analysis, "units": m.units,
            "summary": asdict(m.summary)}
