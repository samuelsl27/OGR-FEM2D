# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The queries of a results file (spec 005, RF-11 to RF-13 and RF-15; D9,
D12, D14).

Every value is a field quantity of the catalogue (``quantities``), in the
user's convention (D1) and in the stored units (m, kN, kPa; the table
converts, D15). Each row says where its value comes from (H6):

* ``point``: the value at an integration point, as the engine gave it;
* ``fe``: a displacement, the finite-element field, its shape functions
  times the nodal values;
* ``spr``: a stress or a strain from the values recovered at the nodes
  (``recovery``, D5), interpolated with the element's shape functions
  (Zienkiewicz and Taylor 2000, Eq. 14.27); ``element`` when some node took
  its element's own field, ``spr+element`` when both;
* no value, with the reason: ``excavated`` (in an element not active in the
  stage), ``outside`` (in no element), ``removed`` (a node without an active
  element: it keeps its displacement but has no stress).

A stress or a strain is recovered and interpolated as a TENSOR, and the
quantity (sigma_1, q, ...) is computed from the tensor at the point: the
principal stress of the interpolated tensor, not the interpolation of the
principal stresses.

Where a point is on a contact between materials, a stress or a strain has
one row per material, in the order of the materials, at the same distance:
the jump is shown, not averaged (D9). A displacement, continuous, has one.

``View(results, stage)`` keeps what the queries of a stage share (the
locator, the tensors, the recovered values); the functions take it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..engine.reference import solver
from ..model import conventions
from . import locate, quantities as qt, recovery, store

POINT, FE = "point", "fe"


@dataclass(frozen=True)
class Row:
    point: int                      # the index of the queried point
    x: float
    y: float
    distance: float | None          # along the query; None where it has no sense
    value: float | None
    element: int | None = None
    material: int | None = None
    source: str = ""
    reason: str = ""


@dataclass(frozen=True)
class Query:
    quantity: str
    stage: int
    stage_id: str
    rows: tuple[Row, ...]
    what: str                       # "line", "boundary", "nodes", "points", "history"
    method: str                     # how the values were obtained
    #: the settings that decided the rows, defaults included (rule 12)
    settings: tuple[tuple[str, object], ...] = ()

    @property
    def unit(self) -> str:
        return qt.get(self.quantity).unit

    @property
    def convention(self) -> str:
        return qt.get(self.quantity).convention

    def values(self) -> list[float | None]:
        return [r.value for r in self.rows]


def locator(results: store.Results) -> locate.Locator:
    """The locator of the mesh of ``results``, made once and kept with it
    (no state outside the object, rule 5)."""
    if getattr(results, "_locator", None) is None:
        mesh = results.mesh()
        results._locator = locate.Locator(mesh.nodes, mesh.elements)
    return results._locator


class View:
    """A stage of a results file, as the queries need it."""

    def __init__(self, results: store.Results, stage: int):
        self.results, self.stage = results, stage
        self.mesh = results.mesh()
        self.analysis = results.header.analysis
        self.info = results.stage_info(stage)
        self.active = results.field(stage, "active").astype(bool)
        self.shape = solver.SHAPES[self.mesh.elements.shape[1]]
        self._cache: dict = {}

    @property
    def locator(self) -> locate.Locator:
        """Where a point is in the mesh, made the first time a point is
        asked (v0.0.15: 0.24 s with case 005, and drawing a field never
        asks one)."""
        if "locator" not in self._cache:
            self._cache["locator"] = locator(self.results)
        return self._cache["locator"]

    # ------------------------------------------------ the user's tensors
    def displacement(self) -> np.ndarray:
        if "u" not in self._cache:
            self._cache["u"] = conventions.user_displacement(
                self.results.field(self.stage, "displacement"))
        return self._cache["u"]

    def tensor(self, kind: str) -> np.ndarray:
        """The user's stress or strain (P, 4) at the points."""
        if kind not in self._cache:
            if kind == qt.STRESS:
                t = conventions.user_stress(self.results.field(self.stage, "stress"))
            else:
                t = qt.strain4(conventions.user_strain(self.results.field(self.stage, "strain")),
                               self.analysis)
            self._cache[kind] = t
        return self._cache[kind]

    def recovered(self, kind: str) -> recovery.Recovered:
        key = ("recovered", kind)
        if key not in self._cache:
            m = self.mesh
            self._cache[key] = recovery.recover(m.nodes, m.elements, m.element_material,
                                                self.active, m.points, m.point_element,
                                                self.tensor(kind))
        return self._cache[key]

    # ------------------------------------------------ values at a point
    def at(self, quantity: str, x: float, y: float):
        """[(value, element, material, source)] at (x, y), one per material
        for a stress or a strain, one for a displacement; or the reason
        there is none."""
        kind = qt.get(quantity).kind
        status, hits = self.locator.find(x, y, self.active)
        if status != locate.IN:
            return status
        material = self.mesh.element_material
        out, seen = [], set()
        for e, lc in hits:
            mat = int(material[e])
            if mat in seen:
                continue
            seen.add(mat)
            n = np.asarray(self.shape.shape_functions(*lc))
            nodes = self.mesh.elements[e]
            if kind == qt.DISPLACEMENT:
                tensor, source = n @ self.displacement()[nodes], FE
            else:
                rec = self.recovered(kind)
                tensor = n @ rec.values[e]
                present = {int(s) for s in rec.source[e]}
                source = "+".join(recovery.SOURCES[s] for s in (recovery.SPR, recovery.ELEMENT)
                                  if s in present)
            out.append((float(qt.of(quantity, tensor)), int(e), mat, source))
            if kind == qt.DISPLACEMENT:
                break
        return out


