# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The FEM model and its validation (spec 004, RF-1, RF-3, RF-5, RF-6; the
file, section by section, in docs/modelo/formato.md).

A model is a VALUE: frozen dataclasses, so every edit gives a new model and
undoing is going back to the one before (``history``). It holds:

* the kind of analysis (plane strain or axisymmetry), the unit system the
  user sees (D5: the values are always in m, kN, kPa and kN/m3; the system
  only changes what is shown) and a summary;
* the boundaries (RF-1): one external (closed), material (open or closed),
  excavation (closed) and stage boundaries (open or closed: the ones that
  split a region to excavate it in parts). Every segment may carry an arc
  (its centre: the minor arc, as in the mesher, spec 003, D3 and D4) and a
  forced number of divisions (RF-2, D2). Boundaries meet only at vertices
  they share (D15); ``regions`` resolves the regions from them;
* the materials (RF-6): elastic and isotropic (D9), E and nu (None until
  given: a model opened from OGR Slip2D has none, and is not translated to
  the engine until they are, D16), the unit weight, and the mode of initial
  loading (D11);
* the stages (RF-3, D10): an ordered list, each with a stable id and a name;
* the assignments (D15, D10): a point of each region, its material, and
  whether it is excavated in each stage. The material is the region's for
  the whole analysis, before the first stage too: that is the initial state
  the field stress is the stress of, and the engine admits no change of
  material between stages (spec 002; RF-4). An excavated region coming back
  is refused (RF-4);
* the field stress (RF-7, D14): constant, or gravitational with a surface
  and horizontal strata, compression positive (D6);
* the conditions (RF-9, D7, D16) and the loads (RF-10) on the geometry: on a
  span of a boundary (from one of its vertices to another, forward in its
  order of vertices; or all of it) or on a vertex, with their state in every
  stage: whether a restraint acts, the factor of an imposed displacement or
  of a load (D10: total = factor x value; a factor 0 makes a load nought,
  None makes an imposed displacement not act). The default condition of the
  external boundary is written explicitly (rule 12);
* the settings of the mesh (those of the mesher, spec 003) and the mesh
  itself (D3), with the fingerprint of the mesher input it came from.

problems() checks everything the model can say about itself and returns
every problem found, each with its rule and its site; validate() raises
ModelError with all of them. A model can be valid as a document and still
not be ready for the engine (a material without E): that the translation
says (``translate``).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field

from ogr_core.loads.loads import LoadOrientation
from ogr_core.units.unit_system import SYSTEMS

from ..engine.initial_stress import Stratum
from ..engine.model import Problem
from ..engine.reference.quadrature import AXISYMMETRIC, PLANE_STRAIN
from ..mesh import geometry as g
from ..mesh.mesher import Boundary as MeshBoundary

ANALYSES = (PLANE_STRAIN, AXISYMMETRIC)

EXTERNAL = "external"
MATERIAL = "material"
EXCAVATION = "excavation"
STAGE = "stage"
BOUNDARY_KINDS = (EXTERNAL, MATERIAL, EXCAVATION, STAGE)
#: the kinds that must be closed (M05 of the interface analysis)
CLOSED_KINDS = (EXTERNAL, EXCAVATION)

#: Initial loading of a material (D11; D03, P05 and M10 of the interface
#: analysis): the field stress only, the field stress and the self weight,
#: the self weight only, or nothing.
FIELD_STRESS = "field_stress"
FIELD_AND_BODY = "field_stress_and_body_force"
BODY_FORCE = "body_force"
NO_LOADING = "none"
INITIAL_LOADINGS = (FIELD_STRESS, FIELD_AND_BODY, BODY_FORCE, NO_LOADING)

#: Conditions (RF-9): restrained in x, in y or both, freed, or an imposed
#: displacement.
X, Y, XY, FREE, DISPLACEMENT = "x", "y", "xy", "free", "displacement"
RESTRAINTS = (X, Y, XY, FREE)
CONDITION_KINDS = RESTRAINTS + (DISPLACEMENT,)

#: The orientations of a load, the core's (ogr_core.loads.LoadOrientation).
NORMAL = LoadOrientation.NORMAL_TO_BOUNDARY.value
VERTICAL = LoadOrientation.VERTICAL.value
HORIZONTAL = LoadOrientation.HORIZONTAL.value
ANGLE_FROM_HORIZONTAL = LoadOrientation.ANGLE_FROM_HORIZONTAL.value
ANGLE_TO_BOUNDARY = LoadOrientation.ANGLE_TO_BOUNDARY.value
ORIENTATIONS = tuple(o.value for o in LoadOrientation)
#: a point has no boundary of its own to be normal to
POINT_ORIENTATIONS = (VERTICAL, HORIZONTAL, ANGLE_FROM_HORIZONTAL)

