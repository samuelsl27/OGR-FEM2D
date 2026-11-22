# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The mesher of OGR FEM2D (spec 003): from a geometry of material regions,
with holes and arcs, to the discrete input of the engine.

It lives outside ``ogr_fem2d.engine`` on purpose (rule 11 of AGENTS.md): the
engine knows nodes and elements, not boundaries. The quality triangulation
itself is the core's (spec 003, D2); this package decides what is meshed and
how (boundaries, arcs, sizes), and turns the result into six-node triangles
and into an ``EngineModel``.

Author: Samuel Sáez López (UPCT)
"""
