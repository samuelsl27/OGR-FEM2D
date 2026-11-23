# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.9 (spec 004, T10) — the fingerprints of a model (RF-16, D12;
ADR-0003).

Invariants protected:

* **the model's fingerprint changes with everything that changes the
  result** (a table of mutations, one per datum: geometry, arcs, divisions,
  kind of boundary, kind of analysis, materials, initial loading,
  assignments and excavation, stages, the field, the default restraint,
  conditions, loads, mesh settings and the mesh itself);
* **and with nothing else**: the summary, the unit system shown, the names
  and colours, the notes and warnings of the mesh, who wrote the file, and
  the ids (renamed everywhere: a boundary, a material and a stage are known
  by their place);
* **the document's fingerprint changes with all of it**, but who wrote it;
* **a fingerprint survives the file**: the model read back has the same two;
* **the canonical text**: keys sorted, fixed separators, ASCII, no NaN, and
  a tuple is a list (the same mesher input, the same digest).
"""
from __future__ import annotations

from dataclasses import replace

import _models
from ogr_fem2d.engine.initial_stress import Stratum
from ogr_fem2d.mesh import geometry as g
from ogr_fem2d.model import fingerprint as fp
from ogr_fem2d.model import model as md
from ogr_fem2d.model import ogr_file, translate

BASE = translate.mesh(_models.with_stages(_models.layers(), 2))


def _b(m, k, **change):
    bs = list(m.boundaries)
    bs[k] = replace(bs[k], **change)
    return replace(m, boundaries=tuple(bs))


def _mat(m, **change):
    return replace(m, materials=(replace(m.materials[0], **change),) + m.materials[1:])


def _renamed(m):
    """The ids of the boundaries, the materials and the stages, renamed
    everywhere they are used."""
    bid = {"ext": "outer", "contact": "c"}
    mid = {"top": "clay", "bottom": "rock"}
    span = lambda s: None if s is None else replace(s, boundary=bid[s.boundary])
    return replace(
        m, boundaries=tuple(replace(b, id=bid[b.id]) for b in m.boundaries),
        materials=tuple(replace(x, id=mid[x.id]) for x in m.materials),
        stages=tuple(replace(s, id="s" + s.id) for s in m.stages),
        assignments=tuple(replace(a, material=mid[a.material]) for a in m.assignments),
        conditions=tuple(replace(c, span=span(c.span)) for c in m.conditions),
        loads=tuple(replace(ld, span=span(ld.span)) if isinstance(ld, md.DistributedLoad) else ld
                    for ld in m.loads))


MOVES = {
    "a vertex": _b(BASE, 0, vertices=((0.0, -10.0), (20.0, -10.0), (20.0, -4.0), (20.0, 0.0), (0.0, 0.5),
                                      (0.0, -4.0))),
    "an arc": _b(BASE, 0, segments=(md.SegmentAttr(1, (10.0, -100.0)),)),
    "divisions": _b(BASE, 0, segments=(md.SegmentAttr(0, divisions=9),)),
    "the kind of a boundary": _b(BASE, 1, kind=md.STAGE),
    "the analysis": replace(BASE, analysis=md.AXISYMMETRIC),
    "E": _mat(BASE, E=3.1e4),
    "nu": _mat(BASE, nu=0.31),
    "the unit weight": _mat(BASE, unit_weight=18.5),
    "the initial loading": _mat(BASE, initial_loading=md.FIELD_STRESS),
    "an assignment's material": replace(BASE, assignments=(replace(BASE.assignments[0], material="bottom"),)
                                        + BASE.assignments[1:]),
    "an excavation": replace(BASE, assignments=(replace(BASE.assignments[0], excavated=(False, True)),)
                             + BASE.assignments[1:]),
    "the order of the materials": replace(BASE, materials=BASE.materials[::-1]),
    "the field": replace(BASE, field=md.GravityField(0.0, (Stratum(-4.0, 18.0, 0.6, 0.7),
                                                           Stratum(-11.0, 24.0, 0.55, 0.45)))),
    "the default restraint": replace(BASE, default_restraint=md.Y),
    "a condition": replace(BASE, conditions=BASE.conditions[1:]),
    "a condition's stage": replace(BASE, conditions=(replace(BASE.conditions[0], active=(True, False)),)
                                   + BASE.conditions[1:]),
    "a load": replace(BASE, loads=(md.PointLoad((0.0, 0.0), 1.0, factors=(1.0, 1.0)),)),
    "a mesh setting": replace(BASE, mesh_settings=replace(BASE.mesh_settings, quality_bound=1.5)),
    "the mesh": replace(BASE, mesh=replace(BASE.mesh, nodes=((0.0, -10.000001),) + BASE.mesh.nodes[1:])),
}

STILL = {
    "the summary": replace(BASE, summary=md.Summary("Otro título", "otra persona")),
    "the units shown": replace(BASE, units="metric_mpa"),
    "a boundary's name": _b(BASE, 0, name="Otro"),
    "a material's name and colour": _mat(BASE, name="Otra", color="#000000"),
    "a stage's name": replace(BASE, stages=(md.Stage("1", "Inicio"), BASE.stages[1])),
    "a condition's name": replace(BASE, conditions=(replace(BASE.conditions[0], name="x"),)
                                  + BASE.conditions[1:]),
    "the notes of the mesh": replace(BASE, mesh=replace(BASE.mesh, notes={"x": 1}, warnings=("w",))),
    "every id, renamed everywhere": _renamed(BASE),
}


class TestTheModel:
    def test_every_datum_that_moves_the_result_moves_it(self):
        base = fp.model_fingerprint(BASE)
        for what, m in MOVES.items():
            assert fp.model_fingerprint(m) != base, what

    def test_and_nothing_else(self):
        base = fp.model_fingerprint(BASE)
        for what, m in STILL.items():
            assert fp.model_fingerprint(m) == base, what

    def test_nor_who_wrote_it(self):
        import ogr_fem2d
        base, doc = fp.model_fingerprint(BASE), fp.document_fingerprint(BASE)
        old = ogr_fem2d.__version__
        try:
            ogr_file.__version__ = "9.9.9"
            assert fp.model_fingerprint(BASE) == base and fp.document_fingerprint(BASE) == doc
        finally:
            ogr_file.__version__ = old


class TestTheDocument:
    def test_it_changes_with_everything(self):
        base = fp.document_fingerprint(BASE)
        for what, m in {**MOVES, **STILL}.items():
            assert fp.document_fingerprint(m) != base, what

    def test_both_survive_the_file(self):
        back = ogr_file.loads(ogr_file.dumps(BASE))
        assert fp.model_fingerprint(back) == fp.model_fingerprint(BASE)
        assert fp.document_fingerprint(back) == fp.document_fingerprint(BASE)


class TestTheCanonicalText:
    def test_sorted_fixed_ascii(self):
        assert fp.canonical({"b": 1, "a": [1.5, "ñ"]}) == '{"a":[1.5,"\\u00f1"],"b":1}'

    def test_no_nan(self):
        try:
            fp.canonical({"x": float("nan")})
        except ValueError:
            pass
        else:
            raise AssertionError("a NaN went into a fingerprint")

    def test_a_tuple_is_a_list_and_a_dataclass_its_fields(self):
        assert fp.digest((1, 2)) == fp.digest([1, 2])
        mi = translate.to_mesh_input(BASE)
        assert fp.digest(mi) == fp.digest(translate.to_mesh_input(BASE))
        assert fp.digest(mi) != fp.digest(replace(mi, settings=g.MeshSettings(boundary_nodes=61)))
