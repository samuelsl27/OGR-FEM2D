# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Entering geometry, without Qt (spec 006, T22; D10, D12; guide §8): what a
typed point means, a boundary being drawn, and finding the vertex or the
segment under the cursor.

**A typed point** is read by the status bar's X, Y field
(``ogr_ui.point_entry.read_point``, OGR GUI 0.1.3, which took this
program's reading of D10 and D12): absolute (``x, y`` or ``x y``),
relative to the reference the tools give (``@dx, dy``) or polar from it
(``@d<angle``, degrees anticlockwise from +x), the decimal mark the point
or the comma. Until v0.0.15 the reading was here (``parse_point``).

**A boundary being drawn** (``BoundaryDrawing``) collects vertices by clicks
or typed points, and arcs by three points (the last vertex, one through
which it passes, its end); an arc of half a circle or more is two segments
(``model.shapes``). A point on the first vertex closes it. Each step can be
undone. What it gives is what ``boundary_add`` takes.

**Picking** (``pick_vertex``, ``pick_segment``) works in pixels of the
screen, turned into model units by the zoom: a click 2 px off a segment
when zoomed out picks it (the reference program picked nothing, and said
nothing, P13).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from ...model import model as md
from ...model import shapes

Point = tuple[float, float]

#: how far from a vertex or a segment a click still picks it, in pixels
PICK_PX = 8.0


class EntryError(ValueError):
    """A step of drawing that cannot be taken; ``message`` is English for
    ``tr()``."""


@dataclass
class BoundaryDrawing:
    """A boundary being drawn (see the module's notes)."""
    kind: str
    states: list = field(default_factory=list)      # the Drawn after each step
    arc_through: Point | None = None
    arc_mode: bool = False

    @property
    def drawn(self) -> shapes.Drawn | None:
        return self.states[-1] if self.states else None

    @property
    def vertices(self) -> tuple[Point, ...]:
        return self.drawn.vertices if self.drawn else ()

    @property
    def last(self) -> Point | None:
        return self.vertices[-1] if self.vertices else None

    @property
    def closed(self) -> bool:
        return bool(self.drawn and self.drawn.closed)

    def start_arc(self) -> None:
        """The next two points draw an arc from the last vertex: through the
        first, ending at the second."""
        if self.last is None:
            raise EntryError("An arc starts at a vertex: give the first vertex before it.")
        self.arc_mode, self.arc_through = True, None

    def add(self, p: Point) -> str:
        """Add a point; what it did: ``vertex``, ``through`` (the middle of
        an arc), ``arc`` or ``closed``. A point on the first vertex closes
        the boundary (three vertices at least)."""
        p = (float(p[0]), float(p[1]))
        if self.closed:
            raise EntryError("The boundary is closed: finish it, or undo the last step.")
        if self.drawn is None:
            self.states.append(shapes.Drawn.start(p))
            return "vertex"
        if self.arc_mode:
            if self.arc_through is None:
                if p == self.last:
                    raise EntryError("The point an arc goes through cannot be its start.")
                self.arc_through = p
                return "through"
            piece = shapes.arc_three_points(self.last, self.arc_through, p)
            self.states.append(self.drawn.arc_to(piece))
            self.arc_mode, self.arc_through = False, None
            return "closed" if self.closed else "arc"
        if p == self.last:
            raise EntryError("That point is the last vertex already.")
        if p == self.vertices[0] and len(self.vertices) >= 3:
            self.states.append(shapes.Drawn(self.drawn.vertices, self.drawn.segments, True))
            return "closed"
        if p in self.vertices:
            raise EntryError("That point is a vertex of this boundary already.")
        self.states.append(self.drawn.line_to(p))
        return "vertex"

    def undo(self) -> bool:
        if self.arc_mode:
            self.arc_mode, self.arc_through = False, None
            return True
        if self.states:
            self.states.pop()
            return True
        return False

    def result(self) -> dict:
        """The arguments of ``boundary_add`` for what is drawn."""
        d = self.drawn
        if d is None:
            raise EntryError("Nothing is drawn yet.")
        closed = d.closed or self.kind in md.CLOSED_KINDS
        need = 3 if closed else 2
        if len(d.vertices) < need:
            raise EntryError("A closed boundary needs three vertices, an open one two.")
        return {"type": self.kind, "points_xy": [list(v) for v in d.vertices],
                "closed": closed,
                "arcs": [{"segment": s.index, "centre": list(s.arc)} for s in d.segments]}


# ------------------------------------------------------------- picking
def pick_vertex(m: md.Model, p: Point, tol: float):
    """(boundary id, index, vertex) of the vertex nearest ``p`` within
    ``tol`` model units, or None."""
    best = None
    for b in m.boundaries:
        for i, v in enumerate(b.vertices):
            d = math.dist(v, p)
            if d <= tol and (best is None or d < best[0]):
                best = (d, b.id, i, v)
    return None if best is None else best[1:]


def _on_segment(a: Point, b: Point, arc: Point | None, p: Point) -> tuple[float, Point] | None:
    """(distance, foot) of ``p`` to the segment (or its arc), or None when
    the foot falls outside it."""
    if arc is None:
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        if L2 == 0.0:
            return None
        t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2
        if not 0.0 < t < 1.0:
            return None
        foot = (a[0] + t * dx, a[1] + t * dy)
        return math.dist(p, foot), foot
    r = math.dist(a, arc)
    ang = math.atan2(p[1] - arc[1], p[0] - arc[0])
    foot = (arc[0] + r * math.cos(ang), arc[1] + r * math.sin(ang))
    t0 = math.atan2(a[1] - arc[1], a[0] - arc[0])
    t1 = math.atan2(b[1] - arc[1], b[0] - arc[0])
    sweep = (t1 - t0 + math.pi) % (2 * math.pi) - math.pi
    rel = (ang - t0 + math.pi) % (2 * math.pi) - math.pi
    if not (0.0 < rel / sweep < 1.0 if sweep else False):
        return None
    return math.dist(p, foot), foot


def pick_segment(m: md.Model, p: Point, tol: float):
    """(boundary id, segment index, the point on it nearest ``p``) of the
    segment nearest ``p`` within ``tol``, or None. The point is on the arc
    of an arc segment."""
    best = None
    for b in m.boundaries:
        for k in range(b.n_segments):
            a, c = b.segment(k)
            attr = b.attr(k)
            got = _on_segment(a, c, attr.arc if attr is not None else None, p)
            if got is not None and got[0] <= tol and (best is None or got[0] < best[0]):
                best = (got[0], b.id, k, got[1])
    return None if best is None else best[1:]
