# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The operations of the mesh (spec 006, T12; RF-12, RF-14): its settings, the
first step (``mesh_discretize``: the nodes the boundaries will have, without
changing the model) and the mesh itself (``mesh_generate``), and taking it
away (``mesh_reset``). The names are OGR Slip2D's where they do the same.

The mesh kept with the model is the mesh of its geometry and settings when
it was made: after an edit of either it is the mesh of another geometry,
``project_validate`` says ``stale`` and calculating is refused (spec 004,
RF-11); it is not deleted (the reference program deleted it, P10).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Optional

from ogr_core.api import Conflict, InvalidArgument, unknown
from ogr_core.api.coerce import coerce_value, points

from ...mesh import discretize
from ...mesh import geometry as g
from ...model import edit as ed
from ...model import model as md
from ...model import regions, translate
from ..messages import say
from ..registry import OPERATIONS
from ..workspace import edit, model_errors
from .project import mesh_state

_SETTINGS = {"kind": str, "nodes_per_element": int, "quality_bound": float,
             "boundary_nodes": int, "max_size": float, "size": float, "elements": int}


@OPERATIONS.operation("mesh_settings", toolset="mesh", mutates=True)
def mesh_settings(ws, project_id: Optional[str] = None, kind: Optional[str] = None,
                  nodes_per_element: Optional[int] = None, quality_bound: Optional[float] = None,
                  boundary_nodes: Optional[int] = None, max_size: Optional[float] = None,
                  size: Optional[float] = None, elements: Optional[int] = None,
                  windows: Optional[list] = None, clear: Optional[list] = None) -> dict:
    """Change the settings of the mesher (spec 003): kind (graded or
    uniform), nodes_per_element (3 or 6), quality_bound (B), boundary_nodes
    (graded: nodes on the excavations, or on the external without any),
    max_size, size or elements (uniform), windows ([{polygon, size}]).
    ``clear`` lists the settings to set back to none."""
    given = {k: coerce_value(v, _SETTINGS[k], k) for k, v in (
        ("kind", kind), ("nodes_per_element", nodes_per_element), ("quality_bound", quality_bound),
        ("boundary_nodes", boundary_nodes), ("max_size", max_size), ("size", size),
        ("elements", elements)) if v is not None}
    for name in clear or ():
        if name not in ("boundary_nodes", "max_size", "size", "elements"):
            raise unknown("setting that can be none", name,
                          ["boundary_nodes", "max_size", "size", "elements"])
        if name in given:
            raise InvalidArgument(say("fem.mesh.clear_and_set", name=name))
        given[name] = None
    if windows is not None:
        ws_ = []
        for k, w in enumerate(windows):
            if not isinstance(w, dict) or set(w) != {"polygon", "size"}:
                raise InvalidArgument(say("fem.windows.shape", index=k))
            ws_.append(g.Window(tuple(points(w["polygon"], f"windows[{k}].polygon", 3)),
                                coerce_value(w["size"], float, f"windows[{k}].size")))
        given["windows"] = tuple(ws_)
    handle, m = edit(ws, project_id, say("fem.step.mesh_settings"),
                     lambda m: ed.set_mesh_settings(m, **given))
    st = m.mesh_settings
    return {"project_id": handle.id, "settings": {
        "kind": st.kind, "nodes_per_element": st.nodes_per_element,
        "quality_bound": st.quality_bound, "boundary_nodes": st.boundary_nodes,
        "max_size": st.max_size, "size": st.size, "elements": st.elements,
        "windows": [{"polygon": [list(p) for p in w.polygon], "size": w.size}
                    for w in st.windows]}, "mesh": mesh_state(m)}


@OPERATIONS.operation("mesh_discretize", toolset="mesh")
def mesh_discretize(ws, project_id: Optional[str] = None) -> dict:
    """The first step of meshing: the nodes every segment of the geometry
    will have, with the settings of now, without changing the model."""
    handle = ws.get(project_id)
    with ws.reading(handle.id, "discretize") as held, model_errors():
        mi = translate.to_mesh_input(held.model)
        try:
            d = discretize.discretize(mi)
        except g.MeshInputError as err:
            geo = regions.build(held.model)
            raise md.ModelError([translate._name_mesh_problem(p, geo)
                                 for p in err.problems]) from None
    return {"project_id": handle.id, "size": d.size,
            "segments": [{"from": list(mi.points[s.segment.a]), "to": list(mi.points[s.segment.b]),
                          "divisions": s.divisions,
                          "nodes": [list(d.points[i]) for i in s.nodes]} for s in d.segments]}