DEFAULT_UNITS = "metric_kpa"

Point = tuple[float, float]


# ---------------------------------------------------------------- geometry
@dataclass(frozen=True)
class SegmentAttr:
    """What the mesher needs of segment ``index`` of a boundary (the side
    from vertex ``index`` to the next): an arc, by its centre, and a forced
    number of divisions (RF-2)."""
    index: int
    arc: Point | None = None
    divisions: int | None = None


@dataclass(frozen=True)
class Boundary:
    """A boundary: its kind, its vertices in order, whether it closes, and
    the attributes of the segments that have any."""
    id: str
    kind: str
    vertices: tuple[Point, ...]
    closed: bool
    segments: tuple[SegmentAttr, ...] = ()
    name: str = ""

    @property
    def n_segments(self) -> int:
        n = len(self.vertices)
        return n if self.closed else max(0, n - 1)

    def segment(self, k: int) -> tuple[Point, Point]:
        n = len(self.vertices)
        return self.vertices[k], self.vertices[(k + 1) % n]

    def attr(self, k: int) -> SegmentAttr | None:
        for s in self.segments:
            if s.index == k:
                return s
        return None


@dataclass(frozen=True)
class Span:
    """A stretch of a boundary: from vertex ``start`` to vertex ``end``,
    forward in the boundary's order of vertices (round the end of a closed
    one if need be); both None is the whole boundary."""
    boundary: str
    start: Point | None = None
    end: Point | None = None


# --------------------------------------------------------------- materials
@dataclass(frozen=True)
class Material:
    """An elastic isotropic material (D9). E and nu are None until given
    (D16); the unit weight acts only with a mode of initial loading that
    has the self weight (D11)."""
    id: str
    name: str = ""
    E: float | None = None
    nu: float | None = None
    unit_weight: float = 0.0
    initial_loading: str = FIELD_STRESS
    color: str = "#d4a373"


@dataclass(frozen=True)
class Stage:
    """A stage: a stable id and a name (D10)."""
    id: str
    name: str = ""


@dataclass(frozen=True)
class Assignment:
    """A region, by a point inside it: its material, and whether it is
    excavated in each stage, in the order of the model's stages."""
    point: Point
    material: str
    excavated: tuple[bool, ...]


# ------------------------------------------------------------ field stress
@dataclass(frozen=True)
class ConstantField:
    """The constant field (RF-7): the major and minor principal stresses in
    the plane, the out-of-plane one, and the angle of sigma_1 from x,
    anticlockwise, in degrees. COMPRESSION POSITIVE (D6)."""
    sigma_1: float = 0.0
    sigma_3: float = 0.0
    sigma_z: float = 0.0
    angle: float = 0.0


@dataclass(frozen=True)
class GravityField:
    """The gravitational field with a horizontal surface and horizontal
    strata (RF-7, D14): each stratum down to its ``bottom``, with its unit
    weight, K in the plane and Kz out of it (spec 002, D3)."""
    surface: float
    strata: tuple[Stratum, ...]


# -------------------------------------------------- conditions and loads
@dataclass(frozen=True)
class Condition:
    """A condition on a span or on a vertex (RF-9, D7).

    * a restraint (x, y, xy) or a release (free), with ``active``: whether
      it acts in each stage;
    * an imposed displacement, ``ux`` and/or ``uy`` (None: that component is
      not imposed), with ``factors``: the total in each stage is factor x
      value (D10), and a factor None means it does not act in that stage.
    """
    kind: str
    span: Span | None = None
    vertex: Point | None = None
    active: tuple[bool, ...] = ()
    ux: float | None = None
    uy: float | None = None
    factors: tuple[float | None, ...] = ()
    name: str = ""


@dataclass(frozen=True)
class DistributedLoad:
    """A load per unit length along a span (RF-10), linear from
    ``start_value`` at its start to ``end_value`` at its end, along its
    length. NORMAL: positive pushes into the ground, the active side of the
    span (D6); the other orientations are the core's directions
    (ogr_core.loads.DistributedLoad.direction_vector), positive along them.
    The total in each stage is factor x value (D10)."""
    span: Span
    start_value: float
    end_value: float
    orientation: str = NORMAL
    angle: float = 0.0
    factors: tuple[float, ...] = ()
    name: str = ""


