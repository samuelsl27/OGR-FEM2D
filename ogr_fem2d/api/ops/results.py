# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The operations on the results of a model (spec 006, T14; RF-6; spec 005):
their state, the queries, the summary by stage, the table, the report and
the field ready to be drawn.

* ``results_open`` says the state of the ``.h5`` beside the model's file
  (spec 005, RF-3): valid, stale, incomplete, cancelled, missing or damaged,
  and who wrote it;
* the others read it **only when it is valid**, unless ``allow_invalid``:
  then every answer carries the state it was read in, so a value of stale
  results is never taken for a valid one;
* values are in the units the results keep (m, kN, kPa) and in the user's
  convention (compression positive), and every answer says its unit, its
  convention and the settings that decided it (rule 12). The table is the
  exception: it is written in the units the model shows (spec 005, D15).

A stage is given by its id, the last one by default. The values a query
recovers at the nodes are worked out once per stage and kept with the
results while the model does not change.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from ogr_core.api import InvalidArgument, NotConfigured, unknown
from ogr_core.api.coerce import coerce_value, point, points

from ...report import info
from ...results import calculate as calc
from ...results import drawing, queries, table
from ...results import quantities as qt
from ..messages import say
from ..registry import OPERATIONS

QUERY_KINDS = ("line", "boundary", "nodes", "points", "at", "history")


def _entry(ws, handle) -> dict:
    """The results of the handle's model as opened, and their views."""
    # the results as opened, and their views (with the values they recover),
    # are kept while neither the model nor its results file change: the
    # state is of those two (v0.0.15: opening again for every question
    # took 0.1 s with the mesh of case 005, the cursor asks many)
    h5 = calc.results_path(handle.path)
    st = h5.stat() if h5.exists() else None
    stamp = None if st is None else (st.st_mtime_ns, st.st_size)
    key = (str(handle.path), handle.document_hash(), stamp)
    cache = handle.exec_ns.setdefault("_results", {})
    if key not in cache:
        with ws.reading(handle.id, "results") as held:
            opened = calc.open_results(handle.path, held.model)
        cache.clear()
        cache[key] = {"opened": opened, "views": {}}
    return cache[key]


def _results_of(ws, project_id, allow_invalid: bool):
    """(handle, the opened results, the results) for a question."""
    handle = ws.get(project_id)
    if handle.path is None:
        raise InvalidArgument(say("fem.run.no_file", model=handle.id),
                              hint=say("fem.run.no_file.hint"))
    entry = _entry(ws, handle)
    opened = entry["opened"]
    if opened.status != calc.VALID and not coerce_value(allow_invalid, bool, "allow_invalid"):
        raise NotConfigured(say("fem.results.not_valid", status=opened.status,
                                message=opened.message or "-"),
                            hint=say("fem.results.not_valid.hint"))
    try:
        r = opened.read_anyway()
    except calc.NotValidError:
        raise NotConfigured(say("fem.results.not_valid", status=opened.status,
                                message=opened.message or "-"),
                            hint=say("fem.results.not_valid.hint")) from None
    return handle, opened, r, entry["views"]


def _view(r, views, stage):
    ids = [r.stage_info(k)["id"] for k in range(r.n_stages)]
    if stage is None:
        k = r.n_stages - 1
    elif stage in ids:
        k = ids.index(stage)
    else:
        raise unknown("stage of the results", stage, ids)
    if k not in views:
        views[k] = queries.View(r, k)
    return views[k]


def _quantity(quantity: str) -> str:
    ids = [q.id for q in qt.CATALOGUE]
    if quantity not in ids:
        raise unknown("quantity", quantity, ids)
    return quantity


def _row(r: queries.Row) -> dict:
    return {"point": r.point, "x": r.x, "y": r.y, "distance": r.distance, "value": r.value,
            "element": r.element, "material": r.material, "source": r.source, "reason": r.reason}


def _query_dict(q: queries.Query, opened) -> dict:
    return {"state": opened.status, "quantity": q.quantity, "stage": q.stage_id, "what": q.what,
            "unit": q.unit, "convention": q.convention, "method": q.method,
            "settings": [[k, v] for k, v in q.settings], "rows": [_row(r) for r in q.rows]}


