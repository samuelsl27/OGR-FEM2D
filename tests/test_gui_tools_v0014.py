# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.14 (spec 006, T22) — entering geometry: clicks, typed points, the
table, circles and arcs, editing vertices (D10, D12; guide §3, §8; P05,
P13).

Invariants protected:

* **a typed point means one thing** (D12): absolute ``x, y``, ``x y``,
  ``x; y`` with decimal commas, ``x,y`` with points; relative ``@dx, dy``;
  polar ``@d<angle`` (a quarter turn exact); what is ambiguous (``1,5,2,5``),
  or relative with no vertex yet, is refused, saying how to write it;
* **a boundary being drawn**: its vertices in order; a point on the first
  vertex closes it; an arc by three points has its centre, and half a
  circle or more is two segments; undo takes back the last step; what it
  gives is what ``boundary_add`` takes;
* **picking works in pixels of the screen**: a vertex or a segment within
  ``PICK_PX`` pixels is picked, on an arc the point is on the arc; a click
  that picks nothing says so (P13);
* **the window's tools end in an operation**: a boundary drawn by clicks is
  one ``boundary_add`` and one step to undo; a click 2 px from a vertex is
  snapped onto it (the boundaries share it); a line across the external
  puts its cuts and says how many; typed points and Enter, the table, a
  circle, an arc, moving, inserting and deleting a vertex, deleting a
  boundary; Esc cancels and the right button finishes.
