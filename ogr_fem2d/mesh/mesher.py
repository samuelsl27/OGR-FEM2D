# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The mesher of a geometry, in two steps, its output and the translation of
the output into the input of the engine (spec 003, RF-3, RF-11, RF-15;
docs/malla/entrada.md).

``mesh(m)``:

1. **Step 1** (``discretize``, RF-2): the nodes of every segment, the arcs
   in pieces of at most 10 degrees (D15).
2. **Step 2**: the planar straight line graph (``pslg``: the pieces,
   labelled with their segment, and the arcs' centres; a seed per region; a
   point in every void; the corners of the windows) meshed by the core's
   quality triangulation (``ogr_core.fem.refine``, OGR-Core 0.2.6; D2), with
   the bound B of the settings and the size bound of ``sizing``. It keeps
   every node of step 1, may add more on a segment (D10), and splits the
   pieces of an arc on the arc (D14), so every node of an arc is on its
   circle.
3. With six-node triangles, the mid-side nodes (``quadratic``, D4): on the
   arc for the sides that are pieces of an arc.
4. The checks (``checks``, RF-13 and RF-14). **The safety net of D14 (a)**:
   if every element rejected by its jacobian has a side on an arc, the whole
   mesh is made again with twice the divisions on the arcs of the rejected
   elements and on the other arcs of their circles, at most
   ``MAX_ARC_RETRIES`` times; the notes say how many and
   with which divisions (rule 12). An element rejected with no side on an
   arc, or still rejected after the last try, stops it with the error of
   RF-13. The same net catches the core's refusal of a piece of a segment
   or a vertex between the chord of a piece of arc and the arc
   (``ARC_CODES``): a valid geometry with a layer thinner than the sagitta
   of its pieces (found in T12; an extension of D14 (a), to be reviewed by
   the owner).
5. The output: the nodes (the corners in the order of the triangulation,
   whose first ones are the points of step 1 in their order; then the
   mid-side nodes), the elements with their region and material, a boundary
   per segment ("segment a-b", its corners from a to b), the notes and the
   warnings.

The notes (rule 12) carry every value that decided the mesh: the settings
and their defaults (B and the angle it guarantees, the size bounds, the
divisions of step 1 per segment), what the refinement did (nodes added on
each segment and where, RF-3 and D10; the triangles left above B, D6; the
smallest input angle and the bound of theorem 12), the arcs (the largest
turn of a piece, the B above which Pav and Walkington prove the
termination, whether the B asked for meets it, and the core's message that
with arcs no source proves it for this mesher, D15), the safety net and the
quality summary (``quality``, RF-12).

Errors: a ``geometry.MeshInputError`` for an input that breaks the schema;
the core's ``refine.QualityMeshError`` when the refinement cannot finish (too
many triangles, edges too short for the floating point); a
``checks.MeshError`` for a mesh that cannot be delivered. Never a bad mesh
delivered in silence.

A mesh carries, besides its nodes and elements:

* the region and the material of every element;
* for every boundary of the geometry (a segment, or a boundary the mesher
  made itself, like the outer circle of the radial mesh), the chain of its
  corner nodes in order, and for every piece of the chain the elements that
  have it as a side, as (element, side k), side k going from corner k to
  corner (k + 1) % 3 (the convention of ``model.EdgeLoad``), and its
  mid-side node with six-node triangles. That is what spec 004 needs to put
  loads and conditions on the geometry and not on the mesh (spec 003,
  plan, "Decisiones de diseño");
* the notes: every value that decided the mesh (rule 12);
* the warnings of the checks (``checks.check``).

``boundary_map`` refuses a chain that is not made of sides of the mesh:
that is RF-3, every segment a union of sides.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import math

from ogr_core.fem import refine

from ..engine import model as em
from . import checks, discretize, pslg, quadratic, quality, sizing
from . import geometry as g
from .quadratic import edge_key

Point = tuple[float, float]


@dataclass(frozen=True)
class Boundary:
    """A boundary of the geometry in the mesh. ``name`` says which: "segment
    a-b" for a segment of the input, or the name the mesher gave it."""
    name: str
    nodes: tuple[int, ...]                                 # corners, in order
    sides: tuple[tuple[tuple[int, int], ...], ...]         # per piece: (element, k)
    mids: tuple[int, ...] = ()                             # per piece, six-node meshes


@dataclass(frozen=True)
class Mesh:
    """What the mesher delivers."""
    analysis: str
    nodes: tuple[Point, ...]
    elements: tuple[tuple[int, ...], ...]
    element_region: tuple[int, ...]
    element_material: tuple[int, ...]
    boundaries: tuple[Boundary, ...]
    notes: Mapping[str, object] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def boundary(self, name: str) -> Boundary:
        for b in self.boundaries:
            if b.name == name:
                return b
        raise KeyError(name)


class BoundaryError(ValueError):
    """A chain of nodes that is not made of sides of the mesh."""


