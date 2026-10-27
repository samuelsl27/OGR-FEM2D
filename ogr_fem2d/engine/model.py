# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The discrete input of the engine and its validation (spec 002, RF-1 and
RF-2; rule 11 of AGENTS.md). The schema, field by field, is documented in
docs/motor/entrada.md.

The engine receives nodes, triangles of one kind (3 or 6 nodes), a material
per element, the kind of analysis, the initial stress of every integration
point and a sequence of stages. It knows nothing of boundaries, menus or
user units: the numbers come in one coherent set of units chosen by the
caller (spec 004 converts).

Conventions (spec 001, D1 and D2):

* tension positive; a stress is (sigma_xx, sigma_yy, sigma_zz, tau_xy). In
  axisymmetry x is the radius r, y is the axis z, and sigma_zz is the hoop
  stress sigma_theta (spec 002, plan, "Convenio");
* gravity acts along -y, with the unit weight of each material;
* loads and imposed displacements of each stage are TOTALS: the state the
  stage ends at, not what it adds;
* in axisymmetry every force is that of the whole ring, 2 pi r times the
  force per unit length of circumference (spec 002, D2; Zienkiewicz and
  Taylor 2000, §5.2.6, p. 118).

validate() checks everything that can be checked before computing and
raises InputError with every problem found, each naming its stage, element
or node and the rule it breaks (``Problem.rule``, one of RULES). What can
only be found while computing (a singular stiffness, a point load outside
its element once the element map is inverted) is the solver's to report.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .reference.elastic import Elastic
from .reference.mohr_coulomb import MohrCoulomb
from .reference.quadrature import AXISYMMETRIC, PLANE_STRAIN, rule_for

ANALYSES = (PLANE_STRAIN, AXISYMMETRIC)

#: Integration points per element (spec 002, D1): the length of its rule in
#: reference/quadrature.py (Zienkiewicz and Taylor 2000, table 9.2, p. 222).
#: T3, the centroid; T6 in plane strain, the three mid-side points
#: (validated in spec 001); T6 in axisymmetry, the seven interior points, so
#: that none lies on the axis.
POINTS_PER_ELEMENT = {(n, a): len(rule_for(n, a)) for n in (3, 6) for a in ANALYSES}

#: A corner triangle whose area is below this fraction of the square of its
#: longest side is taken as degenerate (a sliver this thin is a meshing
#: error, not a shape; an equilateral triangle has 0.43).
SLIVER = 1e-10

Stress = tuple[float, float, float, float]


@dataclass(frozen=True)
class Material:
    """A material: its constitutive law and its unit weight (force per unit
    volume, along -y; 0 for no self weight)."""
    law: Elastic | MohrCoulomb
    unit_weight: float = 0.0


@dataclass(frozen=True)
class Restraint:
    """Zero displacement of a node in x, in y or in both."""
    node: int
    x: bool
    y: bool


@dataclass(frozen=True)
class ImposedDisplacement:
    """The TOTAL displacement of one degree of freedom at the end of the
    stage: component 0 is x (r), 1 is y (z)."""
    node: int
    component: int
    value: float


@dataclass(frozen=True)
class NodalLoad:
    """A TOTAL force on a node."""
    node: int
    fx: float
    fy: float


@dataclass(frozen=True)
class PointLoad:
    """A TOTAL force at a point (x, y) of an element; the engine turns it
    into the consistent nodal forces N_i(x, y) (fx, fy) (spec 002, plan,
    "Formulación")."""
    element: int
    x: float
    y: float
    fx: float
    fy: float


@dataclass(frozen=True)
class EdgeLoad:
    """A TOTAL traction along one side of an element, linear from its first
    corner to its second: side k goes from corner k to corner (k + 1) % 3
    (with T6, through the mid-side node k + 3). ``start`` and ``end`` are
    the traction (force per unit length; in axisymmetry per unit length of
    the meridian, the ring added by the engine) at the two corners, in the
    global frame (x, y) or, with ``normal=True``, as (normal, tangential):
    normal positive outward from the element, which is a pull (tension
    positive), tangential positive from the first corner to the second.
    Uniform: start == end; triangular: one of them zero."""
    element: int
    side: int
    start: tuple[float, float]
    end: tuple[float, float]
    normal: bool = False