@dataclass(frozen=True)
class PointLoad:
    """A force at a vertex (RF-10), along one of POINT_ORIENTATIONS. In
    axisymmetry, the force of the whole ring (the engine's convention, spec
    002, D2)."""
    vertex: Point
    magnitude: float
    orientation: str = VERTICAL
    angle: float = 0.0
    factors: tuple[float, ...] = ()
    name: str = ""


# ------------------------------------------------------------------ mesh
@dataclass(frozen=True)
class StoredMesh:
    """The mesh kept with the model (D3): what ``mesher.mesh`` gave, the
    region (not the material) of every element, and the fingerprint of the
    mesher input it was made from (``source``)."""
    nodes: tuple[Point, ...]
    elements: tuple[tuple[int, ...], ...]
    element_region: tuple[int, ...]
    boundaries: tuple[MeshBoundary, ...]
    notes: Mapping = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    source: str = ""

    def boundary(self, a: int, b: int) -> MeshBoundary | None:
        """The boundary of the mesher's segment a-b, whichever way named."""
        for name in (f"segment {a}-{b}", f"segment {b}-{a}"):
            for bd in self.boundaries:
                if bd.name == name:
                    return bd
        return None


@dataclass(frozen=True)
class Summary:
    title: str = ""
    author: str = ""
    date: str = ""
    notes: str = ""


# ------------------------------------------------------------------ model
@dataclass(frozen=True)
class Model:
    """Everything the engineer defines (see the module's notes)."""
    analysis: str = PLANE_STRAIN
    units: str = DEFAULT_UNITS
    summary: Summary = Summary()
    boundaries: tuple[Boundary, ...] = ()
    materials: tuple[Material, ...] = ()
    stages: tuple[Stage, ...] = (Stage("1", "Stage 1"),)
    assignments: tuple[Assignment, ...] = ()
    field: ConstantField | GravityField = ConstantField()
    #: the condition of the external boundary where nothing else is said
    #: (D16): fixed in x and y, written explicitly (rule 12)
    default_restraint: str = XY
    conditions: tuple[Condition, ...] = ()
    loads: tuple[DistributedLoad | PointLoad, ...] = ()
    mesh_settings: g.MeshSettings = g.MeshSettings()
    mesh: StoredMesh | None = None

    def boundary(self, boundary_id: str) -> Boundary | None:
        for b in self.boundaries:
            if b.id == boundary_id:
                return b
        return None

    def material(self, material_id: str) -> Material | None:
        for m in self.materials:
            if m.id == material_id:
                return m
        return None

    def stage_index(self, stage_id: str) -> int:
        for k, s in enumerate(self.stages):
            if s.id == stage_id:
                return k
        raise KeyError(stage_id)


def every_stage(model: Model, value=True) -> tuple:
    """``value`` once per stage of ``model``: the state of a condition or a
    load that acts the same in all of them."""
    return (value,) * len(model.stages)


# ---------------------------------------------------------------- problems
#: The rules problems() enforces; regions.RULES adds the geometric ones.
RULES = (
    "analysis", "units", "boundary", "boundary_id", "segment_attr", "external",
    "left_of_axis", "material", "material_id", "stage", "assignment",
    "reactivated", "field", "default_restraint", "condition", "load", "mesh",
)


class ModelError(ValueError):
    """The model breaks its own rules: every problem found."""

    def __init__(self, problems: list[Problem]):
        self.problems = problems
        super().__init__("the model is not valid:\n"
                         + "\n".join(f"  {p}" for p in problems))


def _finite(*values) -> bool:
    return all(isinstance(v, (int, float)) and not isinstance(v, bool)
               and math.isfinite(v) for v in values)


def _point(p) -> bool:
    return isinstance(p, tuple) and len(p) == 2 and _finite(*p)


def _int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def boundary_name(b: Boundary) -> str:
    """How a problem names a boundary: its id, and its name if it has one."""
    return f"boundary {b.id!r}" + (f" ({b.name})" if b.name else "")