def method_of(quantity: str) -> str:
    if qt.get(quantity).kind == qt.DISPLACEMENT:
        return "finite-element field (shape functions)"
    return ("superconvergent patch recovery per material (Zienkiewicz and Taylor 2000, §14.4), "
            "interpolated with the shape functions (Eq. 14.27)")


def _rows_at(view: View, quantity: str, points, distances) -> list[Row]:
    rows = []
    for i, ((x, y), d) in enumerate(zip(points, distances)):
        got = view.at(quantity, x, y)
        if isinstance(got, str):
            rows.append(Row(i, x, y, d, None, reason=got))
            continue
        for value, e, mat, source in got:
            rows.append(Row(i, x, y, d, value, e, mat, source))
    return rows


# --------------------------------------------------------------- the line
def spread(vertices, n: int | None):
    """The points of a polyline and their distance from the first: its
    vertices (``n`` None), or ``n`` >= 2 points at equal distances along
    the whole of it, both ends included."""
    v = [(float(x), float(y)) for x, y in vertices]
    if len(v) < 2:
        raise ValueError("a line needs two points or more")
    lengths = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(v, v[1:])]
    if any(L == 0.0 for L in lengths):
        raise ValueError("two consecutive points of the line are the same")
    cumulative = [0.0]
    for L in lengths:
        cumulative.append(cumulative[-1] + L)
    if n is None:
        return v, cumulative
    if n < 2:
        raise ValueError("a line needs n >= 2 points")
    total = cumulative[-1]
    points, distances = [], []
    for i in range(n):
        d = total * i / (n - 1)
        k = min(max(0, np.searchsorted(cumulative, d, side="right") - 1), len(lengths) - 1)
        t = (d - cumulative[k]) / lengths[k]
        a, b = v[k], v[k + 1]
        points.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        distances.append(d)
    points[-1] = v[-1]                       # the end exactly
    return points, distances


def line(view: View, quantity: str, vertices, n: int | None = None) -> Query:
    """The quantity along a line or a polyline (RF-11)."""
    points, distances = spread(vertices, n)
    return Query(quantity, view.stage, view.info["id"],
                 tuple(_rows_at(view, quantity, points, distances)), "line", method_of(quantity),
                 (("vertices", tuple(tuple(map(float, p)) for p in vertices)),
                  ("points", "at the vertices" if n is None else n)))


def at(view: View, quantity: str, x: float, y: float) -> Query:
    """The quantity at (x, y) in the stage (spec 006, T31: the value under
    the cursor, interpolated exactly as a line's, D11): a row per material
    that meets there, or one without value saying why (outside the mesh, in
    an excavated region)."""
    return Query(quantity, view.stage, view.info["id"],
                 tuple(_rows_at(view, quantity, [(float(x), float(y))], [None])), "at",
                 method_of(quantity), (("x", float(x)), ("y", float(y))))