@OPERATIONS.operation("mesh_generate", toolset="mesh", mutates=True)
def mesh_generate(ws, project_id: Optional[str] = None, background: bool = False,
                  wait: float = 0.0) -> dict:
    """Mesh the geometry with its settings, and keep the mesh with the
    model; what decided it (the notes of the mesher) and its warnings. With
    ``background``, in a child process that can be cancelled (job_cancel):
    it returns the job_id, and ``mesh_collect`` puts the mesh in the model
    when the job is done."""
    if coerce_value(background, bool, "background"):
        return _start(ws, project_id, coerce_value(wait, float, "wait"))
    handle, m = edit(ws, project_id, say("fem.step.mesh_generate"), translate.mesh)
    return _meshed(handle, m)


def _meshed(handle, m) -> dict:
    notes = m.mesh.notes
    quality = notes.get("quality", {})
    return {"project_id": handle.id, "nodes": len(m.mesh.nodes),
            "elements": len(m.mesh.elements), "nodes_per_element": notes.get("nodes_per_element"),
            "quality_bound": notes.get("quality_bound"),
            "angle_guaranteed": notes.get("angle_guaranteed"),
            "min_angle": quality.get("min_angle", {}).get("worst"),
            "arc_termination_proven": notes.get("arc_termination_proven"),
            "warnings": list(m.mesh.warnings)}


def _start(ws, project_id, wait: float) -> dict:
    """The job of meshing; what would fail at once is refused here."""
    from .. import worker
    handle = ws.get(project_id)
    with ws.reading(handle.id, "mesh") as held, model_errors():
        m = held.model
        mi = translate.to_mesh_input(m)
        try:
            discretize.discretize(mi)
        except g.MeshInputError as err:
            geo = regions.build(m)
            raise md.ModelError([translate._name_mesh_problem(p, geo)
                                 for p in err.problems]) from None
        job = ws.jobs.start("mesh", {"model": m}, handle.id, handle.document_hash(), {},
                            target=worker.run_mesh)
    out = {"job_id": job.id, "project_id": handle.id}
    if wait > 0:
        job.wait(wait)
    out["state"] = job.status()["state"]
    return out


@OPERATIONS.operation("mesh_collect", toolset="mesh", mutates=True)
def mesh_collect(ws, job_id: str) -> dict:
    """Put in the model the mesh a job of ``mesh_generate`` made, as one step
    to undo; refused if the job is not done, or if the model changed while
    it ran (mesh again)."""
    job = ws.jobs.get(job_id)
    if job.kind != "mesh":
        raise InvalidArgument(say("fem.mesh.not_a_mesh_job", job=job_id))
    state = job.status()["state"]
    if state != "done":
        raise Conflict(say("fem.mesh.job_not_done", job=job_id, state=state))
    handle = ws.get(job.project_id)
    if handle.document_hash() != job.model_hash:
        raise Conflict(say("fem.mesh.model_changed", model=handle.id),
                       hint=say("fem.mesh.model_changed.hint"))
    mesh = job.load_results()
    from dataclasses import replace
    handle, m = edit(ws, handle.id, say("fem.step.mesh_generate"),
                     lambda m: replace(m, mesh=mesh))
    return {**_meshed(handle, m), "job_id": job_id}


@OPERATIONS.operation("mesh_reset", toolset="mesh", mutates=True)
def mesh_reset(ws, project_id: Optional[str] = None) -> dict:
    """Take the mesh away from the model."""
    from dataclasses import replace
    handle, m = edit(ws, project_id, say("fem.step.mesh_reset"), lambda m: replace(m, mesh=None))
    return {"project_id": handle.id, "mesh": mesh_state(m)}
