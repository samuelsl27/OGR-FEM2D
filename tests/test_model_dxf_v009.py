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
* **the arcs come as arcs** (OGR-Core 0.2.7, ``keep_arcs``; D13): a CIRCLE
  in four pieces of 90 degrees, each with its centre, its vertices on the
  circle; a bulge of a polyline and an ARC too. Meshed, the mid-side nodes
  of the sides on a circle lie on it. A SPLINE still comes flattened, and an
  ELLIPSE is not read: the report says so;
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
    # a material boundary with a bulge: a half circle of radius 1 from (4, -6) to (6, -6)
    msp.add_lwpolyline([(3, -6, 0.0), (4, -6, -1.0), (6, -6, 0.0), (7, -6, 0.0)], format="xyb",
                       dxfattribs={"layer": "MATERIAL"})
    msp.add_spline([(-8, 6), (-7, 7), (-6, 6), (-5, 7)], dxfattribs={"layer": "MATERIAL"})
    msp.add_ellipse((-6, -6), major_axis=(1, 0), ratio=0.5, dxfattribs={"layer": "MATERIAL"})
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
        # three material boundaries: the line, the polyline with a bulge, the spline
        assert kinds == sorted([md.EXTERNAL, md.MATERIAL, md.MATERIAL, md.MATERIAL, md.EXCAVATION,
                                md.STAGE])
        for name, kind in (("OGR_EXTERNAL", md.EXTERNAL), ("material", md.MATERIAL),
                           ("Excavación", md.EXCAVATION), ("TUNEL", md.EXCAVATION),
                           ("fase", md.STAGE), ("COTAS", None)):
            assert import_dxf.kind_of(name) == kind, name

    def test_a_layer_of_none_does_not_come_and_is_named(self):
        assert any("'COTAS'" in x for x in REPORT.not_brought)


class TestTheArcs:
    def test_a_circle_in_four_quarters_with_their_centre(self):
        (circle,) = [b for b in BOUNDARIES if b.kind == md.EXCAVATION]
        assert circle.closed and len(circle.vertices) == 4
        assert [(s.index, s.arc) for s in circle.segments] == [(k, (0.0, 4.0)) for k in range(4)]
        assert all(abs(math.hypot(x, y - 4.0) - 1.0) < 1e-12 for x, y in circle.vertices)

    def test_a_bulge_is_an_arc(self):
        bulged = [b for b in BOUNDARIES if b.kind == md.MATERIAL and (3.0, -6.0) in b.vertices]
        (b,) = bulged
        arcs = [s for s in b.segments if s.arc is not None]
        assert len(arcs) == 2 and all(s.arc == (5.0, -6.0) for s in arcs)
        for s in arcs:
            p, q = b.segment(s.index)
            assert abs(math.dist(p, s.arc) - 1.0) < 1e-12 and abs(math.dist(q, s.arc) - 1.0) < 1e-12

    def test_the_spline_and_the_ellipse_are_said(self):
        assert any("SPLINE" in x and "'MATERIAL'" in x for x in REPORT.changed)
        assert any("ELLIPSE" in x for x in REPORT.not_brought)

    def test_meshed_the_mid_side_nodes_are_on_the_circle(self):
        from ogr_fem2d.mesh import geometry as g
        from ogr_fem2d.model import translate
        external = next(b for b in BOUNDARIES if b.kind == md.EXTERNAL)
        circle = next(b for b in BOUNDARIES if b.kind == md.EXCAVATION)
        m = md.Model(boundaries=(external, circle), materials=(md.Material("m"),),
                     assignments=(md.Assignment((5.0, 5.0), "m", (False,)),
                                  md.Assignment((0.0, 4.0), "m", (True,))),
                     mesh_settings=g.MeshSettings(boundary_nodes=40))
        mesh = translate.mesh(m).mesh
        on = [n for n, (x, y) in enumerate(mesh.nodes) if abs(math.hypot(x, y - 4.0) - 1.0) < 1e-9]
        assert len(on) >= 2 * 40                       # the corners and the mid-side nodes


class TestAsDrawn:
    def test_closed_and_open(self):
        external = next(b for b in BOUNDARIES if b.kind == md.EXTERNAL)
        assert external.closed and len(external.vertices) == 6 and not external.segments
        line = next(b for b in BOUNDARIES if b.kind == md.MATERIAL and (-10.0, -2.0) in b.vertices)
        assert not line.closed and line.vertices == ((-10.0, -2.0), (10.0, -2.0))

    def test_they_make_a_valid_model(self):
        external = next(b for b in BOUNDARIES if b.kind == md.EXTERNAL)
        material = next(b for b in BOUNDARIES if b.kind == md.MATERIAL and (-10.0, -2.0) in b.vertices)
        m = md.Model(boundaries=(external, material), materials=(md.Material("m"),),
                     assignments=(md.Assignment((0.0, -6.0), "m", (False,)),
                                  md.Assignment((0.0, 4.0), "m", (False,))))
        geo = regions.build(m)
        assert abs(sum(regions.region_area(geo, r) for r in range(2)) - 400.0) < 1e-9
