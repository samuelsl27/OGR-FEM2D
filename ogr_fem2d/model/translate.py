# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
From the model to the input of the mesher and of the engine (spec 004,
RF-11, RF-12, D3).

* ``to_mesh_input(m)``: the geometry of ``regions`` as a ``MeshInput`` of
  spec 003. Its "material" of every region is THE INDEX OF THE REGION: the
  mesh is of the geometry, not of the materials (D3), and the material of
  every element in every stage is put by ``to_engine``. The order is the
  canonical one of ``regions``; the segment attributes (arc, divisions,
  excavation) follow the order of the segments. The same model gives the
  same input, bit for bit.
* ``mesh(m)``: the model with its mesh (``mesher.mesh`` of that input) and
  the fingerprint of the input it came from (``source``).
* ``to_engine(m)``: the ``EngineModel``: the stored mesh, one engine
  material per material of the model (in its order), the material of every
  element from its region's assignment, the stages (``conditions``,
  ``loads``), the initial stresses and self weights (``field``). The solver
  settings of every stage are the engine's defaults (D9: in elasticity they
  do not move the number). It refuses:

  - a model without a mesh, or with the mesh of another model (its
    ``source`` is not the fingerprint of the mesher input of the model
    now; RF-11). Changing a material, a stage, a condition or a load does
    not make the mesh another model's;
  - a material without E or nu (D16).

Errors name the objects of the model (RF-12): the problems of the mesher
(points, segments, regions by their indices) and of the engine (elements,
nodes, materials and stages by theirs) are written again with the boundary,
the vertex, the region, the material or the stage they come from, the
original kept after it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace

from ..engine import model as em
from ..engine.reference.elastic import Elastic
from ..mesh import geometry as g
from ..mesh import mesher
from . import conditions, field, fingerprint, loads
from . import model as md
from . import regions


@dataclass(frozen=True)
class Context:
    """The model with its geometry and its mesh, and the maps between them
    that conditions and loads need."""
    model: md.Model
    geometry: regions.Geometry
    mesh: md.StoredMesh
    #: (boundary id, segment index) -> index of the segment in the geometry
    segment_of: dict
    #: index of the segment in the geometry -> its mesh boundary
    mesh_boundary: tuple

    def segments_of_span(self, span: md.Span) -> list[int]:
        b = self.model.boundary(span.boundary)
        return [self.segment_of[(b.id, k)] for k in md.span_indices(b, span)]

    def node_of(self, vertex) -> int:
        """The node of a vertex: the point i of the mesher input is node i."""
        return self.geometry.points.index((float(vertex[0]), float(vertex[1])))

    def active_elements(self, k: int) -> tuple[bool, ...]:
        excavated = [self.model.assignments[r.assignment].excavated[k]
                     for r in self.geometry.regions]
        return tuple(not excavated[r] for r in self.mesh.element_region)


# ------------------------------------------------------------- the mesher
def to_mesh_input(m: md.Model) -> g.MeshInput:
    geo = regions.build(m)
    rs = tuple(g.Region(r.outline, r.holes, material=k) for k, r in enumerate(geo.regions))
    specs = tuple(g.SegmentSpec(s.a, s.b, arc=g.Arc(s.arc) if s.arc is not None else None,
                                divisions=s.divisions, excavation=s.excavation)
                  for s in geo.segments
                  if s.arc is not None or s.divisions is not None or s.excavation)
    return g.MeshInput(m.analysis, geo.points, rs, specs, m.mesh_settings)


def source_of(m: md.Model) -> str:
    """The fingerprint of the mesher input of ``m`` (D3)."""
    return fingerprint.digest(to_mesh_input(m))


def _json_normal(value):
    """A value as it comes back from the file (lists, not tuples)."""
    return json.loads(json.dumps(value))


def mesh(m: md.Model) -> md.Model:
    """``m`` with the mesh of its geometry and mesh settings."""
    mi = to_mesh_input(m)
    geo = regions.build(m)
    try:
        out = mesher.mesh(mi)
    except g.MeshInputError as err:
        raise md.ModelError([_name_mesh_problem(p, geo) for p in err.problems]) from None
    stored = md.StoredMesh(tuple(out.nodes), tuple(tuple(e) for e in out.elements),
                           tuple(out.element_region), tuple(out.boundaries),
                           _json_normal(dict(out.notes)), tuple(out.warnings),
                           fingerprint.digest(mi))
    return replace(m, mesh=stored)