@OPERATIONS.operation("results_open", toolset="results")
def results_open(ws, project_id: Optional[str] = None) -> dict:
    """The state of the results beside the model's file (valid, stale,
    incomplete, cancelled, missing, damaged), who wrote them and their
    stages."""
    handle = ws.get(project_id)
    if handle.path is None:
        raise InvalidArgument(say("fem.run.no_file", model=handle.id),
                              hint=say("fem.run.no_file.hint"))
    opened = _entry(ws, handle)["opened"]
    out = {"project_id": handle.id, "state": opened.status, "message": opened.message,
           "other_version": opened.other_version, "path": str(opened.path), "stages": []}
    try:
        r = opened.read_anyway()
    except calc.NotValidError:
        return out
    out["stages"] = [{k: r.stage_info(i)[k] for k in ("id", "name", "solved", "steps")}
                     for i in range(r.n_stages)]
    out["engine"] = r.header.engine_variant
    return out


def _query(handle, view, r, quantity, kind, points_xy, n, boundary, distance, side, x, y):
    """The query asked; what the query refuses (a line with two points the
    same, a distance without its side...) as an ``InvalidArgument`` that
    says it (RF-7; v0.0.15, T32: it escaped as a ValueError)."""
    try:
        return _ask(handle, view, r, quantity, kind, points_xy, n, boundary, distance, side,
                    x, y)
    except ValueError as err:
        raise InvalidArgument(say("fem.query.refused", what=str(err))) from None


def _ask(handle, view, r, quantity, kind, points_xy, n, boundary, distance, side, x, y):
    if kind == "line":
        return queries.line(view, quantity, points(points_xy, "points_xy"),
                            None if n is None else coerce_value(n, int, "n"))
    if kind == "boundary":
        with_model = handle.project.model
        if with_model.boundary(boundary) is None:
            raise unknown("boundary", boundary, [b.id for b in with_model.boundaries])
        return queries.on_boundary(view, quantity, with_model, boundary,
                                   None if n is None else coerce_value(n, int, "n"),
                                   coerce_value(distance, float, "distance"), side)
    if kind == "nodes":
        return queries.all_nodes(view, quantity)
    if kind == "points":
        return queries.all_points(view, quantity)
    if kind == "at":
        if x is None or y is None:
            raise InvalidArgument(say("fem.results.at_needs_xy"))
        return queries.at(view, quantity, coerce_value(x, float, "x"), coerce_value(y, float, "y"))
    return queries.history(r, quantity, coerce_value(x, float, "x"), coerce_value(y, float, "y"))


@OPERATIONS.operation("results_query", toolset="results")
def results_query(ws, quantity: str, kind: str, project_id: Optional[str] = None,
                  stage: Optional[str] = None, points_xy: Optional[list] = None,
                  n: Optional[int] = None, boundary: Optional[str] = None,
                  distance: float = 0.0, side: Optional[str] = None,
                  x: Optional[float] = None, y: Optional[float] = None,
                  allow_invalid: bool = False) -> dict:
    """A quantity along a line or polyline (points_xy; n points along it, or
    its vertices), on a boundary (at distance to a side), at every node, at
    every integration point, at (x, y) in the stage (at), or at (x, y)
    through the stages (history)."""
    quantity = _quantity(quantity)
    if kind not in QUERY_KINDS:
        raise unknown("query kind", kind, list(QUERY_KINDS))
    handle, opened, r, views = _results_of(ws, project_id, allow_invalid)
    if kind == "history":
        h = _query(handle, None, r, quantity, kind, points_xy, n, boundary, distance, side, x, y)
        q = qt.get(quantity)
        return {"state": opened.status, "quantity": quantity, "what": "history", "unit": q.unit,
                "convention": q.convention, "x": h.x, "y": h.y,
                "stages": [{"stage": s.stage_id, "name": s.name, "solved": s.solved,
                            "rows": [_row(row) for row in s.rows]} for s in h.stages]}
    view = _view(r, views, stage)
    q = _query(handle, view, r, quantity, kind, points_xy, n, boundary, distance, side, x, y)
    return _query_dict(q, opened)


@OPERATIONS.operation("results_summary", toolset="results")
def results_summary(ws, project_id: Optional[str] = None, stage: Optional[str] = None,
                    quantities: Optional[list] = None, allow_invalid: bool = False) -> dict:
    """The extremes of each quantity at the points and at the nodes, where
    they are; the greatest displacement; the reactions, in total and (with
    valid results) by boundary."""
    handle, opened, r, views = _results_of(ws, project_id, allow_invalid)
    view = _view(r, views, stage)
    ids = None if quantities is None else [_quantity(q) for q in quantities]
    s = queries.summary(view, handle.project.model if opened.status == calc.VALID else None, ids)
    return {"state": opened.status, "stage": s.stage_id,
            "extremes": [{"quantity": e.quantity, "at": e.at, "max": e.maximum,
                          "max_where": list(e.max_where), "min": e.minimum,
                          "min_where": list(e.min_where)} for e in s.extremes],
            "max_displacement": s.max_displacement, "max_displacement_node": s.max_displacement_node,
            "reactions": list(s.reactions),
            "reactions_by_boundary": [[b, rx, ry] for b, rx, ry in s.reactions_by_boundary]}


