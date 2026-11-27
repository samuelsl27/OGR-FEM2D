# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A field on the canvas, in ONE item (spec 006, T31; D11, D15): the bands of
``drawn.draw`` filled with their colours and its iso-lines, as paths in
model coordinates, so a zoom or a pan only paints them again (with the
mesh of case 005, 20 502 vertices) and never contours again.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsItem

from ogr_ui.themes import current_theme

from .drawn import Drawn

#: the iso-lines (light, dark)
LINE_PEN = ("#202020", "#f0f0f0")


def _polygon(points) -> QPolygonF:
    return QPolygonF([QPointF(float(x), float(y)) for x, y in points])


class FieldItem(QGraphicsItem):
    """The bands and lines of a field."""

    def __init__(self, drawn: Drawn, opacity: float = 1.0):
        super().__init__()
        self.drawn = drawn
        self.fills: list[tuple[QColor, QPainterPath]] = []
        rect = QRectF()
        for colour, rings in drawn.bands:
            path = QPainterPath()
            path.setFillRule(Qt.FillRule.WindingFill)
            for ring in rings:
                path.addPolygon(_polygon(ring))
                path.closeSubpath()
            self.fills.append((QColor(colour), path))
            rect = rect.united(path.boundingRect())
        self.lines = QPainterPath()
        for line in drawn.lines:
            self.lines.addPolygon(_polygon(line))
        rect = rect.united(self.lines.boundingRect())
        self._rect = rect
        light, dark = LINE_PEN
        self._line_pen = QPen(QColor(dark if current_theme() == "dark" else light), 0.0)
        self._line_pen.setCosmetic(True)
        self.setOpacity(opacity)
        self.setZValue(0.5)

    def boundingRect(self) -> QRectF:  # noqa: N802 - Qt's name
        return self._rect

    def colour_at(self, x: float, y: float):
        """The colour painted at (x, y), or None (for a test: what is drawn
        is the legend's colour)."""
        p = QPointF(x, y)
        found = None
        for colour, path in self.fills:
            if path.contains(p):
                found = colour.name()
        return found

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(Qt.PenStyle.NoPen)
        for colour, path in self.fills:
            painter.setBrush(QBrush(colour))
            painter.drawPath(path)
        if not self.lines.isEmpty():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(self._line_pen)
            painter.drawPath(self.lines)
