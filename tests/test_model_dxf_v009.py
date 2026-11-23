# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.9 (spec 004, T13) — opening a DXF: its polylines, by layer, as the
boundaries of a model (RF-14, D13).

The drawing is written in the test with ``ezdxf`` (the library the core's
reader uses): no file from elsewhere is read.

Invariants protected:

* **the layers go to the four kinds** by name, the core's names for the
  external and the material boundaries and this program's for the
  excavation and the stage ones; a layer that is none of them does not come,
  and the report names it;
* **the arcs come flattened**, as the core's reader gives them, and the
  report says how many curved entities there were (D13: a reader that keeps
  them is asked of the core);
* **the boundaries come as drawn**: a closed polyline is closed, an open one
  open; with vertices shared where they meet the model they make is valid,
  and its regions fill the external boundary.
"""
from __future__ import annotations

import math
import tempfile
from pathlib import Path

import ezdxf

from ogr_fem2d.model import import_dxf, regions
from ogr_fem2d.model import model as md


def _drawing(path):
    doc = ezdxf.new()
    msp = doc.modelspace()
    for name in ("OGR_EXTERNAL", "MATERIAL", "EXCAVACION", "FASE", "COTAS"):
        doc.layers.add(name)
    msp.add_lwpolyline([(-10, -10), (10, -10), (10, -2), (10, 10), (-10, 10), (-10, -2)], close=True,
                       dxfattribs={"layer": "OGR_EXTERNAL"})
    msp.add_line((-10, -2), (10, -2), dxfattribs={"layer": "MATERIAL"})
    msp.add_circle((0, 4), 1.0, dxfattribs={"layer": "EXCAVACION"})
    msp.add_line((-1, 4), (1, 4), dxfattribs={"layer": "FASE"})
    msp.add_line((0, 0), (5, 5), dxfattribs={"layer": "COTAS"})
    doc.saveas(path)


def _open():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "modelo.dxf"
        _drawing(path)
        return import_dxf.boundaries_from_dxf(path)


BOUNDARIES, REPORT = _open()


class TestTheLayers:
    def test_the_four_kinds(self):
        kinds = sorted(b.kind for b in BOUNDARIES)
        assert kinds == sorted([md.EXTERNAL, md.MATERIAL, md.EXCAVATION, md.STAGE])
        for name, kind in (("OGR_EXTERNAL", md.EXTERNAL), ("material", md.MATERIAL),
                           ("Excavación", md.EXCAVATION), ("TUNEL", md.EXCAVATION),
                           ("fase", md.STAGE), ("COTAS", None)):
            assert import_dxf.kind_of(name) == kind, name

    def test_a_layer_of_none_does_not_come_and_is_named(self):
        assert any("'COTAS'" in x for x in REPORT.not_brought)


class TestTheArcs:
    def test_flattened_and_said(self):
        (circle,) = [b for b in BOUNDARIES if b.kind == md.EXCAVATION]
        assert circle.closed and not circle.segments and len(circle.vertices) > 8
        assert all(abs(math.hypot(x, y - 4.0) - 1.0) < 1e-12 for x, y in circle.vertices)
        assert any("'EXCAVACION'" in x and "1 curved" in x for x in REPORT.changed)


class TestAsDrawn:
    def test_closed_and_open(self):
        by = {b.kind: b for b in BOUNDARIES}
        assert by[md.EXTERNAL].closed and len(by[md.EXTERNAL].vertices) == 6
        assert not by[md.MATERIAL].closed and by[md.MATERIAL].vertices == ((-10.0, -2.0), (10.0, -2.0))

    def test_they_make_a_valid_model(self):
        external, material = (next(b for b in BOUNDARIES if b.kind == k) for k in (md.EXTERNAL, md.MATERIAL))
        m = md.Model(boundaries=(external, material), materials=(md.Material("m"),),
                     assignments=(md.Assignment((0.0, -6.0), "m", (False,)),
                                  md.Assignment((0.0, 4.0), "m", (False,))))
        geo = regions.build(m)
        assert abs(sum(regions.region_area(geo, r) for r in range(2)) - 400.0) < 1e-9