def context(m: md.Model) -> Context:
    md.validate(m)
    if m.mesh is None:
        raise md.ModelError([em.Problem("mesh", "model", "the model has no mesh")])
    if m.mesh.source != source_of(m):
        raise md.ModelError([em.Problem(
            "mesh_stale", "mesh",
            "the mesh is of another model: the geometry or the mesh settings changed after "
            "meshing (RF-11); mesh again")])
    geo = regions.build(m)
    segment_of = {origin: k for k, s in enumerate(geo.segments) for origin in s.origin}
    bnd = tuple(m.mesh.boundary(s.a, s.b) for s in geo.segments)
    return Context(m, geo, m.mesh, segment_of, bnd)


# -------------------------------------------------------------- the engine
def _materials(m: md.Model) -> tuple[em.Material, ...]:
    missing = [mat for mat in m.materials if mat.E is None or mat.nu is None]
    if missing:
        raise md.ModelError([em.Problem(
            "material_incomplete", f"material {mat.id!r}" + (f" ({mat.name})" if mat.name else ""),
            "has no E or no nu: the engine needs both (D16: they are not invented)")
            for mat in missing])
    return tuple(em.Material(Elastic(mat.E, mat.nu), field.unit_weight(mat)) for mat in m.materials)


def to_engine(m: md.Model) -> em.EngineModel:
    ctx = context(m)
    materials = _materials(m)
    index = {mat.id: k for k, mat in enumerate(m.materials)}
    region_material = [index[m.assignments[r.assignment].material] for r in ctx.geometry.regions]
    element_material = tuple(region_material[r] for r in ctx.mesh.element_region)
    stages = []
    for k in range(len(m.stages)):
        active = ctx.active_elements(k)
        restraints, imposed = conditions.stage_conditions(ctx, k, active)
        edge, nodal = loads.stage_loads(ctx, k, active)
        stages.append(em.Stage(active=active, restraints=restraints, imposed=imposed,
                               nodal_loads=nodal, edge_loads=edge))
    base = em.EngineModel(m.analysis, ctx.mesh.nodes, ctx.mesh.elements, materials,
                          element_material, tuple(stages))
    stresses = field.initial_stresses(m, base)
    engine = replace(base, initial_stresses=stresses)
    try:
        return em.validate(engine)
    except em.InputError as err:
        raise md.ModelError([_name_engine_problem(p, ctx) for p in err.problems]) from None


# -------------------------------------------------- errors with model names
def _name_point(n: int, geo: regions.Geometry) -> str:
    p = geo.points[n]
    holders = [b for s in geo.segments if n in (s.a, s.b) for b, _k in s.origin]
    seen = list(dict.fromkeys(holders))
    return f"vertex {p}" + (f" of boundary {', '.join(repr(b) for b in seen)}" if seen else "")


def _name_mesh_problem(p: em.Problem, geo: regions.Geometry) -> em.Problem:
    where = p.where

    def segment(match):
        i, j = int(match.group(1)), int(match.group(2))
        try:
            return regions._seg_name(geo.segments[geo.segment_index(i, j)])
        except KeyError:
            return match.group(0)

    def point(match):
        return _name_point(int(match.group(1)), geo)

    def region(match):
        r = int(match.group(1))
        return f"the region of the assignment {r} " if r < len(geo.regions) else match.group(0)

    named = re.sub(r"segments? (\d+)-(\d+)", segment, where)
    named = re.sub(r"and (\d+)-(\d+)", lambda mt: "and " + segment(mt), named)
    named = re.sub(r"point (\d+)", point, named)
    named = re.sub(r"region (\d+)", region, named)
    return em.Problem(p.rule, f"{named} [mesher: {where}]", p.message)


