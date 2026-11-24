# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The edits of a model, as pure functions: a model in, a new model out (spec
006, RF-1, RF-7). The operations and the interface apply them through
``history.Document.edit``, which makes each one a step to undo (RF-8).

A model being drawn is not yet a valid model (it may have no external
boundary, or a region without its material): an edit checks what it is
given and what it touches, and leaves the problems of the whole model to
``model.problems``, which the interface lists. What an edit refuses, it
refuses with ``ModelError`` naming the argument or the object.

The boundaries and their vertices (T2):

* ``add_boundary``, ``delete_boundary``, ``rename_boundary``,
  ``set_boundary_kind``, ``set_closed``, ``translate_boundary``;
* ``move_vertex``, ``insert_vertex``, ``delete_vertex``;
* ``set_arc``, ``set_divisions``: the attributes of one segment.

Boundaries meet only at the vertices they share (spec 004, D15), and a
vertex is shared by having the same coordinates. So:

* moving a vertex moves it in every boundary that has it, and with it every
  span end, vertex condition and point load that names it: the boundaries
  stay joined and nothing is left pointing at a point that is gone;
* a vertex inserted on a side goes into every boundary that has that side;
* an edit that would pull shared geometry apart (translating a boundary that
  shares a vertex, deleting a vertex next to a shared side) is refused, and
  the error names the other boundary;
* an edit that would leave an arc off its circle (moving a vertex of an
  arc, deleting a vertex next to one) is refused: the arc is taken off first
  with ``set_arc``, so nothing changes shape without being asked;
* nothing that depends on a boundary is removed without being asked:
  deleting a boundary with conditions or loads on it is refused unless
  ``with_dependents`` says to take them too.

The mesh is kept: an edit of the geometry makes it the mesh of another
geometry, which ``translate.context`` refuses to calculate with, saying so
(spec 004, RF-11; the reference program deleted it, P10).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import replace

from ..engine.model import Problem
from ..mesh import geometry as g
from ..mesh import _trig
from . import model as md

Point = tuple[float, float]

#: The rules of what the edits refuse (the model's own, md.RULES, besides).
RULES = ("boundary_unknown", "vertex_unknown", "segment_unknown", "not_on_segment",
         "vertex_taken", "shared_vertex", "shared_side", "arc_vertex", "divisions_vertex",
         "in_use")

#: The prefix of the ids ``next_id`` gives, by kind of boundary.
ID_PREFIX = {md.EXTERNAL: "ext", md.MATERIAL: "mat", md.EXCAVATION: "exc", md.STAGE: "stg"}


def _fail(rule: str, where: str, message: str):
    raise md.ModelError([Problem(rule, where, message)])


def _pt(p) -> Point:
    return (float(p[0]), float(p[1]))


def _boundary(m: md.Model, boundary_id: str) -> md.Boundary:
    b = m.boundary(boundary_id)
    if b is None:
        known = ", ".join(repr(x.id) for x in m.boundaries) or "none"
        _fail("boundary_unknown", f"boundary {boundary_id!r}",
              f"does not exist (the boundaries are: {known})")
    return b


def _put(m: md.Model, b: md.Boundary) -> md.Model:
    return replace(m, boundaries=tuple(b if x.id == b.id else x for x in m.boundaries))


def _check(m: md.Model, b: md.Boundary) -> md.Boundary:
    """The problems of ``b`` alone (its kind, vertices, closure, segment
    attributes, the axis), with the model's own rules; and its id unique."""
    found: list[Problem] = []
    add = lambda rule, where, message: found.append(Problem(rule, where, message))
    md._boundary_problems(md.Model(analysis=m.analysis, boundaries=(b,)), add)
    found = [p for p in found if p.rule != "external"]
    if sum(1 for x in m.boundaries if x.id == b.id) > 1:
        found.append(Problem("boundary_id", md.boundary_name(b), "the id is repeated"))
    if found:
        raise md.ModelError(found)
    return b


def _segment(b: md.Boundary, k) -> int:
    if not (md._int(k) and 0 <= k < b.n_segments):
        _fail("segment_unknown", f"{md.boundary_name(b)}, segment {k!r}",
              f"there is no such segment (it has {b.n_segments}, from 0)")
    return k