def boundary_map(elements: Sequence[tuple[int, ...]],
                 chains: Sequence[tuple[str, Sequence[int]]]) -> tuple[Boundary, ...]:
    """The boundaries of ``chains`` (name, corner nodes in order) on the
    mesh: for every piece, the (element, side) pairs that have it and, with
    six-node elements, its mid-side node."""
    sides: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for e, el in enumerate(elements):
        for k in range(3):
            sides.setdefault(edge_key(el[k], el[(k + 1) % 3]), []).append((e, k))
    six = bool(elements) and len(elements[0]) == 6
    out = []
    for name, chain in chains:
        per_piece, mids = [], []
        for u, v in zip(chain, chain[1:]):
            found = sides.get(edge_key(u, v))
            if not found:
                raise BoundaryError(f"{name}: the piece {u}-{v} is not a side of the mesh "
                                    "(spec 003, RF-3)")
            per_piece.append(tuple(found))
            if six:
                e, k = found[0]
                mids.append(elements[e][3 + k])
        out.append(Boundary(name, tuple(chain), tuple(per_piece), tuple(mids)))
    return tuple(out)


def to_engine(mesh: Mesh, materials: Sequence[em.Material], stages: Sequence[em.Stage],
              initial_stresses=None) -> em.EngineModel:
    """The engine's input: the mesh's nodes and elements, the material of
    every element (``mesh.element_material`` indexes ``materials``), and the
    stages and initial stresses the caller gives (spec 004 makes them from
    the model). Validated by the engine's own rules."""
    model = em.EngineModel(mesh.analysis, tuple(mesh.nodes), tuple(mesh.elements),
                           tuple(materials), tuple(mesh.element_material), tuple(stages),
                           initial_stresses)
    return em.validate(model)


#: The most triangles a mesh may have before the core stops it with an
#: error (its default; spec 003, "Casos límite": a size bound very small for
#: the domain ends in an error that says so, not in a run that never ends).
MAX_TRIANGLES = 1_000_000

#: How many times the safety net of D14 (a) makes the mesh again.
MAX_ARC_RETRIES = 3


#: The errors of the core that a finer division of an arc removes: a piece
#: of another segment, or a vertex, between the chord of a piece of arc and
#: the arc (OGR-Core 0.2.6). The geometry is valid (its arcs and segments do
#: not meet), but its pieces of 10 degrees are too coarse for it: a layer
#: thinner than the sagitta of a piece, R (1 - cos 5 deg) = 0.0038 R (found
#: in T12).
ARC_CODES = (refine.M.REFINE_SEGMENT_IN_ARC, refine.M.REFINE_VERTEX_IN_ARC)


class _TooCoarse(Exception):
    """A mesh that twice the divisions on some arcs may mend: elements
    rejected by their jacobian, all with a side on an arc, or an error of
    ``ARC_CODES``. ``give_up`` raises the error the caller gets when the
    tries are over."""

    def __init__(self, segments, reason, elements, give_up):
        super().__init__(reason)
        self.segments = segments                  # indices in geometry.segments
        self.reason = reason
        self.elements = elements
        self.give_up = give_up


def mesh(m: g.MeshInput) -> Mesh:
    """The mesh of a geometry (see the module's notes)."""
    g.validate(m)
    segs = g.segments(m)
    base = dict(enumerate(n for _s, n in discretize.divisions(m)))
    more: dict[int, int] = {}
    retries: list[dict] = []
    while True:
        disc = discretize.discretize(m, more)
        try:
            return _mesh_once(m, segs, disc, tuple(retries))
        except _TooCoarse as coarse:
            if len(retries) == MAX_ARC_RETRIES:
                coarse.give_up()
                raise AssertionError("give_up() did not raise") from None
            doubled = _same_circle(m, segs, coarse.segments)
            for k in doubled:
                more[k] = 2 * more.get(k, base[k])
            retries.append({"reason": coarse.reason, "elements": coarse.elements,
                            "divisions": tuple((f"segment {segs[k].a}-{segs[k].b}", more[k])
                                               for k in doubled)})


def _same_circle(m: g.MeshInput, segs, found) -> tuple[int, ...]:
    """The arcs of ``found`` and every other arc on one of their circles
    (the same centre, the same radius to ARC_TOL of the input's size): the
    core names the first piece it meets, and a circle divided alike keeps
    its symmetry."""
    tol = g.ARC_TOL * g._scale(m)

    def circle(k):
        s = segs[k]
        return s.arc.centre, g._ArcGeo(m.points[s.a], m.points[s.b], s.arc.centre).r

    wanted = [circle(k) for k in found]
    out = []
    for k, s in enumerate(segs):
        if s.arc is None:
            continue
        c, r = circle(k)
        if k in found or any(c == wc and abs(r - wr) <= tol for wc, wr in wanted):
            out.append(k)
    return tuple(out)


