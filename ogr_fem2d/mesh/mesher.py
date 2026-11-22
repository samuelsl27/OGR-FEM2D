# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The output of the mesher and its translation into the input of the engine
(spec 003, RF-15; docs/malla/entrada.md, "La salida").

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

from ..engine import model as em
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