# --------------------------------------------- every node and every point
def all_nodes(view: View, quantity: str) -> Query:
    """The quantity at every node (RF-13): a displacement once per node; a
    stress or a strain once per node and material, or without value at a
    node with no active element."""
    m = view.mesh
    kind = qt.get(quantity).kind
    rows = []
    if kind == qt.DISPLACEMENT:
        values = qt.of(quantity, view.displacement())
        for i, (x, y) in enumerate(m.nodes):
            rows.append(Row(i, float(x), float(y), None, float(values[i]), source=FE))
        return Query(quantity, view.stage, view.info["id"], tuple(rows), "nodes", method_of(quantity))
    rec = view.recovered(kind)
    value = qt.of(quantity, rec.values)                         # (E, n)
    first: dict = {}
    for e in np.flatnonzero(view.active):
        mat = int(m.element_material[e])
        for a, node in enumerate(m.elements[e]):
            key = (int(node), mat)
            if key not in first:
                first[key] = (float(value[e, a]), int(e), recovery.SOURCES[int(rec.source[e, a])])
    with_value = {node for node, _ in first}
    for i, (x, y) in enumerate(m.nodes):
        if i not in with_value:
            rows.append(Row(i, float(x), float(y), None, None, reason="removed"))
            continue
        for (node, mat) in sorted(k for k in first if k[0] == i):
            v, e, source = first[(node, mat)]
            rows.append(Row(i, float(x), float(y), None, v, e, mat, source))
    return Query(quantity, view.stage, view.info["id"], tuple(rows), "nodes", method_of(quantity))


def all_points(view: View, quantity: str) -> Query:
    """The quantity at every integration point, the engine's value (RF-13).
    A displacement is not a quantity of the points: ``all_nodes``."""
    kind = qt.get(quantity).kind
    if kind == qt.DISPLACEMENT:
        raise ValueError(f"{quantity!r} is a displacement: it is at the nodes (all_nodes)")
    m = view.mesh
    values = qt.of(quantity, view.tensor(kind))
    rows = []
    for i, ((x, y), e) in enumerate(zip(m.points, m.point_element)):
        if view.active[e]:
            rows.append(Row(i, float(x), float(y), None, float(values[i]), int(e),
                            int(m.element_material[e]), POINT))
        else:
            rows.append(Row(i, float(x), float(y), None, None, int(e), int(m.element_material[e]),
                            reason="excavated"))
    return Query(quantity, view.stage, view.info["id"], tuple(rows), "points",
                 "the integration points, as the engine gave them")


# ------------------------------------------------------- on a boundary
INSIDE, OUTSIDE, LEFT, RIGHT = "inside", "outside", "left", "right"


def _arc(a, b, centre):
    """(radius, start angle, signed sweep) of the minor arc from a to b."""
    ta = math.atan2(a[1] - centre[1], a[0] - centre[0])
    tb = math.atan2(b[1] - centre[1], b[0] - centre[0])
    sweep = (tb - ta + math.pi) % (2.0 * math.pi) - math.pi
    return math.hypot(a[0] - centre[0], a[1] - centre[1]), ta, sweep


def signed_area(b) -> float:
    """The signed area the closed boundary ``b`` encloses (positive when
    its vertices go anticlockwise), arcs included: half the integral of
    x dy - y dx along it."""
    total = 0.0
    for k in range(b.n_segments):
        a, c = b.segment(k)
        attr = b.attr(k)
        if attr is None or attr.arc is None:
            total += a[0] * c[1] - c[0] * a[1]
        else:
            o = attr.arc
            r, _t, sweep = _arc(a, c, o)
            total += o[0] * (c[1] - a[1]) - o[1] * (c[0] - a[0]) + r * r * sweep
    return 0.5 * total


