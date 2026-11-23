# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The FEM model of OGR FEM2D (spec 004): what the engineer defines, kept in a
``.ogrfem2d`` file (ADR-0004), and its deterministic translation into the
input of the mesher and of the engine.

It lives outside ``ogr_fem2d.engine`` and ``ogr_fem2d.mesh`` on purpose
(rule 11 of AGENTS.md): the engine knows nodes and elements, the mesher
regions and segments; the model knows boundaries, materials, stages, the
field stress, conditions and loads on the geometry. No Qt here: the model is
used from scripts, tests, the command line and the MCP server.

Author: Samuel Sáez López (UPCT)
"""