def _vertex_index(b: md.Boundary, index) -> int:
    if not (md._int(index) and 0 <= index < len(b.vertices)):
        _fail("vertex_unknown", f"{md.boundary_name(b)}, vertex {index!r}",
              f"there is no such vertex (it has {len(b.vertices)}, from 0)")
    return index


def _scale(m: md.Model, *extra: Point) -> float:
    pts = [v for b in m.boundaries for v in b.vertices] + list(extra)
    if not pts:
        return 1.0
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return _trig.norm(max(xs) - min(xs), max(ys) - min(ys)) or 1.0


def _segments_touching(b: md.Boundary, i: int) -> list[int]:
    """The segments of ``b`` that have vertex i at an end."""
    n = len(b.vertices)
    out = []
    if b.closed or i > 0:
        out.append((i - 1) % n)
    if b.closed or i < n - 1:
        out.append(i)
    return sorted(set(out))


def _side(b: md.Boundary, k: int) -> frozenset:
    p, q = b.segment(k)
    return frozenset((_pt(p), _pt(q)))


def _attrs_renumbered(b: md.Boundary, change) -> tuple[md.SegmentAttr, ...]:
    """The segment attributes of ``b`` with ``change(attr)`` giving a list of
    the attributes it becomes (renumbered, or split, or none)."""
    out = []
    for s in b.segments:
        out.extend(change(s))
    return tuple(sorted(out, key=lambda s: s.index))


# ---------------------------------------------------------- the boundaries
def next_id(m: md.Model, kind: str) -> str:
    """A free id for a new boundary of ``kind``: its prefix and the first
    number not taken (``ext1``, ``exc2``…)."""
    prefix = ID_PREFIX.get(kind, "b")
    taken = {b.id for b in m.boundaries}
    k = 1
    while f"{prefix}{k}" in taken:
        k += 1
    return f"{prefix}{k}"


def add_boundary(m: md.Model, kind: str, vertices, closed: bool | None = None,
                 segments=(), boundary_id: str | None = None, name: str = "") -> md.Model:
    """A new boundary at the end of the model. ``closed`` by default as its
    kind asks (external and excavation closed, the others open); the id, by
    default ``next_id``. Refused if the boundary breaks a rule of its own
    (the model's rules), or if its id is taken."""
    if closed is None:
        closed = kind in md.CLOSED_KINDS
    bid = next_id(m, kind) if boundary_id is None else boundary_id
    b = md.Boundary(bid, kind, tuple(_pt(v) for v in vertices), bool(closed),
                    tuple(segments), name)
    out = replace(m, boundaries=m.boundaries + (b,))
    _check(out, b)
    return out


def _dependents(m: md.Model, b: md.Boundary) -> tuple[list[int], list[int]]:
    """The conditions and the loads that would be left without ``b``: those
    on a span of it, and those at a vertex that only it has."""
    others = {v for x in m.boundaries if x.id != b.id for v in x.vertices}
    only = set(b.vertices) - others
    conds = [k for k, c in enumerate(m.conditions)
             if (c.span is not None and c.span.boundary == b.id) or c.vertex in only]
    lds = [k for k, ld in enumerate(m.loads)
           if (isinstance(ld, md.DistributedLoad) and ld.span.boundary == b.id)
           or (isinstance(ld, md.PointLoad) and ld.vertex in only)]
    return conds, lds


def delete_boundary(m: md.Model, boundary_id: str, with_dependents: bool = False) -> md.Model:
    """The model without the boundary. If conditions or loads depend on it,
    refused, unless ``with_dependents``: then they go too."""
    b = _boundary(m, boundary_id)
    conds, lds = _dependents(m, b)
    if (conds or lds) and not with_dependents:
        names = [f"condition {k}" for k in conds] + [f"load {k}" for k in lds]
        _fail("in_use", md.boundary_name(b),
              f"{', '.join(names)} depend on it: delete them first, or delete it with "
              "its dependents")
    return replace(m, boundaries=tuple(x for x in m.boundaries if x.id != b.id),
                   conditions=tuple(c for k, c in enumerate(m.conditions) if k not in conds),
                   loads=tuple(ld for k, ld in enumerate(m.loads) if k not in lds))