def boundary_points(b, n_per_segment: int | None = None, distance: float = 0.0,
                    side: str | None = None):
    """The points of a query on the boundary ``b`` of the model (D12): its
    vertices (``n_per_segment`` None) or n points on each segment, on its
    arc if it is one (the start of each segment and n - 1 between; the end
    of an open boundary too), moved ``distance`` along the boundary's normal
    to ``side``: inside or outside for a closed boundary, left or right
    (of its direction) for an open one. At a vertex the normal is the
    bisector of those of its two segments. Returns the points and their
    distance along the boundary."""
    if distance != 0.0:
        allowed = (INSIDE, OUTSIDE) if b.closed else (LEFT, RIGHT)
        if side not in allowed:
            raise ValueError(f"a distance needs its side, one of {allowed} for this boundary")
    if n_per_segment is not None and n_per_segment < 1:
        raise ValueError("n_per_segment >= 1")
    sign = 0.0
    if distance != 0.0:
        if b.closed:
            ccw = signed_area(b) > 0.0                    # the left of an anticlockwise ring is inside
            sign = (1.0 if ccw else -1.0) * (1.0 if side == INSIDE else -1.0)
        else:
            sign = 1.0 if side == LEFT else -1.0

    def piece(k, t):
        """Point, unit tangent and length of segment k at fraction t."""
        a, c = b.segment(k)
        attr = b.attr(k)
        if attr is None or attr.arc is None:
            length = math.hypot(c[0] - a[0], c[1] - a[1])
            tx, ty = (c[0] - a[0]) / length, (c[1] - a[1]) / length
            return (a[0] + t * (c[0] - a[0]), a[1] + t * (c[1] - a[1])), (tx, ty), length
        o = attr.arc
        r, start, sweep = _arc(a, c, o)
        th = start + t * sweep
        s = 1.0 if sweep > 0.0 else -1.0
        point = (o[0] + r * math.cos(th), o[1] + r * math.sin(th))
        if t == 0.0:
            point = a                                    # the vertex itself, not its rounding
        return point, (-s * math.sin(th), s * math.cos(th)), r * abs(sweep)

    def left(tangent):
        return -tangent[1], tangent[0]

    segments = b.n_segments
    points, distances, along = [], [], 0.0
    for k in range(segments):
        count = 1 if n_per_segment is None else n_per_segment
        _p, _t, length = piece(k, 0.0)
        for i in range(count):
            t = i / count
            p, tangent, _ = piece(k, t)
            normal = left(tangent)
            if i == 0 and (b.closed or k > 0):
                prev = (k - 1) % segments
                _q, before, _ = piece(prev, 1.0)
                nb = left(before)
                sx, sy = normal[0] + nb[0], normal[1] + nb[1]
                size = math.hypot(sx, sy)
                if size > 1e-12:
                    normal = (sx / size, sy / size)
            points.append((p[0] + sign * distance * normal[0], p[1] + sign * distance * normal[1]))
            distances.append(along + t * length)
        along += length
    if not b.closed:
        p, tangent, _ = piece(segments - 1, 1.0)
        p = b.vertices[-1]
        normal = left(tangent)
        points.append((p[0] + sign * distance * normal[0], p[1] + sign * distance * normal[1]))
        distances.append(along)
    return points, distances


def on_boundary(view: View, quantity: str, m, boundary_id: str, n_per_segment: int | None = None,
                distance: float = 0.0, side: str | None = None) -> Query:
    """The quantity on a boundary of the model ``m``, or at ``distance`` to
    one ``side`` of it (RF-12, D12). The default distance is 0: on it."""
    b = m.boundary(boundary_id)
    if b is None:
        raise KeyError(f"no boundary {boundary_id!r} in the model")
    points, distances = boundary_points(b, n_per_segment, distance, side)
    return Query(quantity, view.stage, view.info["id"],
                 tuple(_rows_at(view, quantity, points, distances)), "boundary", method_of(quantity),
                 (("boundary", boundary_id),
                  ("points", "at the vertices" if n_per_segment is None else
                   f"{n_per_segment} per segment"),
                  ("distance", float(distance)), ("side", side if distance else "on it")))


# ---------------------------------------------------- through the stages
@dataclass(frozen=True)
class StageValue:
    stage: int
    stage_id: str
    name: str
    solved: bool
    rows: tuple[Row, ...]            # one per material on a contact; one without value otherwise


@dataclass(frozen=True)
class History:
    quantity: str
    x: float
    y: float
    stages: tuple[StageValue, ...]


