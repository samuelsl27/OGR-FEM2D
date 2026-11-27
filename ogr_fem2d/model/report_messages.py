# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The lines of the report of a model and of its results (``report/info.py``)
and of what decides the result (``translate.deciding_values``), each with a
stable code (spec 006, T33; rule 2).

The pattern of ``import_messages.py`` (decided on 2026-11-25 for the
report of a conversion): a line IS its English sentence
(``ogr_core.messages.coded``), so the text and the HTML of the report, the
command line, an agent and the ``.h5`` (which keeps what decides the
result as text) read exactly what they read before; it also carries its
code and values, so that the window says it in the reader's language.
What the user wrote (a title, a name, an id) and the numbers are values,
never translated.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.messages import MessageSpec, as_nested, coded


def _spec(code: str, english: str, **kw) -> MessageSpec:
    return MessageSpec(code, english, **kw)


_WORDS = {
    # yes and no, the state of a boundary, where an extreme is
    "yes": "yes", "no": "no", "closed": "closed", "open": "open",
    "points": "points", "nodes": "nodes",
    "solved": "solved", "not_solved": "not solved (it changes nothing)",
    # the kinds of analysis and of boundary, the restraints, the mesh kinds
    "plane_strain": "plane_strain", "axisymmetric": "axisymmetric",
    "external": "external", "excavation": "excavation", "material": "material",
    "stage": "stage", "graded": "graded", "uniform": "uniform",
    # the states of the results
    "valid": "valid", "stale": "stale", "incomplete": "incomplete",
    "cancelled": "cancelled", "missing": "missing", "damaged": "damaged",
    "not_opened": "not opened", "none": "none",
}