"""
from __future__ import annotations

import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from ogr_fem2d.gui.canvas import controller as tc  # noqa: E402
from ogr_fem2d.gui.canvas import tools  # noqa: E402
from ogr_fem2d.gui.dialogs.coordinates import CoordinatesDialog, TableError, read_rows  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402
from ogr_fem2d.model import model as md  # noqa: E402

APP = QApplication.instance() or QApplication([])
LEFT, RIGHT = Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton
_KEEP = []


def _refused(fn, *words):
    try:
        fn()
    except tools.EntryError as err:
        for w in words:
            assert w in str(err), (w, str(err))
        return
    raise AssertionError("accepted")


class TestTypedPoints:
    """The reading of D10 and D12 is ogr_ui's (``read_point``, taken from this
    program's ``parse_point`` in 0.1.3): held here as what this program
    relies on, as the window uses it. Since ogr-gui 0.2.0 (the owner's
    criterion of 2026-11-28): the comma parts x from y, and the point is the
    decimal mark (``x.x,x.x``)."""

    def test_what_each_form_means(self):
        from ogr_ui.point_entry import read_point
        p = lambda s: read_point(s, (10.0, 20.0))
        for text in ("1.5, 2.5", "1.5,2.5", "1.5 , 2.5"):
            assert p(text) == (1.5, 2.5), text
        assert p("3,4") == (3.0, 4.0)
        assert p("@1, -2") == (11.0, 18.0)
        assert p("@1.5, -2") == (11.5, 18.0)
        assert p("@2<90") == (10.0, 22.0) and p("@2<180") == (8.0, 20.0)
        x, y = p("@2<30")
        assert abs(x - (10 + math.sqrt(3))) < 1e-12 and abs(y - 21.0) < 1e-12

    def test_what_is_refused(self):
        from ogr_ui.point_entry import PointEntryError, read_point
        for text, ref in (("1,5,2,5", (0.0, 0.0)), ("1 2 3", (0.0, 0.0)), ("x, y", (0.0, 0.0)),
                          ("@2<a", (0.0, 0.0)), ("@1, 1", None),
                          # a decimal comma, a space or a semicolon between the two (0.2.0)
                          ("1,5; 2,5", (0.0, 0.0)), ("1,5 2,5", (0.0, 0.0)),
                          ("1.5 2.5", (0.0, 0.0)), ("1.5;2.5", (0.0, 0.0)),
                          ("@1,5<30", (0.0, 0.0))):
            try:
                read_point(text, ref)
            except PointEntryError:
                continue
            raise AssertionError(f"{text!r} accepted")

    def test_the_reference_follows_the_drawing(self):
        """The field is told the last vertex, or the circle's centre, in the
        units shown; None when nothing is being drawn."""
        w = _window()
        try:
            bar = w.statusBar()
            w.tools.start(tc.DRAW, md.EXTERNAL)
            assert bar.coord_input.reference() is None
            w.tools.clicked(2.0, 3.0, LEFT)
            assert bar.coord_input.reference() == w.tools.drawing.last
            w.tools.cancel()
            assert bar.coord_input.reference() is None
            w.tools.start(tc.CIRCLE, md.EXCAVATION)
            w.tools.clicked(10.0, 10.0, LEFT)
            assert bar.coord_input.reference() == w.tools.circle_centre
        finally:
            _close(w)


class TestDrawing:
    def test_lines_and_closing_on_the_first(self):
        d = tools.BoundaryDrawing(md.EXTERNAL)
        for p in ((0, 0), (4, 0), (4, 3)):
            assert d.add(p) == "vertex"
        assert d.add((0, 0)) == "closed" and d.closed
        r = d.result()
        assert r == {"type": md.EXTERNAL, "points_xy": [[0, 0], [4, 0], [4, 3]], "closed": True,
                     "arcs": []}
        _refused(lambda: d.add((1, 1)), "closed")
        assert d.undo() and not d.closed

    def test_arcs(self):
        d = tools.BoundaryDrawing(md.MATERIAL)
        d.add((1.0, 0.0))
        d.start_arc()
        assert d.add((0.0, 1.0)) == "through"
        assert d.add((-1.0, 0.0)) == "arc"             # half a circle: two segments
        r = d.result()
        assert len(r["points_xy"]) == 3 and [a["segment"] for a in r["arcs"]] == [0, 1]
        assert all(math.dist(a["centre"], (0, 0)) < 1e-12 for a in r["arcs"])
        _refused(lambda: tools.BoundaryDrawing(md.STAGE).start_arc(), "first vertex")
        _refused(lambda: tools.BoundaryDrawing(md.STAGE).result(), "Nothing")

    def test_refusals(self):
        d = tools.BoundaryDrawing(md.EXCAVATION)
        d.add((0, 0))
        _refused(lambda: d.add((0, 0)), "last vertex")
        d.add((1, 0))
        _refused(lambda: d.result(), "three vertices")


class TestPicking:
    def test_vertex_and_segment(self):
        m = md.Model(boundaries=(md.Boundary("ext", md.EXTERNAL, ((0.0, 0.0), (10.0, 0.0),
                                                                  (10.0, 10.0)), True),
                                 md.Boundary("hole", md.EXCAVATION,
                                             ((6.0, 4.0), (5.0, 5.0), (4.0, 4.0), (5.0, 3.0)),
                                             True, tuple(md.SegmentAttr(k, (5.0, 4.0))
                                                         for k in range(4)))))
        assert tools.pick_vertex(m, (10.05, 0.0), 0.1) == ("ext", 1, (10.0, 0.0))
        assert tools.pick_vertex(m, (10.5, 0.0), 0.1) is None
        assert tools.pick_segment(m, (5.0, -0.05), 0.1)[:2] == ("ext", 0)
        bid, k, foot = tools.pick_segment(m, (5.75, 4.75), 0.1)
        assert (bid, k) == ("hole", 0) and abs(math.dist(foot, (5.0, 4.0)) - 1.0) < 1e-12


def _window():
    w = MainWindow()
    w.resize(900, 700)
    w.show()
    _KEEP.append(w)
    w.act_new()
    return w


def _close(w):
    w.confirm_discard = lambda: True
    w.close()


def _draw_square(w, side=10.0):
    w.tools.start(tc.DRAW, md.EXTERNAL)
    for p in ((0, 0), (side, 0), (side, side), (0, side)):
        w.tools.clicked(*p, LEFT)
    w.tools.clicked(0.3, 0.3, RIGHT)                  # the right button finishes


class TestTheWindowsTools:
    def test_a_boundary_by_clicks_is_one_step(self):
        w = _window()
        try:
            _draw_square(w)
            m = w.session.model
            assert [b.vertices for b in m.boundaries] == [((0.0, 0.0), (10.0, 0.0), (10.0, 10.0),
                                                           (0.0, 10.0))]
            assert w.session.history()[0] == ["Add boundary"] and w.tools.mode == tc.NONE
        finally:
            _close(w)

    def test_snapped_and_cut(self):
        w = _window()
        try:
            _draw_square(w)
            w.view.zoom_all()
            off = 2.0 / w.view.pixels_per_unit()              # 2 pixels
            w.tools.start(tc.DRAW, md.MATERIAL)
            w.tools.clicked(0.0 + off, 4.0, LEFT)             # onto the left side
            w.tools.clicked(10.0 - off, 4.0, LEFT)            # onto the right side
            w.tools.key(Qt.Key.Key_Return)
            m = w.session.model
            mat = m.boundary("mat1")
            assert mat.vertices == ((0.0, 4.0), (10.0, 4.0))
            assert (0.0, 4.0) in m.boundary("ext1").vertices
            assert "2" in w.statusBar().currentMessage()
            # onto a vertex, 2 pixels away
            w.tools.start(tc.DRAW, md.STAGE)
            w.tools.clicked(10.0 - off, 10.0 - off, LEFT)
            assert w.tools.drawing.vertices == ((10.0, 10.0),)
            w.tools.key(Qt.Key.Key_Escape)
            assert w.tools.mode == tc.NONE and len(w.session.model.boundaries) == 2
        finally:
            _close(w)

    def test_typed_points_table_circle_and_arc(self):
        w = _window()
        try:
            w.tools.start(tc.DRAW, md.EXTERNAL)
            for text in ("0, 0", "@20, 0", "@20<90", "0, 20"):
                w.statusBar().coord_input.setText(text)
                w.statusBar().coord_input.returnPressed.emit()
            w.tools.key(Qt.Key.Key_Return)
            assert w.session.model.boundary("ext1").vertices == ((0.0, 0.0), (20.0, 0.0),
                                                                 (20.0, 20.0), (0.0, 20.0))
            w.statusBar().coord_input.setText("1,5,2")
            w.statusBar().coord_input.returnPressed.emit()                                        # said, not taken
            w.tools.start(tc.CIRCLE, md.EXCAVATION)
            w.tools.clicked(10.0, 10.0, LEFT)
            w.statusBar().coord_input.setText("@2<0")
            w.statusBar().coord_input.returnPressed.emit()
            hole = w.session.model.boundary("exc1")
            assert len(hole.segments) == 4 and hole.vertices[0] == (12.0, 10.0)
            w.tools.start(tc.DRAW, md.STAGE)
            w.tools.points([(5.0, 2.0)])
            w.tools.start_arc()
            w.tools.points([(5.5, 3.0), (5.0, 4.0)])
            w.tools.finish()
            stg = w.session.model.boundary("stg1")
            assert len(stg.segments) == 1 and stg.segments[0].arc is not None
        finally:
            _close(w)

    def test_editing_vertices(self):
        w = _window()
        try:
            _draw_square(w)
            w.view.zoom_all()
            w.tools.start(tc.MOVE)
            w.tools.clicked(12.0, 12.0, LEFT)                 # nothing there
            assert "No vertex within 8 pixels" in w.statusBar().currentMessage()
            w.tools.clicked(10.0, 10.0, LEFT)
            w.tools.clicked(11.0, 12.0, LEFT)
            assert (11.0, 12.0) in w.session.model.boundary("ext1").vertices
            w.tools.start(tc.INSERT)
            w.tools.clicked(5.0, 0.0, LEFT)
            assert (5.0, 0.0) in w.session.model.boundary("ext1").vertices
            w.tools.start(tc.DELETE_VERTEX)
            w.tools.clicked(5.0, 0.0, LEFT)
            assert (5.0, 0.0) not in w.session.model.boundary("ext1").vertices
            w.tools.start(tc.DELETE_BOUNDARY)
            w.tools.clicked(0.0, 5.0, LEFT)
            assert w.session.model.boundaries == ()
        finally:
            _close(w)


class TestTheTable:
    def test_rows(self):
        assert read_rows([("1.5", "2"), ("", ""), ("3", "-4.25")]) == [(1.5, 2.0), (3.0, -4.25)]
        try:
            read_rows([("1", "x")])
        except TableError as err:
            assert "Row 1" in str(err)
        else:
            raise AssertionError("a cell that is not a number was taken")
        dlg = CoordinatesDialog()
        dlg.set_rows([("0", "0"), ("2.5", "0")])
        dlg._accept()
        assert dlg.result_points == [(0.0, 0.0), (2.5, 0.0)]
        dlg.set_rows([("0", "y")])
        dlg._accept()
        assert "Row 1" in dlg.error.text()