def span_indices(b: Boundary, span: Span) -> list[int] | None:
    """The segments of ``b`` a span covers, in order (None if its vertices
    are not vertices of b, or do not make a stretch of it)."""
    n = len(b.vertices)
    if span.start is None and span.end is None:
        return list(range(b.n_segments))
    if span.start is None or span.end is None:
        return None
    try:
        i, j = b.vertices.index(span.start), b.vertices.index(span.end)
    except ValueError:
        return None
    if i == j:
        return None
    if b.closed:
        return [(i + k) % n for k in range((j - i) % n)]
    if j < i:
        return None
    return list(range(i, j))


def _boundary_problems(m: Model, add) -> None:
    seen: set[str] = set()
    externals = []
    for b in m.boundaries:
        where = boundary_name(b)
        if not isinstance(b.id, str) or not b.id:
            add("boundary_id", where, "a boundary needs an id (a non-empty string)")
        elif b.id in seen:
            add("boundary_id", where, "the id is repeated")
        seen.add(b.id)
        if b.kind not in BOUNDARY_KINDS:
            add("boundary", where, f"kind {b.kind!r} is not one of {BOUNDARY_KINDS}")
        if b.kind == EXTERNAL:
            externals.append(b)
        if not all(_point(v) for v in b.vertices):
            add("boundary", where, "a vertex is not two finite numbers")
            continue
        if b.kind in CLOSED_KINDS and not b.closed:
            add("boundary", where, f"a boundary of kind {b.kind!r} must be closed")
        if len(b.vertices) < (3 if b.closed else 2):
            add("boundary", where, "too few vertices: three for a closed boundary, two "
                                   "for an open one")
            continue
        if len(set(b.vertices)) != len(b.vertices):
            add("boundary", where, "a vertex is repeated (a boundary is closed with "
                                   "closed=True, not by repeating its first vertex)")
        indices = set()
        for s in b.segments:
            w = f"{where}, segment {s.index}"
            if not (_int(s.index) and 0 <= s.index < b.n_segments):
                add("segment_attr", w, f"there is no segment {s.index!r}")
                continue
            if s.index in indices:
                add("segment_attr", w, "has its attributes given twice")
            indices.add(s.index)
            if s.arc is not None and not _point(s.arc):
                add("segment_attr", w, f"the arc's centre {s.arc!r} is not two finite numbers")
            if s.divisions is not None and not (_int(s.divisions) and s.divisions >= 1):
                add("segment_attr", w, f"divisions {s.divisions!r} is not an integer >= 1")
            if s.arc is None and s.divisions is None:
                add("segment_attr", w, "has no attribute: an entry that does nothing (rule 7)")
        if m.analysis == AXISYMMETRIC:
            for v in b.vertices:
                if v[0] < 0.0:
                    add("left_of_axis", where,
                        f"vertex {v} has x = r < 0: in axisymmetry the model lies on x >= 0")
                    break
    if len(externals) != 1:
        add("external", "model",
            f"{len(externals)} external boundaries: a model has exactly one")


def _material_problems(m: Model, add) -> None:
    seen: set[str] = set()
    for mat in m.materials:
        where = f"material {mat.id!r}" + (f" ({mat.name})" if mat.name else "")
        if not isinstance(mat.id, str) or not mat.id:
            add("material_id", where, "a material needs an id (a non-empty string)")
        elif mat.id in seen:
            add("material_id", where, "the id is repeated")
        seen.add(mat.id)
        if mat.E is not None and not (_finite(mat.E) and mat.E > 0.0):
            add("material", where, f"E = {mat.E!r} is not > 0")
        if mat.nu is not None and not (_finite(mat.nu) and -1.0 < mat.nu < 0.5):
            add("material", where, f"nu = {mat.nu!r} is not in (-1, 0.5)")
        if not (_finite(mat.unit_weight) and mat.unit_weight >= 0.0):
            add("material", where, f"unit weight {mat.unit_weight!r} is not >= 0")
        if mat.initial_loading not in INITIAL_LOADINGS:
            add("material", where, f"initial loading {mat.initial_loading!r} is not one "
                                   f"of {INITIAL_LOADINGS}")


def _stage_problems(m: Model, add) -> None:
    if not m.stages:
        add("stage", "model", "no stages: a model has at least one")
    seen: set[str] = set()
    for k, s in enumerate(m.stages):
        if not isinstance(s.id, str) or not s.id:
            add("stage", f"stage {k}", "a stage needs an id (a non-empty string)")
        elif s.id in seen:
            add("stage", f"stage {k} ({s.id!r})", "the id is repeated")
        seen.add(s.id)


def _per_stage(values, n, kind) -> bool:
    return isinstance(values, tuple) and len(values) == n and all(kind(v) for v in values)


