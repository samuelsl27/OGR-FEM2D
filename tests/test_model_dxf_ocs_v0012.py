# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.12 (OGR-Core 0.2.8) — a DXF whose entities have their own coordinates
(OCS), and every entity the reader leaves out, in the report.

The core's 0.2.8 reads ARC, CIRCLE, LWPOLYLINE and 2-D POLYLINE in their own
coordinates: with extrusion (0, 0, -1) the OCS x is the drawing's -x, and
one leaning out of the XY plane is not read but counted in ``skipped``.
Until this version the report of the import named only an ELLIPSE: a circle
out of the plane on the excavation layer went without a word, and the hole
was missing from the model.

Invariants protected:

* **a mirrored circle comes where it is drawn**: its centre given as (3, 0)
  in its OCS with extrusion -Z is at (-3, 0) in the drawing, as an arc
  boundary about it;
* **every entity left out is in the report, with why**: out of the plane, a
  type the reader does not read; and nothing else is said to be missing.
"""
from __future__ import annotations

import math
import tempfile
from pathlib import Path

import ezdxf

from ogr_fem2d.model import import_dxf


def _open():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "ocs.dxf"
        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_lwpolyline([(-10, -10), (10, -10), (10, 10), (-10, 10)], close=True,
                           dxfattribs={"layer": "External"})
        msp.add_circle((0, 0), 1.0, dxfattribs={"layer": "Excavation",
                                                 "extrusion": (0.0, 0.6, 0.8)})
        msp.add_circle((3, 0), 1.0, dxfattribs={"layer": "Excavation", "extrusion": (0, 0, -1)})
        msp.add_text("cota", dxfattribs={"layer": "External"})
        doc.saveas(path)
        return import_dxf.boundaries_from_dxf(path)


BOUNDARIES, REPORT = _open()


class TestOcs:
    def test_a_mirrored_circle_comes_where_it_is_drawn(self):
        holes = [b for b in BOUNDARIES if b.kind == "excavation"]
        assert len(holes) == 1
        (hole,) = holes
        assert {s.arc for s in hole.segments} == {(-3.0, 0.0)}
        assert all(abs(math.dist(v, (-3.0, 0.0)) - 1.0) <= 1e-12 for v in hole.vertices)


class TestTheReport:
    def test_every_entity_left_out_with_why(self):
        out = REPORT.not_brought
        assert len(out) == 2, out
        assert any(x.startswith("1 CIRCLE (not in the XY plane): not in the plane of the drawing")
                   for x in out), out
        assert any(x.startswith("1 TEXT: the core's reader does not read this type") for x in out), out

    def test_the_reasons(self):
        assert "unreadable" not in import_dxf.skipped_reason("ARC (unreadable)")
        assert import_dxf.skipped_reason("ARC (unreadable)").startswith("could not be read")
        assert import_dxf.skipped_reason("degenerate") == "fewer than two distinct points"
        assert import_dxf.skipped_reason("HATCH").startswith("the core's reader does not read")
