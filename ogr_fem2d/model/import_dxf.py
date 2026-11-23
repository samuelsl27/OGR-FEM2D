# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Opening a DXF: its polylines, by layer, as the boundaries of a model (spec
004, RF-14, D13).

The drawing is read by the core's reader (``ogr_core.dxf.reader.read_dxf``:
LINE, LWPOLYLINE and POLYLINE, ARC, CIRCLE and SPLINE, in metres). Its
layers go to the four kinds of boundary by name, matched as the core
matches them (case and separators ignored): the core's names for the
external and the material boundaries, and these for the excavation and the
stage ones. A layer that is none of the four does not come, and the report
says so.

The core's reader FLATTENS the arcs (ARC, CIRCLE, SPLINE and the curved
pieces of a polyline) into straight pieces: they come as polylines, and the
mid-side nodes of a six-node mesh go on the chords, not on the circle. The
report says how many curved entities there were. A reader that keeps the
arcs is asked of the core (D13; it does not block this).

The boundaries come as they are drawn: a model needs them to meet only at
shared vertices (D15), and its validation says where they do not. The
materials, assignments, stages and conditions are the user's to give.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from pathlib import Path

from ogr_core.dxf import reader

from . import model as md
from .import_slip2d import Report

#: Layer names of the excavation and stage boundaries (the core knows the
#: external and the material ones).
LAYERS = {
    md.EXCAVATION: ("OGR_EXCAVATION", "EXCAVATION", "EXCAVACION", "EXCAVACIÓN", "TUNEL",
                    "TÚNEL", "TUNNEL"),
    md.STAGE: ("OGR_STAGE", "STAGE", "FASE", "FASES", "STAGEBOUNDARY", "CONTORNO_FASE"),
}

CURVED = ("ARC", "CIRCLE", "SPLINE", "ELLIPSE")


def kind_of(layer: str) -> str | None:
    """The kind of boundary of a layer, or None."""
    norm = reader._normalise(layer)
    for kind, names in LAYERS.items():
        if any(norm == reader._normalise(n) for n in names):
            return kind
    core = reader.guess_kind(layer)
    if core == reader.DxfEntityKind.EXTERNAL:
        return md.EXTERNAL
    if core == reader.DxfEntityKind.MATERIAL:
        return md.MATERIAL
    return None


def boundaries_from_dxf(path, unit: str = "m") -> tuple[tuple[md.Boundary, ...], Report]:
    """The boundaries of a DXF, and what was done."""
    cat = reader.read_dxf(Path(path), unit=unit)
    report = Report()
    out = []
    count = {}
    for layer in cat.layers:
        kind = kind_of(layer.name)
        curved = sum(layer.entity_counts.get(t, 0) for t in CURVED)
        if kind is None:
            report.not_brought.append(f"layer {layer.name!r} ({layer.entity_count} entities): "
                                      "not one of the four kinds of boundary")
            continue
        for k, poly in enumerate(layer.polylines):
            count[kind] = count.get(kind, 0) + 1
            pts = [(float(x), float(y)) for x, y in poly.points]
            closed = poly.closed
            if len(pts) > 2 and pts[0] == pts[-1]:
                pts.pop()
                closed = True
            out.append(md.Boundary(f"{kind} {count[kind]}", kind, tuple(pts), closed,
                                   name=f"{layer.name} {k + 1}"))
        if curved:
            report.changed.append(f"layer {layer.name!r}: {curved} curved entities came as "
                                  "straight pieces (the core's reader flattens the arcs; the "
                                  "mid-side nodes will be on the chords, D13)")
    report.brought.append(f"{len(out)} boundaries: " + ", ".join(
        f"{n} {kind}" for kind, n in sorted(count.items())))
    report.defaults.append("the curved pieces of the polylines (bulges) come flattened too")
    report.defaults.append("materials, assignments, stages, conditions and loads: none, the "
                           "user's to give")
    return tuple(out), report
