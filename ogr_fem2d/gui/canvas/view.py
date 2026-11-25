# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The canvas: the model drawn, and moving about it (spec 006, T21; RF-15;
guide §3, §4, §6).

* **y up**, as the model: the view is scaled (1, -1), so a scene point is
  a model point;
* **what is drawn**: every boundary with the colour and line of its kind
  (``KIND_PENS``, the same in the canvas, the legend and the help), the
  regions filled with their material's colour, an excavated region of the
  stage shown left empty and dashed, a region still without its material
  left empty, and the mesh as ONE item that draws every edge at once (case
  005 has 28 066 T6: an item each would not be fluid, D15);
* **moving about**: the wheel zooms about the cursor, the middle button
  pans, ``zoom_all`` fits the model; the grid follows the zoom
  (``ogr_core.numbers.nice_step``, as Slip2D's) and is drawn with the theme's
  colours; the cursor's model coordinates go to the status bar;
* the pens are cosmetic: a line is as thick on screen at any zoom.

The view draws the session's model again when the session says it changed
(``refresh``); the stage shown is the one edited (RF-15), chosen in the tabs
under it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QGraphicsItem, QGraphicsLineItem, QGraphicsPathItem,
                               QGraphicsScene, QGraphicsView)

from ogr_core.numbers import nice_step
from ogr_ui.themes import current_theme, theme_color

from ...model import model as md
from . import paths

#: kind -> (colour in the light theme, in the dark one, dashed)
KIND_PENS = {
    md.EXTERNAL: ("#2c2c2c", "#e0e0e0", False),
    md.MATERIAL: ("#8b4513", "#d2915a", False),
    md.EXCAVATION: ("#b03a2e", "#ff7b6e", False),
    md.STAGE: ("#2e6fb0", "#7fb2ea", True),
}
MESH_PEN = ("#8a9399", "#6b7378")
#: a mesh of another geometry (spec 004, RF-11): kept, and drawn so that it is not taken
#: for the model's (P10: the reference program deleted it)
MESH_STALE_PEN = ("#c08a2b", "#d9a54a")
#: the nodes the boundaries will have (Mesh > Discretize)
DISCRETIZATION_PEN = ("#1f78b4", "#7fb8e6")
#: the field stress's block, surface and strata (light, dark)
FIELD_PEN = ("#6a3d9a", "#c3a5e6")
REGION_ALPHA = 0.55
ZOOM_STEP = 1.15
#: what the canvas shows of a model with nothing drawn yet, in metres
EMPTY_EXTENT = (-10.0, -10.0, 60.0, 40.0)


def kind_pen(kind: str, width: float = 2.0) -> QPen:
    light, dark, dashed = KIND_PENS[kind]
    pen = QPen(QColor(dark if current_theme() == "dark" else light), width)
    pen.setCosmetic(True)
    if dashed:
        pen.setStyle(Qt.PenStyle.DashLine)
    return pen


def _path(points, closed: bool) -> QPainterPath:
    path = QPainterPath()
    if not points:
        return path
    path.moveTo(QPointF(*points[0]))
    for p in points[1:]:
        path.lineTo(QPointF(*p))
    if closed:
        path.closeSubpath()
    return path


class MeshItem(QGraphicsItem):
    """Every edge of the mesh in one path, drawn at once."""

    def __init__(self, mesh: md.StoredMesh, stale: bool = False):
        super().__init__()
        self.stale = stale
        nodes = mesh.nodes
        corners = 3
        seen = set()
        self._path = QPainterPath()
        for e in mesh.elements:
            n = len(e)
            ring = [e[0], e[3], e[1], e[4], e[2], e[5]] if n == 6 else list(e[:corners])
            for k in range(len(ring)):
                a, b = ring[k], ring[(k + 1) % len(ring)]
                key = (a, b) if a < b else (b, a)
                if key in seen:
                    continue
                seen.add(key)
                self._path.moveTo(QPointF(*nodes[a]))
                self._path.lineTo(QPointF(*nodes[b]))
        self.edges = len(seen)
        self._rect = self._path.boundingRect()
        light, dark = MESH_STALE_PEN if stale else MESH_PEN
        self._pen = QPen(QColor(dark if current_theme() == "dark" else light), 0.0)
        self._pen.setCosmetic(True)
        if stale:
            self._pen.setStyle(Qt.PenStyle.DashLine)
        self.setZValue(1)
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

    def boundingRect(self) -> QRectF:  # noqa: N802 - Qt's name
        return self._rect

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setPen(self._pen)
        painter.drawPath(self._path)