def history(results: store.Results, quantity: str, x: float, y: float,
            views: dict | None = None) -> History:
    """The quantity at (x, y) in every stage of ``results`` (RF-15), each
    with whether the stage was solved. ``views`` (stage -> View) are the
    views already made, used and kept (v0.0.15: each history recovered
    every stage again)."""
    out = []
    views = {} if views is None else views
    for k in range(results.n_stages):
        if k not in views:
            views[k] = View(results, k)
        view = views[k]
        rows = tuple(_rows_at(view, quantity, [(x, y)], [None]))
        out.append(StageValue(k, view.info["id"], view.info["name"], view.info["solved"], rows))
    return History(quantity, float(x), float(y), tuple(out))


# ---------------------------------------------------------- the summary
@dataclass(frozen=True)
class Extreme:
    quantity: str
    at: str                          # "points" or "nodes"
    maximum: float
    max_where: tuple[float, float]
    minimum: float
    min_where: tuple[float, float]


@dataclass(frozen=True)
class Summary:
    stage: int
    stage_id: str
    extremes: tuple[Extreme, ...]
    max_displacement: float
    max_displacement_node: int
    reactions: tuple[float, float]                       # the total
    reactions_by_boundary: tuple[tuple[str, float, float], ...]


def _extreme(quantity, at, values, where) -> Extreme | None:
    values = np.asarray(values, dtype=float)
    ok = np.flatnonzero(~np.isnan(values))
    if not len(ok):
        return None
    hi, lo = ok[np.argmax(values[ok])], ok[np.argmin(values[ok])]
    return Extreme(quantity, at, float(values[hi]), tuple(map(float, where[hi])),
                   float(values[lo]), tuple(map(float, where[lo])))


def boundary_of_nodes(m) -> dict[int, str]:
    """node -> the id of the first boundary of the model (in its order) that
    has it, through the map segment -> nodes of the mesh (spec 003)."""
    from ..model import translate
    ctx = translate.context(m)
    owner: dict[int, str] = {}
    for b in m.boundaries:
        for k in range(b.n_segments):
            seg = ctx.segment_of.get((b.id, k))
            if seg is None:
                continue
            mb = ctx.mesh_boundary[seg]
            for node in tuple(mb.nodes) + tuple(mb.mids):
                owner.setdefault(int(node), b.id)
    return owner


def summary(view: View, m=None, quantities=None) -> Summary:
    """The extremes of each quantity at the points and at the nodes, where
    they are; the greatest displacement and its node; the reactions, in
    total and, with the model ``m``, by boundary of the model (a node on
    two boundaries counts for the first in the model's order; those on none,
    under "-") (RF-15, D14)."""
    mesh = view.mesh
    ids = [q.id for q in qt.CATALOGUE] if quantities is None else list(quantities)
    extremes = []
    for qid in ids:
        kind = qt.get(qid).kind
        if kind == qt.DISPLACEMENT:
            got = _extreme(qid, "nodes", qt.of(qid, view.displacement()), mesh.nodes)
            extremes += [got] if got else []
            continue
        points = qt.of(qid, view.tensor(kind))
        got = _extreme(qid, "points", points, mesh.points)
        extremes += [got] if got else []
        rec = view.recovered(kind)
        at_nodes = qt.of(qid, rec.values).reshape(-1)
        where = mesh.nodes[mesh.elements].reshape(-1, 2)
        got = _extreme(qid, "nodes", at_nodes, where)
        extremes += [got] if got else []
    u = qt.of("u", view.displacement())
    node = int(np.argmax(u))
    nodes = view.results.field(view.stage, "reaction_nodes")
    forces = view.results.field(view.stage, "reactions").reshape(-1, 2)
    total = (float(forces[:, 0].sum()), float(forces[:, 1].sum())) if len(forces) else (0.0, 0.0)
    by: list = []
    if m is not None:
        owner = boundary_of_nodes(m)
        sums: dict[str, list[float]] = {}
        for n, (rx, ry) in zip(nodes, forces):
            key = owner.get(int(n), "-")
            s = sums.setdefault(key, [0.0, 0.0])
            s[0] += float(rx)
            s[1] += float(ry)
        order = [b.id for b in m.boundaries] + ["-"]
        by = [(k, sums[k][0], sums[k][1]) for k in order if k in sums]
    return Summary(view.stage, view.info["id"], tuple(extremes), float(u[node]), node, total,
                   tuple(by))
