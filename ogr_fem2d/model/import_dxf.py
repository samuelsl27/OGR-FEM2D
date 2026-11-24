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

The core's reader keeps the arcs (``read_dxf(..., keep_arcs=True)``, OGR-Core
0.2.7, asked by D13): every ARC, CIRCLE and bulge of a polyline comes in
pieces of at most 90 degrees, each the minor arc of its centre
(``DxfPolyline.arcs``), which is the arc of a segment here (``SegmentAttr``,
spec 003, D3). A SPLINE still comes flattened into straight pieces.

Since OGR-Core 0.2.8 the reader takes ARC, CIRCLE, LWPOLYLINE and 2-D
POLYLINE from their own coordinates (OCS) to the drawing's: one mirrored
(extrusion -Z) comes where it is drawn, and one leaning out of the XY plane
is not read. **Every entity the reader leaves out is in the report** (spec
006; until then only an ELLIPSE was, and a circle out of the plane on the
excavation layer went without a word): each key of its ``skipped``, with
what it means (``SKIPPED``) - out of the plane, unreadable, degenerate, or
of a type it does not read. The reader counts them for the whole drawing,
not by layer.

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

#: what the reader still flattens
FLATTENED = ("SPLINE",)

#: what each kind of key of the reader's ``skipped`` means (OGR-Core 0.2.8);
#: any other key is an entity type it does not read
SKIPPED = {
    " (not in the XY plane)": "not in the plane of the drawing (its extrusion leans away from Z)",
    " (unreadable)": "could not be read (a malformed entity)",
    "degenerate": "fewer than two distinct points",
}


def skipped_reason(key: str) -> str:
    """What a key of the reader's ``skipped`` means."""
    for tail, reason in SKIPPED.items():
        if key == tail or key.endswith(tail):
            return reason
    return "the core's reader does not read this type"


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
    cat = reader.read_dxf(Path(path), unit=unit, keep_arcs=True)
    report = Report()
    out = []
    count = {}
    arcs = 0
    for layer in cat.layers:
        kind = kind_of(layer.name)
        flattened = sum(layer.entity_counts.get(t, 0) for t in FLATTENED)
        if kind is None:
            report.not_brought.append(f"layer {layer.name!r} ({layer.entity_count} entities): "
                                      "not one of the four kinds of boundary")
            continue
        for k, poly in enumerate(layer.polylines):
            count[kind] = count.get(kind, 0) + 1
            pts = [(float(x), float(y)) for x, y in poly.points]
            closed = poly.closed
            if len(pts) > 2 and pts[0] == pts[-1]:
                pts.pop()                  # the closing piece keeps its index, len(pts) - 1
                closed = True
            segments = tuple(md.SegmentAttr(i, arc=(float(c[0]), float(c[1])))
                             for i, c in sorted(poly.arcs.items()))
            arcs += len(segments)
            out.append(md.Boundary(f"{kind} {count[kind]}", kind, tuple(pts), closed, segments,
                                   name=f"{layer.name} {k + 1}"))
        if flattened:
            report.changed.append(f"layer {layer.name!r}: {flattened} SPLINE came as straight "
                                  "pieces (the core's reader flattens them; the mid-side nodes "
                                  "will be on the chords)")
    for key, n in sorted(cat.skipped.items()):
        report.not_brought.append(f"{n} {key}: {skipped_reason(key)}; not read")
    report.brought.append(f"{len(out)} boundaries: " + ", ".join(
        f"{n} {kind}" for kind, n in sorted(count.items())) + f"; {arcs} pieces of arc")
    report.defaults.append("materials, assignments, stages, conditions and loads: none, the "
                           "user's to give")
    return tuple(out), report
