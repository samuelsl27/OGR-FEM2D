# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Small models of spec 004 the tests share (not a test file: the runner only
collects test_*.py).

* ``tunnel``: a square of side 2L with a circular excavation of radius 1 in
  four arcs (the geometry of case 005 at another size), the rock and the
  hole of one material, the hole excavated in the first stage;
* ``layers``: a rectangle of two horizontal strata split by an open
  material boundary, for gravity, conditions and loads;
* ``strip``: the half of a half-space with a strip of width B on its
  surface, a vertex at x = B.

Every model is valid as a document; ``meshed`` adds its mesh.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import replace

from ogr_fem2d.engine.initial_stress import Stratum
from ogr_fem2d.mesh import geometry as g
from ogr_fem2d.model import model as md
from ogr_fem2d.model import translate

B = md.Boundary


def tunnel(half: float = 10.0, stages: int = 1, h: float | None = None) -> md.Model:
    windows = () if h is None else (g.Window(((-3.0, -3.0), (3.0, -3.0), (3.0, 3.0), (-3.0, 3.0)), h),)
    st = tuple(md.Stage(str(k + 1), f"Stage {k + 1}") for k in range(stages))
    return md.Model(
        boundaries=(B("ext", md.EXTERNAL, ((-half, -half), (half, -half), (half, half), (-half, half)),
                      True, name="Exterior"),
                    B("hole", md.EXCAVATION, ((1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)), True,
                      tuple(md.SegmentAttr(k, (0.0, 0.0)) for k in range(4)), name="Hueco")),
        materials=(md.Material("rock", "Roca", 1.0e7, 0.2),),
        stages=st,
        assignments=(md.Assignment((0.5 * half, 0.0), "rock", (False,) * stages),
                     md.Assignment((0.0, 0.0), "rock", (True,) * stages)),
        field=md.ConstantField(30000.0, 30000.0, 30000.0, 0.0),
        mesh_settings=g.MeshSettings(boundary_nodes=36, windows=windows))


def layers(width: float = 20.0, depth: float = 10.0, contact: float = -4.0,
           loading: str = md.FIELD_AND_BODY) -> md.Model:
    """0 <= x <= width, -depth <= y <= 0, a contact at y = contact."""
    ext = B("ext", md.EXTERNAL, ((0.0, -depth), (width, -depth), (width, contact), (width, 0.0),
                                 (0.0, 0.0), (0.0, contact)), True, name="Exterior")
    mat = B("contact", md.MATERIAL, ((0.0, contact), (width, contact)), False, name="Contacto")
    return md.Model(
        boundaries=(ext, mat),
        materials=(md.Material("top", "Arcilla", 3.0e4, 0.3, 18.0, loading),
                   md.Material("bottom", "Roca", 2.0e6, 0.25, 24.0, loading)),
        assignments=(md.Assignment((0.5 * width, 0.5 * contact), "top", (False,)),
                     md.Assignment((0.5 * width, 0.5 * (contact - depth)), "bottom", (False,))),
        field=md.GravityField(0.0, (Stratum(contact, 18.0, 0.6, 0.6),
                                    Stratum(-depth - 1.0, 24.0, 0.5, 0.5))),
        conditions=(md.Condition(md.FREE, md.Span("ext", (width, 0.0), (0.0, 0.0)),
                                 active=(True,), name="Superficie"),
                    md.Condition(md.X, md.Span("ext", (width, -depth), (width, 0.0)),
                                 active=(True,), name="Derecha"),
                    md.Condition(md.X, md.Span("ext", (0.0, 0.0), (0.0, -depth)),
                                 active=(True,), name="Izquierda")),
        mesh_settings=g.MeshSettings(boundary_nodes=60, nodes_per_element=6))


def strip(width: float = 20.0, depth: float = 20.0, b: float = 1.0, q: float = 100.0) -> md.Model:
    ext = B("ext", md.EXTERNAL, ((0.0, -depth), (width, -depth), (width, 0.0), (b, 0.0), (0.0, 0.0)),
            True, name="Exterior")
    return md.Model(
        boundaries=(ext,),
        materials=(md.Material("soil", "Suelo", 2.0e4, 0.2),),
        assignments=(md.Assignment((0.5 * width, -0.5 * depth), "soil", (False,)),),
        conditions=(md.Condition(md.FREE, md.Span("ext", (width, 0.0), (0.0, 0.0)), active=(True,)),
                    md.Condition(md.X, md.Span("ext", (width, -depth), (width, 0.0)), active=(True,)),
                    md.Condition(md.X, md.Span("ext", (0.0, 0.0), (0.0, -depth)), active=(True,))),
        loads=(md.DistributedLoad(md.Span("ext", (b, 0.0), (0.0, 0.0)), q, q, factors=(1.0,),
                                  name="Faja"),),
        mesh_settings=g.MeshSettings(boundary_nodes=40))


def meshed(m: md.Model) -> md.Model:
    return translate.mesh(m)


def with_stages(m: md.Model, n: int) -> md.Model:
    """``m`` with n stages, every per-stage value repeated."""
    from ogr_fem2d.model import stages
    for k in range(1, n):
        m = stages.insert_stage(m, len(m.stages), str(k + 1), f"Stage {k + 1}")
    return m


__all__ = ["tunnel", "layers", "strip", "meshed", "with_stages", "replace"]