def _triangulate(m: g.MeshInput, segs, graph):
    """The core's quality triangulation of ``graph``; an error of
    ``ARC_CODES`` on an arc becomes a ``_TooCoarse``."""
    bound = sizing.size_bound(m)
    try:
        return refine.quality_triangulation(
            graph, max_ratio=m.settings.quality_bound,
            size=bound if bound.floor is not None else None, max_triangles=MAX_TRIANGLES)
    except refine.QualityMeshError as err:
        if err.code not in ARC_CODES:
            raise
        args = err.note.args
        pieces = [args[key] for key in ("k", "j") if key in args]
        arcs = {graph.segments[i][2] for i in pieces if segs[graph.segments[i][2]].arc is not None}
        if not arcs:
            raise

        def give_up(err=err):
            raise err

        raise _TooCoarse(arcs, err.code, (), give_up) from None


def _mesh_once(m: g.MeshInput, segs, disc, retries) -> Mesh:
    st = m.settings
    graph = pslg.build(m, disc)
    qt = _triangulate(m, segs, graph)
    corners = tuple((n.x, n.y) for n in qt.mesh.nodes)
    triangles = tuple(tuple(e.nodes) for e in qt.mesh.elements)
    # the chain of every segment, and the sides that are pieces of an arc
    chain_of: dict[int, list[int]] = {}
    arc_sides: dict[tuple[int, int], int] = {}
    for (_u, _v, label), chain in zip(graph.segments, qt.segment_vertices):
        whole = chain_of.setdefault(label, [])
        whole.extend(chain if not whole else chain[1:])
        if segs[label].arc is not None:
            for a, b in zip(chain, chain[1:]):
                arc_sides[edge_key(a, b)] = label
    nodes, elements = corners, triangles
    if st.nodes_per_element == 6:
        quad = quadratic.promote(corners, triangles,
                                 {key: segs[k].arc.centre for key, k in arc_sides.items()})
        nodes, elements = quad.nodes, quad.elements
    found = checks.indexed_element_problems(nodes, elements, m.analysis)
    if found:
        folded: set[int] = set()
        for e, _p in found:
            tri = elements[e]
            on_arc = {arc_sides[key] for key in (edge_key(tri[k], tri[(k + 1) % 3])
                                                 for k in range(3)) if key in arc_sides}
            if not on_arc:
                break
            folded |= on_arc
        else:
            def give_up():
                checks.check(nodes, elements, m.analysis, found=found)

            raise _TooCoarse(folded, "jacobian", tuple(e for e, _p in found), give_up)
    report = checks.check(nodes, elements, m.analysis, found=found)
    boundaries = boundary_map(elements, [(f"segment {segs[k].a}-{segs[k].b}", tuple(chain_of[k]))
                                         for k in range(len(segs))])
    return Mesh(m.analysis, tuple(nodes), tuple(tuple(e) for e in elements),
                tuple(e.region_index for e in qt.mesh.elements),
                tuple(e.material_id for e in qt.mesh.elements),
                boundaries, _notes(m, segs, disc, graph, qt, corners, triangles, retries),
                report.warnings)


def _notes(m, segs, disc, graph, qt, corners, triangles, retries) -> dict:
    """Every value that decided the mesh (rule 12)."""
    st = m.settings
    core = qt.notes
    name = [f"segment {s.a}-{s.b}" for s in segs]
    added = []
    for k in range(len(segs)):
        new = []
        for (_u, _v, label), chain in zip(graph.segments, qt.segment_vertices):
            if label == k:
                new.extend(chain[1:-1])
        if new:
            added.append({"segment": name[k], "nodes": tuple(new),
                          "points": tuple(corners[i] for i in new)})
    b = float(st.quality_bound)
    arcs = core["arc_pieces"] > 0
    return {
        "kind": st.kind,
        "nodes_per_element": st.nodes_per_element,
        "quality_bound": b,
        "angle_guaranteed": math.degrees(math.asin(1.0 / (2.0 * b))),
        "boundary_nodes": st.boundary_nodes if st.kind == g.GRADED else None,
        "max_size": st.max_size if st.kind == g.GRADED else None,
        "size": disc.size,
        "elements_asked": st.elements if st.kind == g.UNIFORM else None,
        "windows": tuple((tuple(w.polygon), w.size) for w in st.windows),
        "window_corners": len(graph.vertices) - len(disc.points),
        "max_arc_turn": math.degrees(g.MAX_ARC_TURN),
        "divisions": tuple((name[k], ds.divisions) for k, ds in enumerate(disc.segments)),
        "added_on_segments": tuple(added),
        "min_input_angle": core["min_input_angle"],
        "theorem_12_bound": core["theorem_12_bound"],
        "above_ratio": tuple(core["above_ratio"]),
        "declined_splits": core["declined_splits"],
        "length_unit": core["length_unit"],
        "arc_pieces": core["arc_pieces"],
        "arc_turn": core["arc_turn"],
        "arc_bound": core["arc_bound"],
        "arc_termination_proven": core["arc_bound"]["met"] if arcs else None,
        "arc_unproven": core["arc_unproven"],
        "arc_retries": retries,
        "max_triangles": MAX_TRIANGLES,
        "quality": quality.summary(corners, triangles, b),
    }