def _name_engine_problem(p: em.Problem, ctx: Context) -> em.Problem:
    m, geo = ctx.model, ctx.geometry
    where = p.where

    def stage(match):
        k = int(match.group(1))
        s = m.stages[k] if k < len(m.stages) else None
        return f"stage {s.id!r}" + (f" ({s.name})" if s and s.name else "") if s else match.group(0)

    def element(match):
        e = int(match.group(1))
        if e >= len(ctx.mesh.element_region):
            return match.group(0)
        a = m.assignments[geo.regions[ctx.mesh.element_region[e]].assignment]
        return f"element {e} (region of the assignment at {a.point})"

    def node(match):
        n = int(match.group(1))
        if n < len(geo.points):
            return f"node {n} ({_name_point(n, geo)})"
        return f"node {n} at {ctx.mesh.nodes[n]}" if n < len(ctx.mesh.nodes) else match.group(0)

    def material(match):
        k = int(match.group(1))
        return f"material {m.materials[k].id!r}" if k < len(m.materials) else match.group(0)

    named = re.sub(r"stage (\d+)", stage, where)
    named = re.sub(r"element (\d+)", element, named)
    named = re.sub(r"node (\d+)", node, named)
    named = re.sub(r"material (\d+)", material, named)
    return em.Problem(p.rule, f"{named} [engine: {where}]", p.message)


def mesh_problem_named(p: em.Problem, m: md.Model) -> em.Problem:
    """A problem of the mesher with the names of the model (RF-12)."""
    return _name_mesh_problem(p, regions.build(m))


# ----------------------------------------- what decides the result (rule 12)
def deciding_values(m: md.Model) -> list[tuple[str, object, str]]:
    """Every value that decides the result of the model and was not drawn
    (rule 12): the defaults written in the model, the settings of the mesh,
    and the solver settings the translation takes from the engine (D9), as
    (what, value, why). The results of spec 005 carry it. ``what`` and
    ``why`` are coded (``report_messages``, spec 006 T33): they are the same
    English text, and the window says them in the reader's language."""
    from .report_messages import say
    st = m.mesh_settings
    stage = em.Stage(active=())
    out = [
        (say("fem.deciding.units"), say("fem.deciding.units.value"),
         say("fem.deciding.units.why", units=repr(m.units))),
        (say("fem.deciding.analysis"), m.analysis, say("fem.deciding.analysis.why")),
        (say("fem.deciding.default_restraint"), m.default_restraint,
         say("fem.deciding.default_restraint.why")),
    ]
    for mat in m.materials:
        out.append((say("fem.deciding.initial_loading", material=repr(mat.id)),
                    mat.initial_loading, say("fem.deciding.initial_loading.why")))
    spec003, graded, uniform = (say("fem.deciding.spec003"), say("fem.deciding.graded"),
                                say("fem.deciding.uniform"))
    default = say("fem.deciding.engine_default")
    out += [
        (say("fem.deciding.mesh_kind"), st.kind, spec003),
        (say("fem.deciding.mesh_nodes_per_element"), st.nodes_per_element, spec003),
        (say("fem.deciding.mesh_quality_bound"), st.quality_bound,
         say("fem.deciding.quality_bound.why")),
        (say("fem.deciding.mesh_boundary_nodes"), st.boundary_nodes,
         say("fem.deciding.boundary_nodes.why")),
        (say("fem.deciding.mesh_max_size"), st.max_size, graded),
        (say("fem.deciding.mesh_size"), st.size, uniform),
        (say("fem.deciding.mesh_elements"), st.elements, uniform),
        (say("fem.deciding.mesh_windows"), len(st.windows), say("fem.deciding.windows.why")),
        (say("fem.deciding.solver_steps"), stage.steps, say("fem.deciding.solver_steps.why")),
        (say("fem.deciding.solver_tolerance"), stage.tolerance, default),
        (say("fem.deciding.solver_max_iterations"), stage.max_iterations, default),
        (say("fem.deciding.solver_max_cuts"), stage.max_cuts, default),
    ]
    if m.analysis == md.AXISYMMETRIC and any(isinstance(ld, md.PointLoad) for ld in m.loads):
        out.append((say("fem.deciding.point_loads"), say("fem.deciding.point_loads.value"),
                    say("fem.deciding.point_loads.why")))
    return out