def _assignment_problems(m: Model, add) -> None:
    n = len(m.stages)
    ids = {mat.id for mat in m.materials}
    for a in m.assignments:
        where = f"assignment at {a.point}"
        if not _point(a.point):
            add("assignment", where, "the point is not two finite numbers")
        if a.material not in ids:
            add("assignment", where, f"material {a.material!r} does not exist")
        if not _per_stage(a.excavated, n, lambda v: isinstance(v, bool)):
            add("assignment", where, f"needs one excavated flag per stage ({n})")
            continue
        for k in range(1, n):
            if a.excavated[k - 1] and not a.excavated[k]:
                add("reactivated", where,
                    f"excavated in stage {m.stages[k - 1].id!r} and back in "
                    f"{m.stages[k].id!r}: the engine admits no element coming back "
                    "(spec 002; RF-4, until spec 012)")
                break


def _field_problems(m: Model, add) -> None:
    f = m.field
    if isinstance(f, ConstantField):
        if not _finite(f.sigma_1, f.sigma_3, f.sigma_z, f.angle):
            add("field", "field stress", "the constant field needs four finite numbers")
        elif f.sigma_1 < f.sigma_3:
            add("field", "field stress",
                f"sigma_1 = {f.sigma_1} < sigma_3 = {f.sigma_3}: sigma_1 is the major one")
    elif isinstance(f, GravityField):
        if not _finite(f.surface):
            add("field", "field stress", "the surface is not a finite number")
            return
        if not f.strata:
            add("field", "field stress", "a gravitational field needs at least one stratum")
        top = f.surface
        for i, s in enumerate(f.strata):
            if not _finite(s.bottom, s.unit_weight, s.k, s.kz):
                add("field", f"stratum {i}", "needs four finite numbers")
                return
            if not s.bottom < top:
                add("field", f"stratum {i}", f"its bottom {s.bottom} is not below its top {top}")
            if min(s.unit_weight, s.k, s.kz) < 0.0:
                add("field", f"stratum {i}", "unit weight, K and Kz must be >= 0")
            top = s.bottom
    else:
        add("field", "field stress", f"{type(f).__name__} is not a field stress")


def _where_span(m: Model, span, add, rule, where) -> None:
    if not isinstance(span, Span):
        add(rule, where, "needs a span")
        return
    b = m.boundary(span.boundary)
    if b is None:
        add(rule, where, f"boundary {span.boundary!r} does not exist")
    elif span_indices(b, span) is None:
        add(rule, where, f"{span.start} to {span.end} is not a stretch of "
                         f"{boundary_name(b)}: both must be its vertices, the start "
                         "before the end in an open one")


def _vertices(m: Model) -> set:
    return {v for b in m.boundaries for v in b.vertices}


def _condition_problems(m: Model, add) -> None:
    n = len(m.stages)
    vertices = _vertices(m)
    if m.default_restraint not in RESTRAINTS:
        add("default_restraint", "model",
            f"the default restraint {m.default_restraint!r} is not one of {RESTRAINTS}")
    for k, c in enumerate(m.conditions):
        where = f"condition {k}" + (f" ({c.name})" if c.name else "")
        if c.kind not in CONDITION_KINDS:
            add("condition", where, f"kind {c.kind!r} is not one of {CONDITION_KINDS}")
            continue
        if (c.span is None) == (c.vertex is None):
            add("condition", where, "needs a span or a vertex, one of the two")
        elif c.span is not None:
            _where_span(m, c.span, add, "condition", where)
        elif c.vertex not in vertices:
            add("condition", where, f"{c.vertex} is not a vertex of any boundary")
        if c.kind == DISPLACEMENT:
            if c.active:
                add("condition", where, "an imposed displacement has factors, not active "
                                        "flags (rule 7)")
            if c.ux is None and c.uy is None:
                add("condition", where, "imposes neither ux nor uy")
            if not all(v is None or _finite(v) for v in (c.ux, c.uy)):
                add("condition", where, "ux and uy must be finite numbers or None")
            if not _per_stage(c.factors, n, lambda v: v is None or _finite(v)):
                add("condition", where, f"needs one factor (a number or None) per stage ({n})")
        else:
            if c.factors or c.ux is not None or c.uy is not None:
                add("condition", where, "a restraint has active flags, not displacements "
                                        "or factors (rule 7)")
            if not _per_stage(c.active, n, lambda v: isinstance(v, bool)):
                add("condition", where, f"needs one active flag per stage ({n})")