@dataclass(frozen=True)
class Stage:
    """One stage: which elements exist, how the boundary is held, what acts
    on the model at its end (totals), and the settings of its solution,
    which change the result and go with it (rule 12)."""
    active: tuple[bool, ...]
    restraints: tuple[Restraint, ...] = ()
    imposed: tuple[ImposedDisplacement, ...] = ()
    nodal_loads: tuple[NodalLoad, ...] = ()
    point_loads: tuple[PointLoad, ...] = ()
    edge_loads: tuple[EdgeLoad, ...] = ()
    steps: int = 1
    tolerance: float = 1e-8
    max_iterations: int = 25
    max_cuts: int = 0


@dataclass(frozen=True)
class EngineModel:
    """Everything the engine receives."""
    analysis: str
    nodes: tuple[tuple[float, float], ...]
    elements: tuple[tuple[int, ...], ...]
    materials: tuple[Material, ...]
    element_material: tuple[int, ...]
    stages: tuple[Stage, ...]
    #: one per integration point, element by element in the order of the
    #: element's rule; None is zero everywhere
    initial_stresses: tuple[Stress, ...] | None = None

    @property
    def nodes_per_element(self) -> int:
        return len(self.elements[0]) if self.elements else 0

    @property
    def n_points(self) -> int:
        key = (self.nodes_per_element, self.analysis)
        return POINTS_PER_ELEMENT.get(key, 0) * len(self.elements)


# ---------------------------------------------------------------- problems
#: The rules validate() enforces, by name; docs/motor/entrada.md says why.
RULES = (
    "analysis", "nodes", "node_left_of_axis", "unused_node",
    "element_kind", "element_node", "repeated_node", "degenerate_element",
    "element_material", "material", "plasticity_not_validated",
    "initial_stresses", "no_stage", "active", "no_active_element",
    "node", "inactive_node", "restrained_and_imposed", "imposed_twice",
    "component", "load_on_axis", "imposed_on_axis", "element",
    "inactive_element", "side", "finite", "stage_settings",
)


@dataclass(frozen=True)
class Problem:
    rule: str           # one of RULES
    where: str          # "stage 2, node 14", "element 3", "model"
    message: str

    def __str__(self) -> str:
        return f"{self.where}: {self.message} [{self.rule}]"


class InputError(ValueError):
    """The input breaks the schema: every problem found, none computed."""

    def __init__(self, problems: list[Problem]):
        self.problems = problems
        super().__init__("the engine input is not valid:\n"
                         + "\n".join(f"  {p}" for p in problems))


def _finite(*values: float) -> bool:
    return all(isinstance(v, (int, float)) and math.isfinite(v) for v in values)


def _signed_area(a, b, c) -> float:
    return 0.5 * ((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))