_ENTRIES = [_spec(f"fem.report.word.{k}", v) for k, v in _WORDS.items()] + [
    # the sections
    _spec("fem.report.title.summary", "Project summary"),
    _spec("fem.report.title.analysis", "Analysis"),
    _spec("fem.report.title.field", "Field stress"),
    _spec("fem.report.title.boundaries", "Boundaries"),
    _spec("fem.report.title.materials", "Materials and assignments"),
    _spec("fem.report.title.conditions", "Conditions and loads"),
    _spec("fem.report.title.mesh", "Mesh"),
    _spec("fem.report.title.deciding", "What decides the result (rule 12)"),
    _spec("fem.report.title.results", "Results"),
    # the summary and the analysis
    _spec("fem.report.title_", "Title"),
    _spec("fem.report.author", "Author"),
    _spec("fem.report.date", "Date"),
    _spec("fem.report.notes", "Notes"),
    _spec("fem.report.analysis", "Analysis"),
    _spec("fem.report.units_shown", "Units shown"),
    _spec("fem.report.units_kept", "Units kept"),
    _spec("fem.report.units_kept.value",
          "m, kN, kPa, kN/m3 (the values do not change with the units shown)"),
    _spec("fem.report.stages", "Stages"),
    _spec("fem.report.stage_n", "Stage {n}"),
    # the field stress
    _spec("fem.report.field", "Field stress"),
    _spec("fem.report.field.constant", "constant (compression positive)"),
    _spec("fem.report.field.gravity", "gravitational, horizontal strata (compression positive)"),
    _spec("fem.report.angle_sigma1", "Angle of sigma_1 from x"),
    _spec("fem.report.degrees", "{value} deg"),
    _spec("fem.report.surface", "Surface"),
    _spec("fem.report.stratum", "Stratum {n}"),
    _spec("fem.report.stratum.value", "down to {bottom}, unit weight {gamma}, K {k}, Kz {kz}"),
    # the boundaries
    _spec("fem.report.boundary",
          "{kind}, {closed}, {vertices} vertices, {arcs} arcs"),
    _spec("fem.report.boundary.divided",
          "{kind}, {closed}, {vertices} vertices, {arcs} arcs, divisions {divisions}"),
    _spec("fem.report.boundary.vertices", "{boundary}: vertices"),
    # the materials and the assignments
    _spec("fem.report.materials", "Materials"),
    _spec("fem.report.material.value",
          "E {E}, nu {nu}, unit weight {gamma}, initial loading {loading}"),
    _spec("fem.report.region_at", "Region at {point}"),
    _spec("fem.report.region.value", "{material}; excavated: {stages}"),
    _spec("fem.report.by_stage", "{stage}: {value}"),
    # the conditions and the loads
    _spec("fem.report.default_external", "Default of the external boundary"),
    _spec("fem.report.condition", "Condition {n}"),
    _spec("fem.report.condition_named", "Condition {n} ({name})"),
    _spec("fem.report.load", "Load {n}"),
    _spec("fem.report.load_named", "Load {n} ({name})"),
    _spec("fem.report.at_vertex", "vertex {point}"),
    _spec("fem.report.all_of", "all of {boundary}"),
    _spec("fem.report.from_to", "{boundary} from {start} to {end}"),
    _spec("fem.report.imposed", "{where}: imposed ux {ux}, uy {uy}; factors: {factors}"),
    _spec("fem.report.restraint", "{where}: {kind}; active: {active}"),
    _spec("fem.report.distributed",
          "{where}: distributed {orientation}, from {start} to {end}; factors: {factors}"),
    _spec("fem.report.distributed_angle",
          "{where}: distributed {orientation}, from {start} to {end}, angle {angle} deg; "
          "factors: {factors}"),
    _spec("fem.report.point_load",
          "{where}: point {orientation}, {force} (per metre out of plane); factors: {factors}"),
    _spec("fem.report.point_load_angle",
          "{where}: point {orientation}, {force} (per metre out of plane), angle {angle} deg; "
          "factors: {factors}"),
    # the mesh
    _spec("fem.report.mesh", "Mesh"),
    _spec("fem.report.mesh.none", "none: Mesh > Mesh"),
    _spec("fem.report.state", "State"),
    _spec("fem.report.mesh.stale",
          "of another geometry or other settings: mesh again before calculating"),
    _spec("fem.report.kind", "Kind"),
    _spec("fem.report.nodes_per_element", "Nodes per element"),
    _spec("fem.report.nodes", "Nodes"),
    _spec("fem.report.elements", "Elements"),
    _spec("fem.report.bound_b", "Bound B"),
    _spec("fem.report.bound_b.value", "{b}, guarantees angles above {angle} deg"),
    _spec("fem.report.smallest_angle", "Smallest angle"),
    _spec("fem.report.largest_angle", "Largest angle"),
    _spec("fem.report.boundary_nodes",
          "Nodes on the excavations (or on the external, without any)"),
    _spec("fem.report.added_on", "Added on {segment}"),
    _spec("fem.report.arcs", "Arcs"),
    _spec("fem.report.axis_nodes", "Nodes on the axis"),
    _spec("fem.report.axis_nodes.value",
          "{n}: u_r = 0 there, set by the engine (spec 002, D1 bis)"),
    _spec("fem.report.warning", "Warning"),
    # what decides the result
    _spec("fem.report.deciding.value", "{value} ({why})"),
    # the results
    _spec("fem.report.state.value", "{state}"),
    _spec("fem.report.state.said", "{state}: {message}"),
    _spec("fem.report.written_by", "Written by"),
    _spec("fem.report.engine", "Engine"),
    _spec("fem.report.kept_as", "Kept as"),
    _spec("fem.report.stage", "Stage {stage}"),
    _spec("fem.report.stage_named", "Stage {stage} ({name})"),
    _spec("fem.report.stage.value", "{solved}; greatest displacement {u} at node {node}"),
    _spec("fem.report.extreme", "{stage}: {quantity} at the {at}"),
    _spec("fem.report.extreme.value", "max {max} at {max_at}, min {min} at {min_at}"),
    _spec("fem.report.reactions", "{stage}: reactions"),
    _spec("fem.report.reactions.value", "({rx}, {ry}) per metre out of plane"),
    _spec("fem.report.reactions_on", "{stage}: reactions on {boundary}"),
    _spec("fem.report.message.no_results", "no results: calculate the model"),
    _spec("fem.report.message.changed", "the model changed after the calculation"),
    # what decides the result (translate.deciding_values): what, and why
    _spec("fem.deciding.units", "units"),
    _spec("fem.deciding.units.value", "m, kN, kPa, kN/m3"),
    _spec("fem.deciding.units.why",
          "the model stores and the engine receives kPa (D5); {units} is only what is shown"),
    _spec("fem.deciding.analysis", "analysis"),
    _spec("fem.deciding.analysis.why", "plane strain or axisymmetry"),
    _spec("fem.deciding.default_restraint", "default_restraint"),
    _spec("fem.deciding.default_restraint.why",
          "the external boundary where no condition says otherwise (D16)"),
    _spec("fem.deciding.initial_loading", "material {material}: initial_loading"),
    _spec("fem.deciding.initial_loading.why", "what its elements start with (D11)"),
    _spec("fem.deciding.mesh_kind", "mesh: kind"),
    _spec("fem.deciding.mesh_nodes_per_element", "mesh: nodes_per_element"),
    _spec("fem.deciding.mesh_quality_bound", "mesh: quality_bound"),
    _spec("fem.deciding.mesh_boundary_nodes", "mesh: boundary_nodes"),
    _spec("fem.deciding.mesh_max_size", "mesh: max_size"),
    _spec("fem.deciding.mesh_size", "mesh: size"),
    _spec("fem.deciding.mesh_elements", "mesh: elements"),
    _spec("fem.deciding.mesh_windows", "mesh: windows"),
    _spec("fem.deciding.spec003", "spec 003"),
    _spec("fem.deciding.quality_bound.why",
          "B; with sqrt 2 no angle below 20.7 degrees (Shewchuk 2002a)"),
    _spec("fem.deciding.boundary_nodes.why", "graded mesh (spec 003, D5)"),
    _spec("fem.deciding.graded", "graded mesh"),
    _spec("fem.deciding.uniform", "uniform mesh"),
    _spec("fem.deciding.windows.why", "size bounds (spec 003, D9)"),
    _spec("fem.deciding.solver_steps", "solver: steps"),
    _spec("fem.deciding.solver_steps.why",
          "the engine's default (D9: in elasticity it does not move the number)"),
    _spec("fem.deciding.solver_tolerance", "solver: tolerance"),
    _spec("fem.deciding.solver_max_iterations", "solver: max_iterations"),
    _spec("fem.deciding.solver_max_cuts", "solver: max_cuts"),
    _spec("fem.deciding.engine_default", "the engine's default (D9)"),
    _spec("fem.deciding.point_loads", "point loads"),
    _spec("fem.deciding.point_loads.value", "the force of the whole ring"),
    _spec("fem.deciding.point_loads.why",
          "the engine's convention in axisymmetry (spec 002, D2)"),
]

REPORT_MESSAGES = {s.code: s for s in _ENTRIES}


def say(code: str, **args):
    """The line ``code`` of :data:`REPORT_MESSAGES` with ``args``."""
    return coded(REPORT_MESSAGES, code, **args)


def part(code: str, **args) -> dict:
    """The line ``code`` as the value of another line's field."""
    return as_nested(say(code, **args))


def word(key: str):
    """A word of the report (yes, closed, solved...), or the key itself
    when it is not one (an id the user gave)."""
    code = f"fem.report.word.{key}"
    return part(code) if code in REPORT_MESSAGES else key
