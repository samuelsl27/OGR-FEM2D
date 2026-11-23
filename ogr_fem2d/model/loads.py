# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The loads of the model on the sides and nodes of the mesh, stage by stage
(spec 004, RF-10, D6, D10).

**Distributed loads.** A load runs along its span, from its start vertex to
its end vertex, forward in the boundary's order of vertices. Its value is
linear in the length along the span (the length of the arc on an arc):
v(s) = v0 + (v1 - v0) s / L (elementary geometry). Every side of the mesh on
the span gets an ``EdgeLoad`` of the engine, with the value at its two
corners, on the ONE element that is active on that side in the stage: a
side with none or two (a contact between two active regions) is an error
that names the load, the boundary and the stage (RF-10). The total of the
stage is factor x value (D10); a factor 0 puts nothing.

* NORMAL, positive pushing into the ground, that is into the active element:
  the engine's normal traction, positive outward of the element, is its
  opposite (``conventions.engine_normal``), with no tangential part; exact
  on a curved side too (docs/motor/entrada.md);
* the other orientations, in global components: VERTICAL (0, -1),
  HORIZONTAL (1, 0), ANGLE_FROM_HORIZONTAL (cos a, sin a), and
  ANGLE_TO_BOUNDARY the tangent of the span (in its direction) turned by a
  anticlockwise, at each corner (the core's directions,
  ``ogr_core.loads.DistributedLoad.direction_vector``). On a curved side the
  engine takes the load linear between the corners, an approximation of the
  turning tangent (docs/motor/entrada.md).

**Point loads**, at a vertex, which is a node of the mesh (the point i of the
mesher input is node i): a ``NodalLoad`` of factor x magnitude along the
orientation. In axisymmetry, the force of the whole ring (spec 002, D2). A
point load at a node with no active element is an error.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from ..engine import model as em
from . import conventions
from . import model as md


def _name(m: md.Model, k: int) -> str:
    ld = m.loads[k]
    return f"load {k}" + (f" ({ld.name})" if ld.name else "")


def direction(orientation: str, angle: float, tangent=None) -> tuple[float, float]:
    """The unit vector a load pushes along (not NORMAL)."""
    if orientation == md.VERTICAL:
        return (0.0, -1.0)
    if orientation == md.HORIZONTAL:
        return (1.0, 0.0)
    a = math.radians(angle)
    if orientation == md.ANGLE_FROM_HORIZONTAL:
        return (math.cos(a), math.sin(a))
    if orientation == md.ANGLE_TO_BOUNDARY:
        tx, ty = tangent
        return (tx * math.cos(a) - ty * math.sin(a), tx * math.sin(a) + ty * math.cos(a))
    raise ValueError(orientation)


class _Piece:
    """A segment of the span: its chain of corners in the direction of the
    span, the length along the span of each, and its tangent."""

    def __init__(self, ctx, b: md.Boundary, k: int, offset: float):
        p, q = b.segment(k)
        seg_index = ctx.segment_of[(b.id, k)]
        seg = ctx.geometry.segments[seg_index]
        bd = ctx.mesh_boundary[seg_index]
        start = ctx.node_of(p)
        forward = bd.nodes[0] == start
        self.nodes = list(bd.nodes) if forward else list(reversed(bd.nodes))
        self.sides = list(bd.sides) if forward else list(reversed(bd.sides))
        self.p, self.q, self.arc = p, q, seg.arc
        xy = ctx.mesh.nodes
        if self.arc is None:
            self.length = math.dist(p, q)
            self.s = {n: offset + math.dist(p, xy[n]) for n in self.nodes}
        else:
            c = self.arc
            r = 0.5 * (math.dist(p, c) + math.dist(q, c))
            self.r = r
            self.ccw = (p[0] - c[0]) * (q[1] - c[1]) - (p[1] - c[1]) * (q[0] - c[0]) > 0.0

            def turned(x):
                ux, uy = p[0] - c[0], p[1] - c[1]
                vx, vy = x[0] - c[0], x[1] - c[1]
                return abs(math.atan2(ux * vy - uy * vx, ux * vx + uy * vy))

            self.length = r * turned(q)
            self.s = {n: offset + r * turned(xy[n]) for n in self.nodes}
        # the ends are the vertices, exactly
        self.s[self.nodes[0]] = offset
        self.s[self.nodes[-1]] = offset + self.length

    def tangent(self, x) -> tuple[float, float]:
        if self.arc is None:
            d = math.dist(self.p, self.q)
            return ((self.q[0] - self.p[0]) / d, (self.q[1] - self.p[1]) / d)
        c = self.arc
        rx, ry = x[0] - c[0], x[1] - c[1]
        r = math.hypot(rx, ry)
        return (-ry / r, rx / r) if self.ccw else (ry / r, -rx / r)


def _distributed(ctx, i: int, ld: md.DistributedLoad, k: int, factor: float, active,
                 problems) -> list:
    m = ctx.model
    b = m.boundary(ld.span.boundary)
    pieces, offset = [], 0.0
    for seg in md.span_indices(b, ld.span):
        piece = _Piece(ctx, b, seg, offset)
        pieces.append(piece)
        offset += piece.length
    total = offset
    v0, v1 = factor * ld.start_value, factor * ld.end_value

    def value(s):
        return v0 + (v1 - v0) * s / total

    out = []
    elements, xy = ctx.mesh.elements, ctx.mesh.nodes
    for piece in pieces:
        for sides in piece.sides:
            on = [(e, side) for e, side in sides if active[e]]
            if len(on) != 1:
                problems.append(em.Problem(
                    "load_not_on_boundary",
                    f"stage {m.stages[k].id!r}, {_name(m, i)}, boundary {b.id!r}",
                    f"a side of its span has {len(on)} active elements: a load acts on the "
                    "outside of the active domain (one active element), not on a contact "
                    "nor on an excavated part (RF-10)"))
                return out
            e, side = on[0]
            c0, c1 = elements[e][side], elements[e][(side + 1) % 3]
            a0, a1 = value(piece.s[c0]), value(piece.s[c1])
            if ld.orientation == md.NORMAL:
                out.append(em.EdgeLoad(e, side, (conventions.engine_normal(a0), 0.0),
                                       (conventions.engine_normal(a1), 0.0), normal=True))
            else:
                d0 = direction(ld.orientation, ld.angle, piece.tangent(xy[c0]))
                d1 = direction(ld.orientation, ld.angle, piece.tangent(xy[c1]))
                out.append(em.EdgeLoad(e, side, (a0 * d0[0], a0 * d0[1]),
                                       (a1 * d1[0], a1 * d1[1])))
    return out


def stage_loads(ctx, k: int, active) -> tuple[tuple, tuple]:
    m = ctx.model
    edge, nodal, problems = [], [], []
    alive = {n for e, on in zip(ctx.mesh.elements, active) if on for n in e}
    for i, ld in enumerate(m.loads):
        factor = ld.factors[k]
        if factor == 0.0:
            continue
        if isinstance(ld, md.DistributedLoad):
            edge.extend(_distributed(ctx, i, ld, k, factor, active, problems))
        else:
            n = ctx.node_of(ld.vertex)
            if n not in alive:
                problems.append(em.Problem(
                    "load_not_on_boundary", f"stage {m.stages[k].id!r}, {_name(m, i)}",
                    f"its vertex {ld.vertex} has no active element in this stage"))
                continue
            dx, dy = direction(ld.orientation, ld.angle)
            f = factor * ld.magnitude
            nodal.append(em.NodalLoad(n, f * dx, f * dy))
    if problems:
        raise md.ModelError(problems)
    return tuple(edge), tuple(nodal)