def _model_problems(m: EngineModel) -> list[Problem]:
    out: list[Problem] = []
    add = lambda rule, where, message: out.append(Problem(rule, where, message))

    if m.analysis not in ANALYSES:
        add("analysis", "model", f"analysis {m.analysis!r} is not one of {ANALYSES}")
    if len(m.nodes) < 3:
        add("nodes", "model", "fewer than three nodes")
    for n, xy in enumerate(m.nodes):
        if len(xy) != 2 or not _finite(*xy):
            add("nodes", f"node {n}", f"coordinates {xy!r} are not two finite numbers")
        elif m.analysis == AXISYMMETRIC and xy[0] < 0.0:
            add("node_left_of_axis", f"node {n}",
                f"x = r = {xy[0]!r} < 0: in axisymmetry the axis is x = 0 and "
                "the model lies on x >= 0")

    kinds = {len(e) for e in m.elements}
    if not m.elements:
        add("element_kind", "model", "no elements")
    elif not kinds <= {3, 6} or len(kinds) > 1:
        add("element_kind", "model",
            f"elements with {sorted(kinds)} nodes: all must be triangles of 3 or "
            "all of 6 nodes (one kind per model)")
    used = set()
    n_nodes = len(m.nodes)
    for e, element in enumerate(m.elements):
        bad = [n for n in element if not (isinstance(n, int) and 0 <= n < n_nodes)]
        if bad:
            add("element_node", f"element {e}", f"nodes {bad} do not exist")
            continue
        used.update(element)
        if len(set(element)) != len(element):
            add("repeated_node", f"element {e}", f"repeats a node: {element}")
            continue
        corners = [m.nodes[n] for n in element[:3]]
        if not all(len(c) == 2 and _finite(*c) for c in corners):
            continue
        area = _signed_area(*corners)
        longest = max(math.dist(corners[i], corners[(i + 1) % 3]) for i in range(3))
        if area <= SLIVER * longest ** 2:
            add("degenerate_element", f"element {e}",
                f"corner area {area:.3e}: zero, or the corners are not "
                "anticlockwise (Zienkiewicz and Taylor 2000, §4.2.1)")
    for n in range(n_nodes):
        if n not in used and m.elements:
            add("unused_node", f"node {n}", "belongs to no element: it would have no stiffness")

    if len(m.element_material) != len(m.elements):
        add("element_material", "model",
            f"{len(m.element_material)} material indices for {len(m.elements)} elements")
    for e, k in enumerate(m.element_material):
        if not (isinstance(k, int) and 0 <= k < len(m.materials)):
            add("element_material", f"element {e}", f"material {k!r} does not exist")
    for k, mat in enumerate(m.materials):
        law = mat.law
        where = f"material {k}"
        if not isinstance(law, (Elastic, MohrCoulomb)):
            add("material", where, f"unknown law {type(law).__name__}")
            continue
        if not (_finite(law.young, law.poisson, mat.unit_weight) and law.young > 0.0
                and -1.0 < law.poisson < 0.5 and mat.unit_weight >= 0.0):
            add("material", where, "needs E > 0, -1 < nu < 0.5 and unit weight >= 0")
        if isinstance(law, MohrCoulomb):
            if not (_finite(law.cohesion, law.phi, law.psi) and law.cohesion >= 0.0
                    and 0.0 <= law.psi <= law.phi < 0.5 * math.pi):
                add("material", where,
                    "Mohr-Coulomb needs c >= 0 and 0 <= psi <= phi < 90 degrees")
            if (m.nodes_per_element, m.analysis) != (6, PLANE_STRAIN):
                add("plasticity_not_validated", where,
                    "Mohr-Coulomb is validated only with six-node triangles in plane "
                    "strain (spec 002, D6)")

    if m.initial_stresses is not None:
        if len(m.initial_stresses) != m.n_points:
            add("initial_stresses", "model",
                f"{len(m.initial_stresses)} initial stresses for {m.n_points} "
                "integration points")
        for i, s in enumerate(m.initial_stresses):
            if len(s) != 4 or not _finite(*s):
                add("initial_stresses", f"integration point {i}",
                    f"{s!r} is not four finite numbers")
    return out