def rename_boundary(m: md.Model, boundary_id: str, name: str) -> md.Model:
    return _put(m, replace(_boundary(m, boundary_id), name=str(name)))


def set_boundary_kind(m: md.Model, boundary_id: str, kind: str) -> md.Model:
    """The boundary becomes one of another kind (an open one cannot become
    external or an excavation: those are closed)."""
    b = replace(_boundary(m, boundary_id), kind=kind)
    out = _put(m, b)
    _check(out, b)
    return out


def set_closed(m: md.Model, boundary_id: str, closed: bool) -> md.Model:
    """Close an open boundary (a segment from its last vertex to its first)
    or open a closed one (its last segment goes, and with it its
    attributes). External and excavation boundaries stay closed."""
    b = _boundary(m, boundary_id)
    if bool(closed) == b.closed:
        return m
    last = len(b.vertices) - 1
    segs = b.segments if closed else tuple(s for s in b.segments if s.index != last)
    nb = replace(b, closed=bool(closed), segments=segs)
    out = _put(m, nb)
    _check(out, nb)
    return out


def translate_boundary(m: md.Model, boundary_id: str, dx: float, dy: float) -> md.Model:
    """The boundary moved by (dx, dy), its arc centres with it, and the span
    ends, vertex conditions and point loads at its vertices. Refused if it
    shares a vertex with another boundary (moving it would pull them
    apart)."""
    b = _boundary(m, boundary_id)
    if not md._finite(dx, dy):
        _fail("boundary", md.boundary_name(b), f"({dx!r}, {dy!r}) is not two finite numbers")
    for x in m.boundaries:
        if x.id != b.id and set(x.vertices) & set(b.vertices):
            _fail("shared_vertex", md.boundary_name(b),
                  f"shares a vertex with {md.boundary_name(x)}: moving it would pull them apart")
    shift = lambda p: (p[0] + float(dx), p[1] + float(dy))
    moved = {v: shift(v) for v in b.vertices}
    nb = replace(b, vertices=tuple(moved[v] for v in b.vertices),
                 segments=tuple(replace(s, arc=None if s.arc is None else shift(s.arc))
                                for s in b.segments))
    out = _moved_references(_put(m, nb), moved, only=b.id)
    _check(out, nb)
    return out


# ------------------------------------------------------------- the vertices
def _moved_references(m: md.Model, moved: dict, only: str | None = None) -> md.Model:
    """Span ends, vertex conditions and point loads at a moved vertex follow
    it (span ends of boundary ``only`` alone, when it is given)."""
    def span(s: md.Span) -> md.Span:
        if only is not None and s.boundary != only:
            return s
        return replace(s, start=moved.get(s.start, s.start), end=moved.get(s.end, s.end))

    conds = tuple(replace(c, span=span(c.span)) if c.span is not None
                  else replace(c, vertex=moved.get(c.vertex, c.vertex)) for c in m.conditions)
    lds = tuple(replace(ld, span=span(ld.span)) if isinstance(ld, md.DistributedLoad)
                else replace(ld, vertex=moved.get(ld.vertex, ld.vertex)) for ld in m.loads)
    return replace(m, conditions=conds, loads=lds)


def move_vertex(m: md.Model, point, to) -> md.Model:
    """The vertex at ``point`` moved to ``to``, in every boundary that has
    it, with the span ends, vertex conditions and point loads that name it.
    Refused if no boundary has it, if a vertex is at ``to`` already, or if a
    segment of an arc ends at it (the arc would leave its circle)."""
    p, q = _pt(point), _pt(to)
    if not md._finite(*q):
        _fail("boundary", f"vertex {p}", f"the new place {to!r} is not two finite numbers")
    holders = [b for b in m.boundaries if p in b.vertices]
    if not holders:
        _fail("vertex_unknown", f"vertex {p}", "is not a vertex of any boundary")
    if q == p:
        return m
    if any(q in b.vertices for b in m.boundaries):
        _fail("vertex_taken", f"vertex {p}",
              f"there is a vertex at {q} already: two vertices cannot be put in one place")
    for b in holders:
        i = b.vertices.index(p)
        for k in _segments_touching(b, i):
            a = b.attr(k)
            if a is not None and a.arc is not None:
                _fail("arc_vertex", f"{md.boundary_name(b)}, vertex {i}",
                      f"segment {k} is an arc: moving its end would take it off its circle "
                      "(take the arc off first)")
    out = replace(m, boundaries=tuple(
        replace(b, vertices=tuple(q if v == p else v for v in b.vertices)) for b in m.boundaries))
    out = _moved_references(out, {p: q})
    for b in out.boundaries:
        if q in b.vertices:
            _check(out, b)
    return out