class ModelView(QGraphicsView):
    """The canvas of a model (see the module's notes)."""

    #: the cursor's model coordinates
    cursor_moved = Signal(float, float)
    #: a left or right click, at its model coordinates
    clicked = Signal(float, float, object)
    #: a key pressed on the canvas (the tools take Esc, Enter, Backspace)
    key_pressed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.scale(1.0, -1.0)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setMouseTracking(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.show_grid = True
        self.show_mesh = True
        self.stage = 0
        self.model: md.Model | None = None
        self.boundary_items: dict[str, QGraphicsPathItem] = {}
        self.region_items: list[QGraphicsPathItem] = []
        self.mesh_item: MeshItem | None = None
        self.axis_item: QGraphicsLineItem | None = None
        self.field_item: QGraphicsPathItem | None = None
        self.discretization_item: QGraphicsPathItem | None = None
        #: whether the model's mesh is of another geometry (the window says)
        self.mesh_stale = False
        #: the units shown in one metre (``gui.units``): the grid is round in them
        self.length_factor = 1.0
        self._pan_from = None
        self.setBackgroundBrush(QBrush(QColor(theme_color("canvas_bg"))))

    # ------------------------------------------------------------ drawing
    def set_model(self, m: md.Model | None, stage: int | None = None) -> None:
        """Draw ``m`` (its stage ``stage``, or the one shown). A model seen
        for the first time is fitted; one with nothing drawn yet shows
        ``EMPTY_EXTENT``, so that the grid and the snap are of a size an
        engineer draws at (at one pixel per metre the grid was of 50 m, and
        every click went to its nearest node)."""
        first = m is not None and (self.model is None or not self.model.boundaries)
        self.model = m
        if stage is not None:
            self.stage = stage
        if m is not None:
            self.stage = min(self.stage, len(m.stages) - 1)
        self._draw()
        if first:
            if m.boundaries:
                self.zoom_all()
            else:
                self.show_extent(*EMPTY_EXTENT)

    def show_extent(self, x0: float, y0: float, x1: float, y1: float) -> None:
        """Fit the rectangle (x0, y0)-(x1, y1) in the view."""
        self.fitInView(QRectF(x0, y0, x1 - x0, y1 - y0), Qt.AspectRatioMode.KeepAspectRatio)

    def set_stage(self, stage: int) -> None:
        self.stage = stage
        self._draw()

    def _draw(self) -> None:
        scene = self.scene()
        scene.clear()
        self.boundary_items, self.region_items, self.mesh_item = {}, [], None
        self.axis_item = None
        self.field_item = None
        self.discretization_item = None
        m = self.model
        if m is None:
            return
        colours = {mat.id: mat.color for mat in m.materials}
        for r in paths.region_shapes(m, self.stage):
            path = _path(r.outline, True)
            for h in r.holes:
                path.addPath(_path(h, True))
            path.setFillRule(Qt.FillRule.OddEvenFill)
            item = QGraphicsPathItem(path)
            item.setPen(QPen(Qt.PenStyle.NoPen))
            if r.material is not None and not r.excavated:
                c = QColor(colours.get(r.material, "#cccccc"))
                c.setAlphaF(REGION_ALPHA)
                item.setBrush(QBrush(c))
            else:
                item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            item.setData(0, ("region", r.assignment, r.material, r.excavated))
            item.setZValue(0)
            scene.addItem(item)
            self.region_items.append(item)
        if self.show_mesh and m.mesh is not None:
            self.mesh_item = MeshItem(m.mesh, stale=self.mesh_stale)
            scene.addItem(self.mesh_item)
        for b in m.boundaries:
            item = QGraphicsPathItem(_path(paths.boundary_line(b), False))
            item.setPen(kind_pen(b.kind))
            item.setData(0, ("boundary", b.id))
            item.setZValue(2)
            scene.addItem(item)
            self.boundary_items[b.id] = item
        box = paths.bounds(m)
        if box is not None:
            x0, y0, x1, y1 = box
            w, h = max(x1 - x0, 1e-9), max(y1 - y0, 1e-9)
            scene.setSceneRect(QRectF(x0 - 10 * w, y0 - 10 * h, 21 * w, 21 * h))
        if m.analysis == md.AXISYMMETRIC:
            self._draw_axis(box)
        self._draw_field()

    def show_discretization(self, points) -> None:
        """A small cross at each node the boundaries will have (gone at
        the next change of the model)."""
        if self.discretization_item is not None:
            self.scene().removeItem(self.discretization_item)
            self.discretization_item = None
        if not points:
            return
        s = 3.0 / max(self.pixels_per_unit(), 1e-12)          # 3 pixels
        path = QPainterPath()
        for x, y in points:
            path.moveTo(QPointF(x - s, y - s))
            path.lineTo(QPointF(x + s, y + s))
            path.moveTo(QPointF(x - s, y + s))
            path.lineTo(QPointF(x + s, y - s))
        item = QGraphicsPathItem(path)
        pen = QPen(QColor(DISCRETIZATION_PEN[1] if current_theme() == "dark"
                          else DISCRETIZATION_PEN[0]), 1.5)
        pen.setCosmetic(True)
        item.setPen(pen)
        item.setData(0, ("discretization", len(points)))
        item.setZValue(4)
        self.scene().addItem(item)
        self.discretization_item = item

    def _draw_field(self) -> None:
        """The field stress as it is kept (``paths.field_marks``): the block
        of a constant field, the surface and strata of a gravitational one."""
        marks = paths.field_marks(self.model)
        if marks is None:
            return
        path = QPainterPath()
        for line in marks.lines:
            path.addPath(_path(line, False))
        item = QGraphicsPathItem(path)
        pen = QPen(QColor(FIELD_PEN[1] if current_theme() == "dark" else FIELD_PEN[0]), 1.5)
        pen.setCosmetic(True)
        if marks.kind == "gravity":
            pen.setStyle(Qt.PenStyle.DashLine)
        item.setPen(pen)
        item.setData(0, ("field", marks.kind))
        item.setZValue(3)
        self.scene().addItem(item)
        self.field_item = item

    def _draw_axis(self, box) -> None:
        """The axis of revolution, x = 0, dash-dot, longer than the model
        (the case limit of the spec: axisymmetry, the axis drawn)."""
        y0, y1 = EMPTY_EXTENT[1], EMPTY_EXTENT[3]
        if box is not None:
            h = max(box[3] - box[1], 1.0)
            y0, y1 = box[1] - h, box[3] + h
        item = QGraphicsLineItem(0.0, y0, 0.0, y1)
        pen = QPen(QColor(theme_color("status_text")), 1.0)
        pen.setCosmetic(True)
        pen.setStyle(Qt.PenStyle.DashDotLine)
        item.setPen(pen)
        item.setData(0, ("axis",))
        item.setZValue(1)
        self.scene().addItem(item)
        self.axis_item = item

    # ------------------------------------------------------------ moving about
    def pixels_per_unit(self) -> float:
        return abs(self.transform().m11())

    def zoom_all(self, margin: float = 0.08) -> None:
        """Fit the model's boundaries in the view, and the field's block
        beside them."""
        box = None if self.model is None else paths.bounds(self.model)
        if box is None:
            return
        x0, y0, x1, y1 = box
        marks = paths.field_marks(self.model)
        if marks is not None and marks.kind == "constant":
            xs = [p[0] for line in marks.lines for p in line]
            ys = [p[1] for line in marks.lines for p in line]
            x0, y0, x1, y1 = min(x0, *xs), min(y0, *ys), max(x1, *xs), max(y1, *ys)
        w, h = max(x1 - x0, 1e-9), max(y1 - y0, 1e-9)
        self.fitInView(QRectF(x0 - margin * w, y0 - margin * h, w * (1 + 2 * margin),
                              h * (1 + 2 * margin)), Qt.AspectRatioMode.KeepAspectRatio)

    def zoom_by(self, factor: float, about: QPointF | None = None) -> None:
        """Zoom by ``factor`` keeping the scene point ``about`` (the view's
        centre by default) under the same pixel."""
        if about is None:
            about = self.mapToScene(self.viewport().rect().center())
        before = self.mapFromScene(about)
        self.scale(factor, factor)
        after = self.mapFromScene(about)
        d = after - before
        self.translate_pixels(d.x(), d.y())

    def translate_pixels(self, dx: float, dy: float) -> None:
        s = self.pixels_per_unit()
        if s > 0:
            self.translate(-dx / s, dy / s)

    def model_point(self, pos) -> tuple[float, float]:
        p = self.mapToScene(pos.toPoint() if hasattr(pos, "toPoint") else pos)
        return p.x(), p.y()

    # ------------------------------------------------------------ events
    def wheelEvent(self, event) -> None:  # noqa: N802
        factor = ZOOM_STEP if event.angleDelta().y() > 0 else 1.0 / ZOOM_STEP
        self.zoom_by(factor, self.mapToScene(event.position().toPoint()))
        event.accept()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_from = event.position()
            event.accept()
            return
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            x, y = self.model_point(event.position())
            self.clicked.emit(x, y, event.button())
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        self.key_pressed.emit(event.key())
        super().keyPressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        x, y = self.model_point(event.position())
        self.cursor_moved.emit(x, y)
        if self._pan_from is not None:
            d = event.position() - self._pan_from
            self._pan_from = event.position()
            self.translate_pixels(-d.x(), -d.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_from = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:  # noqa: N802
        super().drawBackground(painter, rect)
        if self.show_grid:
            self.draw_grid(painter, rect)

    def grid_step(self) -> float:
        """The grid's spacing in metres: about 60 pixels, rounded to 1-2-5
        in the units shown (in feet, a round number of feet)."""
        s, f = self.pixels_per_unit(), self.length_factor
        return nice_step(60.0 * f / s) / f if s > 0 else 0.0

    def draw_grid(self, painter: QPainter, rect: QRectF) -> None:
        step = self.grid_step()
        if step <= 0 or rect.width() / step > 2000 or rect.height() / step > 2000:
            return
        import math
        minor = QPen(QColor(theme_color("grid_minor")), 0.0)
        major = QPen(QColor(theme_color("grid_major")), 0.0)
        minor.setCosmetic(True)
        major.setCosmetic(True)
        x = math.floor(rect.left() / step) * step
        while x <= rect.right():
            painter.setPen(major if abs(round(x / (5 * step)) * 5 * step - x) < 1e-9 * step else minor)
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += step
        y = math.floor(rect.top() / step) * step
        while y <= rect.bottom():
            painter.setPen(major if abs(round(y / (5 * step)) * 5 * step - y) < 1e-9 * step else minor)
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += step