def _stage_problems(m: EngineModel, i: int, s: Stage) -> list[Problem]:
    out: list[Problem] = []
    add = lambda rule, where, message: out.append(Problem(rule, f"stage {i}, {where}", message))
    n_nodes, n_elements = len(m.nodes), len(m.elements)

    if not (isinstance(s.steps, int) and s.steps >= 1 and isinstance(s.max_iterations, int)
            and s.max_iterations >= 1 and isinstance(s.max_cuts, int) and s.max_cuts >= 0
            and _finite(s.tolerance) and s.tolerance > 0.0):
        add("stage_settings", "settings",
            "needs steps >= 1, max_iterations >= 1, max_cuts >= 0 and tolerance > 0")
    if len(s.active) != n_elements:
        add("active", "elements", f"{len(s.active)} active flags for {n_elements} elements")
        return out
    if not any(s.active):
        add("no_active_element", "elements", "no element is active")
    alive = set()
    for e, element in enumerate(m.elements):
        if s.active[e]:
            alive.update(element)

    def node_ok(n: int, what: str, active: bool = True) -> bool:
        """The node exists and, if ``active``, has an active element: a
        load or an imposed displacement on a node out of the system would be
        lost. A restraint there is harmless (it holds nothing), so it only
        has to exist: the boundary of a region excavated later keeps its
        restraints."""
        if not (isinstance(n, int) and 0 <= n < n_nodes):
            add("node", f"{what} on node {n!r}", "the node does not exist")
            return False
        if active and n not in alive:
            add("inactive_node", f"{what} on node {n}",
                "the node has no active element in this stage")
            return False
        return True

    def on_axis(n: int) -> bool:
        return m.analysis == AXISYMMETRIC and m.nodes[n][0] == 0.0

    restrained = set()
    for r in s.restraints:
        if node_ok(r.node, "restraint", active=False):
            restrained.update(2 * r.node + c for c, held in ((0, r.x), (1, r.y)) if held)
    imposed = set()
    for d in s.imposed:
        if not node_ok(d.node, "imposed displacement"):
            continue
        if d.component not in (0, 1):
            add("component", f"imposed displacement on node {d.node}",
                f"component {d.component!r} is not 0 (x) or 1 (y)")
            continue
        if not _finite(d.value):
            add("finite", f"imposed displacement on node {d.node}", "value not finite")
        dof = 2 * d.node + d.component
        if dof in restrained:
            add("restrained_and_imposed", f"node {d.node}",
                f"component {d.component} is both restrained and imposed")
        if dof in imposed:
            add("imposed_twice", f"node {d.node}",
                f"component {d.component} is imposed twice")
        imposed.add(dof)
        if on_axis(d.node) and d.component == 0 and d.value != 0.0:
            add("imposed_on_axis", f"node {d.node}",
                "a radial displacement on the axis: u_r = 0 there by symmetry "
                "(spec 002, D1 bis)")
    for f in s.nodal_loads:
        if not node_ok(f.node, "nodal load"):
            continue
        if not _finite(f.fx, f.fy):
            add("finite", f"nodal load on node {f.node}", "force not finite")
        if on_axis(f.node) and f.fx != 0.0:
            add("load_on_axis", f"nodal load on node {f.node}",
                "a radial force on the axis would go into the reaction of u_r = 0 "
                "(spec 002, D1 bis)")

    def element_ok(e: int, what: str) -> bool:
        if not (isinstance(e, int) and 0 <= e < n_elements):
            add("element", f"{what} on element {e!r}", "the element does not exist")
            return False
        if not s.active[e]:
            add("inactive_element", f"{what} on element {e}",
                "the element is not active in this stage")
            return False
        return True

    for p in s.point_loads:
        if element_ok(p.element, "point load") and not _finite(p.x, p.y, p.fx, p.fy):
            add("finite", f"point load on element {p.element}", "position or force not finite")
    for q in s.edge_loads:
        if not element_ok(q.element, "edge load"):
            continue
        if q.side not in (0, 1, 2):
            add("side", f"edge load on element {q.element}",
                f"side {q.side!r} is not 0, 1 or 2")
        if not (len(q.start) == 2 and len(q.end) == 2 and _finite(*q.start, *q.end)):
            add("finite", f"edge load on element {q.element}", "traction not two finite numbers")
    return out


def problems(m: EngineModel) -> list[Problem]:
    """Every problem of the input, in the order found (empty when valid)."""
    out = _model_problems(m)
    if not m.stages:
        out.append(Problem("no_stage", "model", "no stages"))
    for i, s in enumerate(m.stages):
        out.extend(_stage_problems(m, i, s))
    return out


def validate(m: EngineModel) -> EngineModel:
    """The model itself when it is valid; InputError with every problem
    otherwise (spec 002, RF-2)."""
    found = problems(m)
    if found:
        raise InputError(found)
    return m
