# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The conditions of the model on the nodes of the mesh, stage by stage (spec
004, RF-9, D7, D16).

For every stage:

1. **Each segment of the geometry** takes the union of the restraints of the
   span conditions that act on it in that stage; a release (``free``)
   contributes nothing but says the segment has a condition. A segment of the
   external boundary that no acting condition covers takes the default
   (``Model.default_restraint``, written in the model, rule 12).
2. **Each node** takes the union of the segments it lies on: corners and
   mid-side nodes of their chains in the mesh. So freeing a segment does not
   free the corner it shares with a restrained one (P14:82 of the interface
   analysis).
3. **A vertex condition** replaces, at its node, what the segments gave it
   (the vertex comes first, D16); several acting at one vertex join.
4. **Imposed displacements**: total = factor x value (D10); a factor None
   does not act. Those of spans go first, then those of vertices, which
   replace them at their node. Two that ask different values of the same
   degree of freedom at the same level are an error that names both. An
   imposed component replaces the restraint of that component at that node.
   An imposed displacement at a node with no active element is an error
   (the engine would lose it).

The engine's restraints come sorted by node, and its imposed displacements by
node and component.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ..engine import model as em
from . import model as md

_FLAGS = {md.X: (True, False), md.Y: (False, True), md.XY: (True, True), md.FREE: (False, False)}


def _name(m: md.Model, k: int) -> str:
    c = m.conditions[k]
    return f"condition {k}" + (f" ({c.name})" if c.name else "")


def segment_nodes(ctx, seg: int) -> list[int]:
    """The corner and mid-side nodes of a segment of the geometry."""
    bd = ctx.mesh_boundary[seg]
    return list(bd.nodes) + list(bd.mids)


def _active_nodes(ctx, active) -> set[int]:
    return {n for e, on in zip(ctx.mesh.elements, active) if on for n in e}


def stage_conditions(ctx, k: int, active) -> tuple[tuple, tuple]:
    m = ctx.model
    stage = m.stages[k]
    external = next(b.id for b in m.boundaries if b.kind == md.EXTERNAL)
    # 1. the segments
    said: dict[int, list[bool]] = {}
    for c in m.conditions:
        if c.kind == md.DISPLACEMENT or c.span is None or not c.active[k]:
            continue
        fx, fy = _FLAGS[c.kind]
        for s in ctx.segments_of_span(c.span):
            flags = said.setdefault(s, [False, False])
            flags[0], flags[1] = flags[0] or fx, flags[1] or fy
    default = _FLAGS[m.default_restraint]
    flags_of: dict[int, list[bool]] = {}
    for s, seg in enumerate(ctx.geometry.segments):
        if s in said:
            fx, fy = said[s]
        elif any(b == external for b, _k in seg.origin):
            fx, fy = default
        else:
            continue
        # 2. the nodes: the union of their segments
        for n in segment_nodes(ctx, s):
            flags = flags_of.setdefault(n, [False, False])
            flags[0], flags[1] = flags[0] or fx, flags[1] or fy
    # 3. the vertices
    at_vertex: dict[int, list[bool]] = {}
    for c in m.conditions:
        if c.kind == md.DISPLACEMENT or c.vertex is None or not c.active[k]:
            continue
        fx, fy = _FLAGS[c.kind]
        flags = at_vertex.setdefault(ctx.node_of(c.vertex), [False, False])
        flags[0], flags[1] = flags[0] or fx, flags[1] or fy
    flags_of.update(at_vertex)
    # 4. the imposed displacements
    imposed: dict[tuple[int, int], tuple[float, int]] = {}
    problems = []
    for level in ("span", "vertex"):
        here: dict[tuple[int, int], tuple[float, int]] = {}
        for i, c in enumerate(m.conditions):
            if c.kind != md.DISPLACEMENT or c.factors[k] is None:
                continue
            if (level == "span") != (c.span is not None):
                continue
            nodes = ([n for s in ctx.segments_of_span(c.span) for n in segment_nodes(ctx, s)]
                     if c.span is not None else [ctx.node_of(c.vertex)])
            for comp, value in ((0, c.ux), (1, c.uy)):
                if value is None:
                    continue
                total = c.factors[k] * value
                for n in nodes:
                    old = here.get((n, comp))
                    if old is not None and old[0] != total:
                        problems.append(em.Problem(
                            "condition_conflict",
                            f"stage {stage.id!r}, {_name(m, old[1])} and {_name(m, i)}",
                            f"ask u{'xy'[comp]} = {old[0]} and {total} at node {n} "
                            f"{ctx.mesh.nodes[n]}"))
                    here[(n, comp)] = (total, i)
        imposed.update(here)
    alive = _active_nodes(ctx, active)
    for (n, comp), (value, i) in sorted(imposed.items()):
        if n not in alive:
            problems.append(em.Problem(
                "condition_inactive", f"stage {stage.id!r}, {_name(m, i)}",
                f"imposes a displacement at node {n} {ctx.mesh.nodes[n]}, which has no active "
                "element in this stage: the engine would lose it"))
        flags = flags_of.get(n)
        if flags is not None:
            flags[comp] = False
    if problems:
        raise md.ModelError(problems)
    restraints = tuple(em.Restraint(n, fx, fy) for n, (fx, fy) in sorted(flags_of.items())
                       if fx or fy)
    displacements = tuple(em.ImposedDisplacement(n, comp, value)
                          for (n, comp), (value, _i) in sorted(imposed.items()))
    return restraints, displacements