def _on_segment(m: md.Model, b: md.Boundary, k: int, p: Point) -> bool:
    """``p`` lies on segment k of ``b``, away from its ends: on the straight
    segment or on its arc, within the geometric tolerance of the mesher
    (``ARC_TOL`` of the size of the model)."""
    a, c = (_pt(v) for v in b.segment(k))
    if p in (a, c):
        return False
    tol = g.ARC_TOL * _scale(m, p)
    attr = b.attr(k)
    if attr is None or attr.arc is None:
        ab = _trig.length(a, c)
        if abs(g._cross(a, c, p)) > tol * ab:
            return False
        t = ((p[0] - a[0]) * (c[0] - a[0]) + (p[1] - a[1]) * (c[1] - a[1])) / (ab * ab)
        return 0.0 < t < 1.0
    arc = g._ArcGeo(a, c, _pt(attr.arc))
    if abs(_trig.length(p, arc.c) - arc.r) > tol:
        return False
    return arc.on_open_arc(p, tol)


def _insert_into(b: md.Boundary, k: int, p: Point) -> md.Boundary:
    """``b`` with ``p`` between vertex k and k + 1 (segment k split in two;
    an arc keeps its centre in both halves; divisions are refused before)."""
    def renumber(s):
        if s.index < k:
            return [s]
        if s.index > k:
            return [replace(s, index=s.index + 1)]
        return [replace(s, index=k), replace(s, index=k + 1)]
    return replace(b, vertices=b.vertices[:k + 1] + (p,) + b.vertices[k + 1:],
                   segments=_attrs_renumbered(b, renumber))


def insert_vertex(m: md.Model, boundary_id: str, segment: int, point) -> md.Model:
    """A vertex at ``point`` on segment ``segment`` of the boundary, and in
    every other boundary that has that side. Refused if the point is not on
    the segment (or its arc), or if the segment has forced divisions (they
    are of the whole side: split, they would have to be invented)."""
    b = _boundary(m, boundary_id)
    k = _segment(b, segment)
    p = _pt(point)
    if not md._finite(*p):
        _fail("boundary", f"{md.boundary_name(b)}, segment {k}",
              f"{point!r} is not two finite numbers")
    if not _on_segment(m, b, k, p):
        _fail("not_on_segment", f"{md.boundary_name(b)}, segment {k}",
              f"{p} is not on it, away from its ends")
    side = _side(b, k)
    out = m
    for x in m.boundaries:
        for j in range(x.n_segments):
            if _side(x, j) != side:
                continue
            a = x.attr(j)
            if a is not None and a.divisions is not None:
                _fail("divisions_vertex", f"{md.boundary_name(x)}, segment {j}",
                      f"has {a.divisions} forced divisions: take them off before splitting it")
            nx = _insert_into(x, j, p)
            out = _put(out, nx)
            _check(out, nx)
            break
    return out


