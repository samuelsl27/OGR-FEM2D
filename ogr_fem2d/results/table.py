# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A query as a table (spec 005, RF-14; D15).

CSV in UTF-8, a point as the decimal mark, every number written so that it
reads back the same (Python's repr). First, comment lines (``#``) that
declare what the table is: the program, the quantity and its name, the unit,
the convention, the stage, the method, the kind of query and the model's
fingerprint. Then the fixed columns, identifiers and not translated text,
so that a script that reads them does not break with the language
(the first five are those of the reference's query tables):

    query_id, point, x, y, distance, value, element, material, source

``value`` is empty where there is none, and ``source`` then says why
(``excavated``, ``outside``, ``removed``). Lengths and values are in the
units of the system the model shows (``ogr_core.units``, its ``to_user``):
the results keep m, kN and kPa (D15). A history (``queries.History``) is a
table with a row per stage: ``point`` is the stage's index.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import csv
import io

from ogr_core.units import Quantity as Q
from ogr_core.units.unit_system import get_system

import ogr_fem2d
from . import quantities as qt
from .queries import History, Query, Row

COLUMNS = ("query_id", "point", "x", "y", "distance", "value", "element", "material", "source")
_UNITS = {qt.PRESSURE: Q.PRESSURE, qt.LENGTH: Q.LENGTH}


def _number(v) -> str:
    return "" if v is None else repr(float(v))


def to_csv(query: Query | History, units: str = "metric_kpa", analysis: str = "plane_strain",
           fingerprint: str = "", query_id: int = 1) -> str:
    system = get_system(units)
    if system.id != units:
        raise ValueError(f"unknown unit system {units!r}")
    q = qt.get(query.quantity)
    unit = _UNITS.get(q.unit)
    label = system.label_for(unit) if unit else ("degrees" if q.unit == qt.ANGLE else "-")
    length = system.label_for(Q.LENGTH)

    def value(v):
        return None if v is None else (system.to_user(v, unit) if unit else v)

    def coord(v):
        return None if v is None else system.to_user(v, Q.LENGTH)

    if isinstance(query, History):
        rows = [Row(s.stage, query.x, query.y, None, r.value, r.element, r.material,
                    r.source, r.reason) for s in query.stages for r in s.rows]
        head = [f"history at ({query.x!r}, {query.y!r}): a row per stage, its index in 'point'",
                "stages: " + ", ".join(f"{s.stage}={s.stage_id}" + ("" if s.solved else " (not solved)")
                                       for s in query.stages)]
        method = "as each stage's query"
    else:
        rows = list(query.rows)
        head = [f"query: {query.what}", f"stage: {query.stage} (id {query.stage_id})"]
        if query.settings:
            head.append("settings: " + "; ".join(f"{k} = {v}" for k, v in query.settings))
        method = query.method
    out = io.StringIO()
    lines = [f"OGR FEM2D {ogr_fem2d.__version__}",
             f"quantity: {q.id} ({q.name(analysis)})",
             f"unit: {label}; coordinates and distance: {length}",
             f"convention: {q.convention}", *head, f"method: {method}",
             f"model_fingerprint: {fingerprint}"]
    for line in lines:
        out.write(f"# {line}\n")
    w = csv.writer(out, lineterminator="\n")
    w.writerow(COLUMNS)
    for r in rows:
        w.writerow([query_id, r.point, _number(coord(r.x)), _number(coord(r.y)),
                    _number(coord(r.distance)), _number(value(r.value)),
                    "" if r.element is None else r.element,
                    "" if r.material is None else r.material,
                    r.source if r.value is not None else r.reason])
    return out.getvalue()


def write(path, query: Query | History, **kwargs) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(to_csv(query, **kwargs))
