# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.14 (spec 006, T21) — the canvas: the model drawn and moving about it
(RF-15; D15; guide §3, §4, §6).

Invariants protected:

* **y up**: a point above another in the model is above it on screen;
* **each kind of boundary has its pen** (colour, and a dashed line for a
  stage boundary), the suite's; every boundary drawn once; an arc drawn on
  its circle (its chords' points on it);
* **the regions are filled with their material's colour**; an excavated
  region of the stage shown, and a region still without its material, left
  empty; changing the stage shown changes what is excavated (RF-15); a
  model being drawn (no external yet) has its boundaries drawn and no
  regions;
* **the mesh is one item** with every edge once (case 005: 84 432 edges);
* **moving about**: zooming keeps the point under the cursor where it is;
  zoom all fits the model; the grid follows the zoom, at 1-2-5 steps;
* **the window draws the session's model**: an edit by an operation is
  drawn, a tab per stage, and the tab chosen is the stage shown;
  the cursor's coordinates reach the status bar;
* **D15, measured with case 005** (28 066 T6), written before measuring:
  the first drawing in 1 s at most, zooming or panning in 0.1 s at most on
  the development machine (five times that on a CI runner, which is
  slower and shared).
"""
from __future__ import annotations

import math
import os
import time
from dataclasses import replace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import _cases_model  # noqa: E402
import _models  # noqa: E402
from ogr_fem2d.gui.canvas import paths  # noqa: E402
from ogr_fem2d.gui.canvas.view import KIND_PENS, ModelView  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402
from ogr_fem2d.model import edit, ogr_file  # noqa: E402
from ogr_fem2d.model import model as md  # noqa: E402

APP = QApplication.instance() or QApplication([])
SLOWER = 5.0 if os.environ.get("CI") else 1.0
_KEEP = []


def _view(m=None, size=(800, 600)):
    v = ModelView()
    v.resize(*size)
    v.show()
    _KEEP.append(v)
    if m is not None:
        v.set_model(m)
    return v


def _render(v):
    img = QImage(v.viewport().size(), QImage.Format.Format_ARGB32)
    p = QPainter(img)
    v.render(p)
    p.end()
    return img


def _two_stage_tunnel():
    m = _models.with_stages(_models.tunnel(), 2)
    return replace(m, assignments=(m.assignments[0], replace(m.assignments[1],
                                                            excavated=(False, True))))


class TestDrawing:
    def test_y_up(self):
        v = _view(_models.tunnel())
        assert v.mapFromScene(QPointF(0, 5)).y() < v.mapFromScene(QPointF(0, 0)).y()
        assert v.mapFromScene(QPointF(5, 0)).x() > v.mapFromScene(QPointF(0, 0)).x()

    def test_each_kind_its_pen(self):
        m = edit.add_boundary(_models.tunnel(), md.STAGE, ((-10.0, 5.0), (10.0, 5.0)))
        m = edit.add_boundary(m, md.MATERIAL, ((-10.0, -5.0), (10.0, -5.0)))
        v = _view(m)
        assert set(v.boundary_items) == {b.id for b in m.boundaries}
        # the suite's (the colours of OGR Slip2D for the kinds it has)
        expected = {md.EXTERNAL: ("#2c2c2c", False), md.MATERIAL: ("#8b4513", False),
                    md.EXCAVATION: ("#b03a2e", False), md.STAGE: ("#2e6fb0", True)}
        for b in m.boundaries:
            pen = v.boundary_items[b.id].pen()
            colour, dashed = expected[b.kind]
            assert KIND_PENS[b.kind][0] == colour
            assert pen.color() == QColor(colour) and pen.isCosmetic()
            assert (pen.style() == Qt.PenStyle.DashLine) == dashed, b.kind
        # the arc of the hole on its circle
        hole = paths.boundary_line(m.boundary("hole"))
        assert len(hole) >= 4 * paths.CHORDS_PER_QUARTER + 1
        assert all(abs(math.hypot(*p) - 1.0) <= 1e-12 for p in hole)

    def test_regions_and_the_stage_shown(self):
        v = _view(_two_stage_tunnel())
        rock = md.Material("rock").color
        fills = lambda: sorted((i.data(0)[2], i.data(0)[3], i.brush().style() != Qt.BrushStyle.NoBrush)
                               for i in v.region_items)
        assert fills() == [("rock", False, True), ("rock", False, True)]
        assert QColor(v.region_items[0].brush().color().name()) == QColor(rock)
        v.set_stage(1)
        assert fills() == [("rock", False, True), ("rock", True, False)]

    def test_being_drawn_and_without_material(self):
        drawing = edit.add_boundary(md.Model(), md.EXCAVATION, ((0, 0), (1, 0), (1, 1)))
        v = _view(drawing)
        assert v.region_items == [] and list(v.boundary_items) == ["exc1"]
        lay = _models.layers()
        v = _view(replace(lay, assignments=lay.assignments[:1]))
        styles = sorted(i.brush().style() != Qt.BrushStyle.NoBrush for i in v.region_items)
        assert styles == [False, True]

    def test_the_mesh_one_item(self):
        v = _view(_models.meshed(_models.tunnel()))
        m = v.model
        edges = {tuple(sorted(e)) for el in m.mesh.elements
                 for e in ((el[0], el[3]), (el[3], el[1]), (el[1], el[4]), (el[4], el[2]),
                           (el[2], el[5]), (el[5], el[0]))}
        assert v.mesh_item is not None and v.mesh_item.edges == len(edges)
        assert v.mesh_item._path.elementCount() == 2 * len(edges)     # each edge drawn once
        v.show_mesh = False
        v.set_model(m)
        assert v.mesh_item is None


class TestMovingAbout:
    def test_zoom_keeps_the_point_and_zoom_all_fits(self):
        v = _view(_models.tunnel())
        v.zoom_all()
        for x, y in ((-10, -10), (10, 10)):
            p = v.mapFromScene(QPointF(x, y))
            assert v.viewport().rect().contains(p), (x, y, p)
        about = QPointF(3.0, -2.0)
        before = v.mapFromScene(about)
        v.zoom_by(1.7, about)
        after = v.mapFromScene(about)
        assert abs(after.x() - before.x()) <= 1 and abs(after.y() - before.y()) <= 1
        s0 = v.pixels_per_unit()
        v.zoom_by(2.0)
        assert abs(v.pixels_per_unit() / s0 - 2.0) <= 1e-9

    def test_the_grid_follows_the_zoom(self):
        v = _view(_models.tunnel())
        step = v.grid_step()
        mantissa = step / 10 ** math.floor(math.log10(step))
        assert round(mantissa, 9) in (1.0, 2.0, 5.0)
        v.zoom_by(10.0)
        assert v.grid_step() < step


class TestTheWindow:
    def test_draws_the_session_model(self):
        w = MainWindow()
        _KEEP.append(w)
        try:
            w.act_new()
            got = []
            w.view.cursor_moved.connect(lambda x, y: got.append((x, y)))
            w.session.call("boundary_add", type="external",
                           points_xy=[[0, 0], [10, 0], [10, 5], [0, 5]])
            assert list(w.view.boundary_items) == ["ext1"]
            w.session.call("stage_add", name="Dos")
            assert w.stage_tabs.count() == 2
            w.stage_tabs.setCurrentIndex(1)
            assert w.view.stage == 1 and w.stage == 1
            from PySide6.QtCore import QEvent, QPoint
            from PySide6.QtGui import QMouseEvent
            pos = QPointF(w.view.mapFromScene(QPointF(2.0, 3.0)))
            w.view.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, pos, pos,
                                              Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                                              Qt.KeyboardModifier.NoModifier))
            x, y = got[-1]
            assert abs(x - 2.0) < 0.1 and abs(y - 3.0) < 0.1
            w.act_undo()
            assert w.stage_tabs.count() == 1 and w.stage == 0
        finally:
            w.confirm_discard = lambda: True
            w.close()


class TestD15:
    def test_case_005(self):
        m = ogr_file.read(_cases_model.path("005-kirsch-malla-general"))
        v = _view(size=(1600, 1000))
        t = time.perf_counter()
        v.set_model(m)
        _render(v)
        first = time.perf_counter() - t
        assert v.mesh_item.edges == 84432
        moves = []
        for move in (lambda: v.zoom_by(1.15), lambda: v.translate_pixels(30, 0),
                     lambda: v.zoom_by(1 / 1.15)):
            t = time.perf_counter()
            move()
            _render(v)
            moves.append(time.perf_counter() - t)
        assert first <= 1.0 * SLOWER, first
        assert max(moves) <= 0.1 * SLOWER, moves