def delete_vertex(m: md.Model, boundary_id: str, index: int) -> md.Model:
    """The boundary without its vertex ``index`` (its two segments become
    one). Refused if a segment that ends at it is an arc or has divisions, or
    is a side of another boundary; if a span of the boundary ends at it; or
    if a vertex condition or point load is at it and no other boundary has
    it."""
    b = _boundary(m, boundary_id)
    i = _vertex_index(b, index)
    p = b.vertices[i]
    where = f"{md.boundary_name(b)}, vertex {i}"
    touching = _segments_touching(b, i)
    for k in touching:
        a = b.attr(k)
        if a is not None and a.arc is not None:
            _fail("arc_vertex", where, f"segment {k} is an arc: take the arc off first")
        if a is not None and a.divisions is not None:
            _fail("divisions_vertex", where,
                  f"segment {k} has forced divisions: take them off first")
        side = _side(b, k)
        for x in m.boundaries:
            if x.id != b.id and any(_side(x, j) == side for j in range(x.n_segments)):
                _fail("shared_side", where,
                      f"segment {k} is also a side of {md.boundary_name(x)}: deleting the "
                      "vertex would pull them apart")
    users = [f"condition {k}" for k, c in enumerate(m.conditions)
             if c.span is not None and c.span.boundary == b.id and p in (c.span.start, c.span.end)]
    users += [f"load {k}" for k, ld in enumerate(m.loads)
              if isinstance(ld, md.DistributedLoad) and ld.span.boundary == b.id
              and p in (ld.span.start, ld.span.end)]
    if not any(x.id != b.id and p in x.vertices for x in m.boundaries):
        users += [f"condition {k}" for k, c in enumerate(m.conditions) if c.vertex == p]
        users += [f"load {k}" for k, ld in enumerate(m.loads)
                  if isinstance(ld, md.PointLoad) and ld.vertex == p]
    if users:
        _fail("in_use", where, f"{', '.join(users)} name it: change or delete them first")

    # the segment that remains takes the index of the first of the two
    n = len(b.vertices)
    if b.closed and i == 0:
        def renumber(s):
            return [] if s.index in (n - 1, 0) else [replace(s, index=s.index - 1)]
    else:
        def renumber(s):
            if s.index < i - 1:
                return [s]
            if s.index in (i - 1, i):
                return []
            return [replace(s, index=s.index - 1)]
    nb = replace(b, vertices=b.vertices[:i] + b.vertices[i + 1:],
                 segments=_attrs_renumbered(b, renumber))
    out = _put(m, nb)
    _check(out, nb)
    return out


# ------------------------------------------------------------ the segments
def set_arc(m: md.Model, boundary_id: str, segment: int, centre) -> md.Model:
    """Segment ``segment`` becomes the minor arc about ``centre``, or
    straight with None. Refused if its two ends are not on one circle about
    the centre, or if the centre is on the chord (half a circle or more is
    split by a vertex: spec 003, D4), with the tolerance of the model's
    rule ``arc``."""
    b = _boundary(m, boundary_id)
    k = _segment(b, segment)
    old = b.attr(k)
    arc = None if centre is None else _pt(centre)
    if arc is not None and md._finite(*arc):
        a, c = (_pt(v) for v in b.segment(k))
        ra, rc = _trig.length(a, arc), _trig.length(c, arc)
        scale = _scale(m, arc)
        where = f"{md.boundary_name(b)}, segment {k}"
        if abs(ra - rc) > g.ARC_TOL * max(ra, rc, scale):
            _fail("arc", where, f"its ends are at {ra!r} and {rc!r} from the centre {arc}: "
                                "not on one circle")
        if abs(g._cross(a, c, arc)) <= g.ARC_TOL * scale * _trig.length(a, c):
            _fail("arc", where, "the centre is on the chord: half a circle or more must be "
                                "split by a vertex (spec 003, D4)")
    div = None if old is None else old.divisions
    rest = tuple(s for s in b.segments if s.index != k)
    new = () if arc is None and div is None else (md.SegmentAttr(k, arc, div),)
    nb = replace(b, segments=tuple(sorted(rest + new, key=lambda s: s.index)))
    out = _put(m, nb)
    _check(out, nb)
    return out


def set_divisions(m: md.Model, boundary_id: str, segment: int, divisions: int | None) -> md.Model:
    """Segment ``segment`` divided in ``divisions`` by the mesher, or as the
    mesher decides with None."""
    b = _boundary(m, boundary_id)
    k = _segment(b, segment)
    old = b.attr(k)
    arc = None if old is None else old.arc
    rest = tuple(s for s in b.segments if s.index != k)
    new = () if arc is None and divisions is None else (md.SegmentAttr(k, arc, divisions),)
    nb = replace(b, segments=tuple(sorted(rest + new, key=lambda s: s.index)))
    out = _put(m, nb)
    _check(out, nb)
    return out
