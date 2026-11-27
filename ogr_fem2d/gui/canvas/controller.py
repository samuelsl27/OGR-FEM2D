# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The tools of the canvas (spec 006, T22; D10; guide §3, §4, §8): drawing a
boundary, a circle, and editing vertices, on the window's model through the
operations.

* **a mode at a time**: ``draw`` (a boundary of a kind, by clicks, typed
  points, the table or arcs), ``circle`` (its centre, then its radius or a
  point it goes through), ``move_vertex``, ``insert_vertex``,
  ``delete_vertex``, ``delete_boundary``; Esc leaves it, Backspace undoes
  the last point, Enter or the right button finishes a boundary;
* **every click is snapped** (``ogr_ui.canvas.snap_engine``): to a vertex,
  to a segment (an arc by its chords, which are not vertices), to the grid,
  orthogonally; the toggles are those of the status bar. The tolerances are
  in pixels of the screen, and say so;
* **picking** a vertex or a segment works within ``tools.PICK_PX`` pixels;
  a click that picks nothing says so on the status bar (P13);
* **finishing calls the operation** (``boundary_add`` with its cuts,
  ``boundary_circle``, ``boundary_edit``), one step of the history, and the
  status bar says the cuts it put; a refusal is said there too.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsPathItem

from ogr_ui.canvas.snap_engine import SnapEngine, SnapPoint, SnapSettings, SnapShape
from ogr_ui.i18n import tr
from ogr_ui.themes import theme_color

from ...model import model as md
from .. import units
from . import paths, tools

NONE, DRAW, CIRCLE = "none", "draw", "circle"
#: assigning what the assignment panel chose, by clicks inside regions (T26)
ASSIGN = "assign"
#: putting a condition or a load on what a click picks: a vertex, or a segment (T27)
PLACE = "place"
MOVE, INSERT, DELETE_VERTEX, DELETE_BOUNDARY = ("move_vertex", "insert_vertex", "delete_vertex",
                                                "delete_boundary")