@OPERATIONS.operation("results_table", toolset="results")
def results_table(ws, path: str, quantity: str, kind: str, project_id: Optional[str] = None,
                  stage: Optional[str] = None, points_xy: Optional[list] = None,
                  n: Optional[int] = None, boundary: Optional[str] = None,
                  distance: float = 0.0, side: Optional[str] = None,
                  x: Optional[float] = None, y: Optional[float] = None,
                  overwrite: bool = False, allow_invalid: bool = False) -> dict:
    """Write a query as a CSV table (spec 005, D15), in the units the model
    shows; another existing file is not replaced unless ``overwrite``."""
    quantity = _quantity(quantity)
    if kind not in QUERY_KINDS:
        raise unknown("query kind", kind, list(QUERY_KINDS))
    target = ws.resolve_path(path, for_write=True, overwrite=coerce_value(overwrite, bool,
                                                                         "overwrite"),
                             suffix=".csv")
    handle, opened, r, views = _results_of(ws, project_id, allow_invalid)
    view = None if kind == "history" else _view(r, views, stage)
    q = _query(handle, view, r, quantity, kind, points_xy, n, boundary, distance, side, x, y)
    m = handle.project.model
    table.write(target, q, units=m.units, analysis=m.analysis,
                fingerprint=r.header.model_fingerprint)
    return {"state": opened.status, "path": str(target)}


@OPERATIONS.operation("results_report", toolset="results")
def results_report(ws, project_id: Optional[str] = None, format: str = "text",
                   path: Optional[str] = None, overwrite: bool = False) -> dict:
    """The report of the model and of its results (text or html), and, with
    ``path``, written to that file."""
    if format not in ("text", "html"):
        raise unknown("report format", format, ["text", "html"])
    handle = ws.get(project_id)
    with ws.reading(handle.id, "report") as held:
        opened = calc.open_results(handle.path, held.model) if handle.path else None
        sections = info.report(held.model, opened)
    text = info.to_text(sections) if format == "text" else info.to_html(sections)
    out = {"project_id": handle.id, "format": format, "state": opened.status if opened else None}
    if path is not None:
        target = ws.resolve_path(path, for_write=True,
                                 overwrite=coerce_value(overwrite, bool, "overwrite"),
                                 suffix=".txt" if format == "text" else ".html")
        Path(target).write_text(text, encoding="utf-8")
        out["path"] = str(target)
    else:
        out["report"] = text
    return out


@OPERATIONS.operation("results_field", toolset="results")
def results_field(ws, quantity: str, project_id: Optional[str] = None,
                  stage: Optional[str] = None, level: int = drawing.DEFAULT_LEVEL,
                  absolute: bool = False, range_mode: str = drawing.AUTO_STAGE,
                  low: Optional[float] = None, high: Optional[float] = None,
                  allow_invalid: bool = False, as_arrays: bool = False) -> dict:
    """A quantity ready to be drawn: the triangles of every active element
    subdivided (level), their values and the range of the legend
    (auto_stage, auto_all or custom). With ``as_arrays`` the arrays as they
    are (for the interface, in the same process); otherwise as lists."""
    quantity = _quantity(quantity)
    handle, opened, r, views = _results_of(ws, project_id, allow_invalid)
    view = _view(r, views, stage)
    lvl = coerce_value(level, int, "level")
    ab = coerce_value(absolute, bool, "absolute")
    try:
        f = drawing.field(view, quantity, lvl, ab)
        rng = drawing.value_range(view, quantity, range_mode, lvl, ab,
                                  None if low is None else coerce_value(low, float, "low"),
                                  None if high is None else coerce_value(high, float, "high"),
                                  views=views, drawn=f)
    except ValueError as err:
        raise InvalidArgument(say("fem.field.refused", what=str(err))) from None
    q = qt.get(quantity)
    out = {"state": opened.status, "quantity": quantity, "stage": view.info["id"],
           "unit": q.unit, "convention": q.convention, "level": lvl, "absolute": ab,
           "range": list(rng), "range_mode": range_mode}
    arrays = {"xy": f.xy, "triangles": f.triangles, "values": f.values,
              "element": f.element, "material": f.material}
    if coerce_value(as_arrays, bool, "as_arrays"):
        out.update(arrays)
    else:
        out.update({k: np.asarray(v).tolist() for k, v in arrays.items()})
    return out