def _load_problems(m: Model, add) -> None:
    n = len(m.stages)
    vertices = _vertices(m)
    for k, ld in enumerate(m.loads):
        where = f"load {k}" + (f" ({ld.name})" if getattr(ld, "name", "") else "")
        if isinstance(ld, DistributedLoad):
            _where_span(m, ld.span, add, "load", where)
            if ld.orientation not in ORIENTATIONS:
                add("load", where, f"orientation {ld.orientation!r} is not one of {ORIENTATIONS}")
            if not _finite(ld.start_value, ld.end_value, ld.angle):
                add("load", where, "the values and the angle must be finite")
            if ld.orientation not in (ANGLE_FROM_HORIZONTAL, ANGLE_TO_BOUNDARY) and ld.angle != 0.0:
                add("load", where, f"an angle with orientation {ld.orientation!r} does nothing "
                                   "(rule 7)")
        elif isinstance(ld, PointLoad):
            if ld.vertex not in vertices:
                add("load", where, f"{ld.vertex} is not a vertex of any boundary")
            if ld.orientation not in POINT_ORIENTATIONS:
                add("load", where, f"orientation {ld.orientation!r}: a point load is one of "
                                   f"{POINT_ORIENTATIONS} (a point has no boundary to be "
                                   "normal to)")
            if not _finite(ld.magnitude, ld.angle):
                add("load", where, "the magnitude and the angle must be finite")
            if ld.orientation != ANGLE_FROM_HORIZONTAL and ld.angle != 0.0:
                add("load", where, f"an angle with orientation {ld.orientation!r} does nothing "
                                   "(rule 7)")
        else:
            add("load", where, f"{type(ld).__name__} is not a load")
            continue
        if not _per_stage(ld.factors, n, _finite):
            add("load", where, f"needs one factor per stage ({n})")


def _mesh_problems(m: Model, add) -> None:
    mesh = m.mesh
    if mesh is None:
        return
    nn = len(mesh.nodes)
    if not all(_point(p) for p in mesh.nodes):
        add("mesh", "mesh", "a node is not two finite numbers")
    kinds = {len(e) for e in mesh.elements}
    if not mesh.elements or kinds - {3, 6} or len(kinds) != 1:
        add("mesh", "mesh", "the elements are not all of 3 or all of 6 nodes")
    if any(not (_int(i) and 0 <= i < nn) for e in mesh.elements for i in e):
        add("mesh", "mesh", "an element has a node that does not exist")
    if len(mesh.element_region) != len(mesh.elements):
        add("mesh", "mesh", "one region per element is needed")
    if not isinstance(mesh.source, str) or not mesh.source:
        add("mesh", "mesh", "the fingerprint of its mesher input is missing")


def problems(m: Model) -> list[Problem]:
    """Every problem of the model as a document, in the order found (empty
    when valid). The regions are checked when the rest allows it."""
    out: list[Problem] = []
    add = lambda rule, where, message: out.append(Problem(rule, where, message))
    if m.analysis not in ANALYSES:
        add("analysis", "model", f"analysis {m.analysis!r} is not one of {ANALYSES}")
    if m.units not in SYSTEMS:
        add("units", "model", f"unit system {m.units!r} is not one of {tuple(SYSTEMS)} "
                              "(D5: an unknown one is an error, not replaced)")
    _boundary_problems(m, add)
    _material_problems(m, add)
    _stage_problems(m, add)
    _assignment_problems(m, add)
    _field_problems(m, add)
    _condition_problems(m, add)
    _load_problems(m, add)
    _mesh_problems(m, add)
    if not out:
        from . import regions
        out.extend(regions.problems(m))
    return out


def validate(m: Model) -> Model:
    """The model itself when it is valid; ModelError with every problem
    otherwise."""
    found = problems(m)
    if found:
        raise ModelError(found)
    return m


def refuse_new_problems(before: Model, after: Model) -> Model:
    """``after`` when it has no problem that ``before`` did not have;
    ModelError with the new ones otherwise (spec 006, T5). An edit of a
    model being drawn (no external yet, a region without its material) is
    judged by what it breaks, not by what was not finished before it."""
    old = {(p.rule, p.where, p.message) for p in problems(before)}
    new = [p for p in problems(after) if (p.rule, p.where, p.message) not in old]
    if new:
        raise ModelError(new)
    return after