class ToolController:
    """The tools of one window's canvas."""

    def __init__(self, window):
        self.w = window
        self.view = window.view
        self.mode = NONE
        self.drawing: tools.BoundaryDrawing | None = None
        self.circle_kind = md.EXCAVATION
        self.circle_centre = None
        self.picked = None                      # (boundary, index, vertex) to move
        self.cursor = None
        self.snap = SnapEngine(SnapSettings(snap=True, ortho=False, osnap=False))
        self._preview = None
        self.action: dict = {}

    # ------------------------------------------------------------ modes
    def start(self, mode: str, kind: str | None = None) -> None:
        self.cancel(quiet=True)
        self.mode = mode
        if mode == DRAW:
            self.drawing = tools.BoundaryDrawing(kind)
            self.say(tr("Click or type the first vertex [Enter: finish, Esc: cancel, "
                        "Backspace: undo]."))
        elif mode == CIRCLE:
            self.circle_kind = kind or md.EXCAVATION
            self.say(tr("Click or type the centre of the circle."))
        elif mode == MOVE:
            self.say(tr("Click the vertex to move."))
        elif mode == INSERT:
            self.say(tr("Click the segment where the vertex goes."))
        elif mode == DELETE_VERTEX:
            self.say(tr("Click the vertex to delete."))
        elif mode == DELETE_BOUNDARY:
            self.say(tr("Click the boundary to delete."))
        elif mode == PLACE:
            self.say(tr("Click the segments or vertices (within %d pixels) [Esc: stop].")
                     % tools.PICK_PX)
        elif mode == ASSIGN:
            self.say(tr("Click inside the regions [Esc: stop]."))
        self.w.refresh_tools()

    def cancel(self, quiet: bool = False) -> None:
        self.mode, self.drawing, self.circle_centre, self.picked = NONE, None, None, None
        self._show_preview()
        if not quiet:
            self.say(tr("Cancelled."))
            self.w.refresh_tools()

    def say(self, text: str) -> None:
        self.w.statusBar().showMessage(text, 15000)

    @property
    def tol(self) -> float:
        """``PICK_PX`` pixels, in model units at the current zoom."""
        s = self.view.pixels_per_unit()
        return tools.PICK_PX / s if s > 0 else 0.0

    # ------------------------------------------------------------ snapping
    def shapes(self) -> list:
        m = self.w.session.model
        out = []
        if m is not None:
            for b in m.boundaries:
                line = paths.boundary_line(b)
                segs = tuple((SnapPoint(*line[k]), SnapPoint(*line[k + 1]))
                             for k in range(len(line) - 1))
                out.append(SnapShape(tuple(SnapPoint(*v) for v in b.vertices), segs))
        if self.drawing is not None and self.drawing.vertices:
            out.append(SnapShape.polyline([SnapPoint(*v) for v in self.drawing.vertices]))
        return out

    def snapped(self, x: float, y: float) -> tuple[float, float]:
        self.snap.settings.grid_h = self.snap.settings.grid_v = self.view.grid_step() or 1.0
        last = self.drawing.last if self.drawing is not None else self.circle_centre
        self.snap.set_reference(None if last is None else SnapPoint(*last))
        r = self.snap.resolve(SnapPoint(x, y), self.shapes(), self.view.pixels_per_unit())
        return r.point.x, r.point.y

    # ------------------------------------------------------------ input
    def moved(self, x: float, y: float) -> None:
        self.cursor = self.snapped(x, y) if self.mode in (DRAW, CIRCLE) else (x, y)
        self._show_preview()

    def start_place(self, action: dict) -> None:
        """Put ``action`` (a condition or a load, the window's) on what
        the next clicks pick."""
        self.start(PLACE)
        self.action = action

    def place_at(self, p) -> None:
        """A vertex within ``PICK_PX`` pixels, else a segment: said if
        neither (P13)."""
        m = self.w.session.model
        v = tools.pick_vertex(m, p, self.tol)
        if v is not None:
            self.w.place(self.action, vertex=v[2])
            return
        s = tools.pick_segment(m, p, self.tol)
        if s is None:
            self.say(tr("No boundary within %d pixels of the click.") % tools.PICK_PX)
            return
        b = m.boundary(s[0])
        start, end = b.segment(s[1])
        self.w.place(self.action, boundary=b.id, start=start, end=end)

    def start_assign(self) -> None:
        self.start(ASSIGN)

    def clicked(self, x: float, y: float, button) -> None:
        if self.mode == NONE:
            if button == Qt.MouseButton.RightButton:
                self.w.region_context(x, y)          # the region's menu (D7)
            return
        if self.mode == PLACE and button == Qt.MouseButton.LeftButton:
            self.place_at((x, y))
            return
        if self.mode == ASSIGN and button == Qt.MouseButton.LeftButton:
            self.w.assign_at(x, y)
            return
        if button == Qt.MouseButton.RightButton:
            if self.mode == DRAW:
                self.finish()
            else:
                self.cancel()
            return
        if self.mode in (DRAW, CIRCLE):
            self.point(self.snapped(x, y))
        else:
            self._edit_at((x, y))

    def reference(self):
        """The point a typed ``@...`` is measured from: the last vertex of
        the boundary being drawn, or the centre of the circle; None."""
        return self.drawing.last if self.drawing is not None else self.circle_centre

    def _give_reference(self) -> None:
        """The status bar's X, Y field told the reference, in the units
        shown (ogr_ui 0.1.3), each time it may have changed."""
        last, m = self.reference(), self.w.session.model
        self.w.statusBar().set_point_reference(
            None if last is None or m is None else units.to_user(m, last))

    def typed_point(self, x: float, y: float) -> None:
        """A point typed in the status bar's field, read there (absolute,
        relative or polar, from the reference given) in the units shown."""
        if self.mode not in (DRAW, CIRCLE, MOVE):
            self.say(tr("Typed points are for drawing: Boundaries > Add."))
            return
        p = units.from_user(self.w.session.model, (x, y))     # kept in metres (gui.units)
        if self.mode == MOVE:
            self._edit_at(p, typed=True)
        else:
            self.point(p)

    def points(self, pts) -> None:
        """Several points, from the table."""
        for p in pts:
            if self.mode not in (DRAW,):
                break
            self.point(units.from_user(self.w.session.model, p))

    def key(self, key) -> bool:
        """A key of the canvas; True if it was a tool's."""
        if self.mode == NONE:
            return False
        if key == Qt.Key.Key_Escape:
            self.cancel()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.mode == DRAW:
            self.finish()
        elif key == Qt.Key.Key_Backspace and self.drawing is not None:
            self.drawing.undo()
            self._show_preview()
        else:
            return False
        return True

    # ------------------------------------------------------------ drawing
    def point(self, p) -> None:
        if self.mode == CIRCLE:
            if self.circle_centre is None:
                self.circle_centre = p
                self.say(tr("Click or type a point of the circle (or @radius<0)."))
                self._show_preview()
                return
            c, self.circle_centre = self.circle_centre, None
            self.mode = NONE
            self._show_preview()
            got = self.w.do("boundary_circle", type=self.circle_kind, centre=list(c),
                            through=list(p))
            if got is not None:
                self._said_cuts(got)
            self.w.refresh_tools()
            return
        try:
            what = self.drawing.add(p)
        except (tools.EntryError, ValueError) as err:
            self.say(tr(str(err)))
            return
        if what == "closed":
            self.finish()
            return
        self.say({"vertex": tr("Next vertex [a: arc, Enter: finish, Esc: cancel]."),
                  "through": tr("Click or type the end of the arc."),
                  "arc": tr("Next vertex [a: arc, Enter: finish, Esc: cancel].")}[what])
        self._show_preview()

    def start_arc(self) -> None:
        if self.drawing is None:
            return
        try:
            self.drawing.start_arc()
        except tools.EntryError as err:
            self.say(tr(str(err)))
            return
        self.say(tr("Click or type a point the arc goes through."))

    def finish(self) -> None:
        if self.drawing is None:
            return
        try:
            args = self.drawing.result()
        except tools.EntryError as err:
            self.say(tr(str(err)))
            return
        self.cancel(quiet=True)
        got = self.w.do("boundary_add", **args)
        if got is not None:
            self._said_cuts(got)
        self.w.refresh_tools()

    def _said_cuts(self, got: dict) -> None:
        n = len({tuple(c["point"]) for c in got.get("cuts", ())})
        self.say(tr("Boundary added.") if not n else
                 tr("Boundary added; vertices put where it cuts others: %d") % n)

    # ------------------------------------------------------------ editing
    def _edit_at(self, p, typed: bool = False) -> None:
        m = self.w.session.model
        if m is None:
            return
        if self.mode == MOVE and self.picked is not None:
            bid, _i, v = self.picked
            self.picked = None
            self.mode = NONE
            self.w.do("boundary_edit", boundary=bid, op="move_vertex", point_xy=list(v),
                      to_xy=list(p))
            self.w.refresh_tools()
            return
        tol = 0.0 if typed else self.tol
        if self.mode in (MOVE, DELETE_VERTEX):
            hit = tools.pick_vertex(m, p, tol)
            if hit is None:
                self.say(tr("No vertex within %d pixels of the click.") % int(tools.PICK_PX))
                return
            if self.mode == MOVE:
                self.picked = hit
                self.say(tr("Click or type where the vertex goes."))
                return
            self.mode = NONE
            self.w.do("boundary_edit", boundary=hit[0], op="delete_vertex", index=hit[1])
        else:
            hit = tools.pick_segment(m, p, tol)
            if hit is None:
                self.say(tr("No boundary within %d pixels of the click.") % int(tools.PICK_PX))
                return
            mode, self.mode = self.mode, NONE
            if mode == INSERT:
                self.w.do("boundary_edit", boundary=hit[0], op="insert_vertex", segment=hit[1],
                          point_xy=list(hit[2]))
            else:
                self.w.do("boundary_edit", boundary=hit[0], op="delete")
        self.w.refresh_tools()

    # ------------------------------------------------------------ preview
    def _preview_item(self) -> QGraphicsPathItem:
        """The dashed line of what is being drawn; made again when the
        canvas drew the model again (clearing its scene deletes it)."""
        import shiboken6
        if self._preview is None or not shiboken6.isValid(self._preview):
            item = QGraphicsPathItem()
            pen = QPen(QColor(theme_color("accent")), 1.5, Qt.PenStyle.DashLine)
            pen.setCosmetic(True)
            item.setPen(pen)
            item.setZValue(10)
            self.view.scene().addItem(item)
            self._preview = item
        return self._preview

    def _show_preview(self) -> None:
        self._give_reference()
        self._preview_item()
        path = QPainterPath()
        pts = []
        if self.drawing is not None and self.drawing.drawn is not None:
            pts = paths.boundary_line(md.Boundary("", self.drawing.kind, self.drawing.vertices,
                                                  self.drawing.closed, self.drawing.drawn.segments))
        elif self.circle_centre is not None:
            pts = [self.circle_centre]
        if pts:
            path.moveTo(QPointF(*pts[0]))
            for q in pts[1:]:
                path.lineTo(QPointF(*q))
            if self.cursor is not None and not (self.drawing and self.drawing.closed):
                path.lineTo(QPointF(*self.cursor))
        self._preview_item().setPath(path)
