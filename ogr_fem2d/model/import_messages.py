# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The lines of the report of a conversion (``import_slip2d``, ``import_dxf``),
each with a stable code (spec 006, decided on 2026-11-25; rule 2).

The pattern of ``api/messages.py``: a line IS its English sentence
(``ogr_core.messages.coded``), so the operations, the command line and an
agent read it as before, and it also carries its code and values, so that
the window says it in the reader's language. The operations' catalogue
(``api.messages.FEM_MESSAGES``) includes this one.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.messages import MessageSpec, as_nested, coded


def _spec(code: str, english: str, **kw) -> MessageSpec:
    return MessageSpec(code, english, **kw)


_ENTRIES = [
    # OGR Slip2D
    _spec("fem.import.load_off_external",
          "distributed load {name}: its ends are not on the external boundary"),
    _spec("fem.import.vertex_for_load",
          "a vertex inserted in the external boundary at {point}, an end of the distributed "
          "load {name}"),
    _spec("fem.import.point_off_external",
          "line load {name}: its point is not on the external boundary"),
    _spec("fem.import.vertex_for_point",
          "a vertex inserted in the external boundary at {point}, the point of the line load "
          "{name}"),
    _spec("fem.import.region_no_material", "a region with no material in Slip2D"),
    _spec("fem.import.region_inherited",
          "the region with material {material} at {point} had no assignment of its own in "
          "Slip2D (inherited, or Slip2D's first material)"),
    _spec("fem.import.normal_flipped",
          "distributed load {name}: Slip2D's normal pointed out of the ground; brought with the "
          "sign changed (D6)"),
    _spec("fem.import.angle_reversed",
          "distributed load {name}: runs the other way round the external boundary; its angle "
          "to the boundary + 180 degrees"),
    _spec("fem.import.point_at_corner",
          "line load {name}: {orientation} at a corner of the boundary, where the boundary has "
          "no one direction"),
    _spec("fem.import.point_turned",
          "line load {name}: {orientation} turned into an angle of {angle} degrees from the "
          "horizontal"),
    _spec("fem.import.default_conditions",
          "conditions: the sides and the bottom of the external boundary fixed in x and y, the "
          "surface free (as the reference program)"),
    _spec("fem.import.default_materials",
          "materials: E and nu not given; the model is not translated to the engine until they "
          "are (D16)"),
    _spec("fem.import.default_field",
          "field stress: none (constant, zero); the gravitational field under the real ground "
          "surface is spec 009"),
    _spec("fem.import.default_stage_mesh",
          "one stage; the mesh settings by default (graded, six-node triangles, B = sqrt 2), "
          "boundary_nodes to be given"),
    _spec("fem.import.brought_boundaries",
          "{count} boundaries (1 external, {materials} material)"),
    _spec("fem.import.brought_materials", "{count} materials (name, colour, unit weight)",
          one="1 material (name, colour, unit weight)", count="count"),
    _spec("fem.import.brought_regions", "{count} regions with their material",
          one="1 region with its material", count="count"),
    _spec("fem.import.brought_loads", "{count} loads", one="1 load", count="count"),
    _spec("fem.import.no_strength",
          "the strength of the materials (no law of this version uses it, spec 008) and their "
          "pore pressure settings"),
    _spec("fem.import.boundaries_of_type", "{count} boundaries of type {kind}",
          one="1 boundary of type {kind}", count="count"),
    _spec("fem.import.supports", "{count} supports", one="1 support", count="count"),
    _spec("fem.import.water",
          "the water pressure grid, the seepage mesh and its results"),
    _spec("fem.import.analysis_settings",
          "the analysis settings: methods, searches, seismic loading, statistics"),
    # DXF
    _spec("fem.import.dxf_layer",
          "layer {layer} ({count} entities): not one of the four kinds of boundary",
          one="layer {layer} (1 entity): not one of the four kinds of boundary", count="count"),
    _spec("fem.import.dxf_spline",
          "layer {layer}: {count} SPLINE came as straight pieces (the core's reader flattens "
          "them; the mid-side nodes will be on the chords)"),
    _spec("fem.import.dxf_skipped", "{count} {key}: {reason}; not read"),
    _spec("fem.import.dxf_reason.plane",
          "not in the plane of the drawing (its extrusion leans away from Z)"),
    _spec("fem.import.dxf_reason.unreadable", "could not be read (a malformed entity)"),
    _spec("fem.import.dxf_reason.degenerate", "fewer than two distinct points"),
    _spec("fem.import.dxf_reason.type", "the core's reader does not read this type"),
    _spec("fem.import.dxf_brought",
          "{count} boundaries: {kinds}; {arcs} pieces of arc",
          one="1 boundary: {kinds}; {arcs} pieces of arc", count="count"),
    _spec("fem.import.dxf_count.external", "{count} external"),
    _spec("fem.import.dxf_count.material", "{count} material"),
    _spec("fem.import.dxf_count.excavation", "{count} excavation",
          one="1 excavation", count="count"),
    _spec("fem.import.dxf_count.stage", "{count} stage"),
    # the orientations of a line load of Slip2D, as its values name them
    _spec("fem.import.orientation.normal_to_boundary", "normal to the boundary"),
    _spec("fem.import.orientation.vertical", "vertical"),
    _spec("fem.import.orientation.horizontal", "horizontal"),
    _spec("fem.import.orientation.angle_from_horizontal", "at an angle from the horizontal"),
    _spec("fem.import.orientation.angle_to_boundary", "at an angle to the boundary"),
    _spec("fem.import.dxf_defaults",
          "materials, assignments, stages, conditions and loads: none, the user's to give"),
]

IMPORT_MESSAGES = {e.code: e for e in _ENTRIES}


def say(code: str, **args):
    """The line ``code`` of :data:`IMPORT_MESSAGES` with ``args``."""
    return coded(IMPORT_MESSAGES, code, **args)


def part(code: str, **args) -> dict:
    """The line ``code`` as the value of another line's field."""
    return as_nested(say(code, **args))
