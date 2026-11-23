# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.9 (spec 004, T1) — the FEM model and its validation as a document
(RF-1, RF-3, RF-5, RF-6; docs/modelo/formato.md).

Invariants protected:

* **a valid model passes untouched**: the tunnel, the two strata and the
  strip of tests/_models.py have no problem, and validate() hands the same
  object back;
* **every rule catches what it is for, and says where**: for each rule of
  model.RULES there is a model that breaks it, and the problem names that
  rule and the boundary, material, stage, assignment, condition or load at
  fault. The table covers RULES exactly, so a rule added without its case,
  or a case for a rule that is gone, fails here;
* **no default in silence** (D5, D9, D15, D16): an unknown unit system is an
  error, not the core's silent kPa; a material may lack E and nu as a
  document (a model opened from Slip2D) but the model says it is not ready
  only when it goes to the engine (tests of T8);
* **a setting that does nothing is refused** (rule 7): a segment entry with
  no attribute, an angle with an orientation that has none, active flags on
  an imposed displacement or factors on a restraint;
* **all problems at once**.
"""
from __future__ import annotations

from dataclasses import replace

import _models
from ogr_fem2d.engine.initial_stress import Stratum
from ogr_fem2d.model import model as md

T = _models.tunnel()
L = _models.layers()
S = _models.strip()


def _with_boundary(m, k, **change):
    bs = list(m.boundaries)
    bs[k] = replace(bs[k], **change)
    return replace(m, boundaries=tuple(bs))


CASES = {
    "analysis": (replace(T, analysis="plane_stress"), "model"),
    "units": (replace(T, units="metric_mpa_storage"), "model"),
    "boundary": (_with_boundary(T, 1, closed=False), "boundary 'hole'"),
    "boundary_id": (_with_boundary(T, 1, id="ext"), "boundary 'ext'"),
    "segment_attr": (_with_boundary(T, 0, segments=(md.SegmentAttr(0),)), "segment 0"),
    "external": (_with_boundary(T, 1, kind=md.EXTERNAL), "model"),
    "left_of_axis": (replace(T, analysis=md.AXISYMMETRIC), "boundary 'ext'"),
    "material": (replace(T, materials=(md.Material("rock", "Roca", 1e7, 0.5),)), "material 'rock'"),
    "material_id": (replace(T, materials=T.materials + (md.Material("rock"),)), "material 'rock'"),
    "stage": (replace(T, stages=()), "model"),
    "assignment": (replace(T, assignments=(md.Assignment((5.0, 0.0), "granite", (False,)),
                                           T.assignments[1])), "assignment at (5.0, 0.0)"),
    "reactivated": (replace(_models.with_stages(T, 2),
                            assignments=(replace(T.assignments[0], excavated=(False, False)),
                                         md.Assignment((0.0, 0.0), "rock", (True, False)))),
                    "assignment at (0.0, 0.0)"),
    "field": (replace(T, field=md.ConstantField(10.0, 20.0, 10.0, 0.0)), "field stress"),
    "default_restraint": (replace(T, default_restraint="fixed"), "model"),
    "condition": (replace(S, conditions=(md.Condition(md.X, md.Span("ext", (0.0, 0.0), (5.0, 0.0)),
                                                       active=(True,)),)), "condition 0"),
    "load": (replace(S, loads=(md.PointLoad((3.0, 0.0), 10.0, factors=(1.0,)),)), "load 0"),
    "mesh": (replace(T, mesh=md.StoredMesh(((0.0, 0.0),), ((0, 1, 2),), (0,), ())), "mesh"),
}


def _rules(m):
    return [p.rule for p in md.problems(m)]


class TestValidModels:
    def test_the_models_of_the_tests_are_valid(self):
        for m in (T, L, S):
            assert md.problems(m) == [], md.problems(m)
            assert md.validate(m) is m

    def test_a_model_by_default_is_one_stage_fixed_outside(self):
        m = md.Model()
        assert [s.id for s in m.stages] == ["1"] and m.default_restraint == md.XY
        assert m.units == "metric_kpa" and m.analysis == "plane_strain"


class TestEveryRule:
    def test_the_table_covers_the_rules(self):
        assert set(CASES) == set(md.RULES)

    def test_each_rule_catches_its_case_and_says_where(self):
        for rule, (m, where) in CASES.items():
            found = [p for p in md.problems(m) if p.rule == rule]
            assert found, (rule, md.problems(m))
            assert any(where in p.where for p in found), (rule, found)

    def test_all_problems_at_once(self):
        m = replace(T, analysis="x", units="y", default_restraint="z")
        assert {"analysis", "units", "default_restraint"} <= set(_rules(m))
        try:
            md.validate(m)
        except md.ModelError as err:
            assert len(err.problems) >= 3
        else:
            raise AssertionError("validate() let an invalid model through")


class TestNoSilentDefault:
    def test_an_unknown_unit_system_is_an_error(self):
        assert "units" in _rules(replace(T, units="metric_kpa_typo"))
        for sid in ("metric_kpa", "metric_mpa", "imperial_psf"):
            assert "units" not in _rules(replace(T, units=sid))

    def test_a_material_without_e_and_nu_is_a_valid_document(self):
        m = replace(T, materials=(md.Material("rock", "Roca"),))
        assert md.problems(m) == []


class TestNothingThatDoesNothing:
    def test_an_empty_segment_entry(self):
        assert "segment_attr" in _rules(_with_boundary(T, 0, segments=(md.SegmentAttr(1),)))

    def test_an_angle_without_an_orientation_that_uses_it(self):
        load = replace(S.loads[0], angle=30.0)
        assert "load" in _rules(replace(S, loads=(load,)))
        ok = replace(S.loads[0], orientation=md.ANGLE_FROM_HORIZONTAL, angle=30.0)
        assert "load" not in _rules(replace(S, loads=(ok,)))

    def test_flags_and_factors_where_they_belong(self):
        span = md.Span("ext", (0.0, 0.0), (0.0, -20.0))
        bad = (md.Condition(md.DISPLACEMENT, span, active=(True,), ux=0.1, factors=(1.0,)),
               md.Condition(md.X, span, active=(True,), factors=(1.0,)),
               md.Condition(md.DISPLACEMENT, span, factors=(1.0,)))
        for c in bad:
            assert "condition" in _rules(replace(S, conditions=(c,))), c
        good = md.Condition(md.DISPLACEMENT, span, ux=0.1, factors=(None,))
        assert "condition" not in _rules(replace(S, conditions=(good,)))

    def test_a_point_load_has_no_normal(self):
        load = md.PointLoad((1.0, 0.0), 10.0, md.NORMAL, factors=(1.0,))
        assert "load" in _rules(replace(S, loads=(load,)))


class TestSpans:
    def test_a_span_goes_forward_and_may_wrap_a_closed_boundary(self):
        b = S.boundaries[0]
        assert md.span_indices(b, md.Span("ext", (20.0, 0.0), (0.0, 0.0))) == [2, 3]
        assert md.span_indices(b, md.Span("ext", (0.0, 0.0), (20.0, -20.0))) == [4, 0]
        assert md.span_indices(b, md.Span("ext")) == [0, 1, 2, 3, 4]
        assert md.span_indices(b, md.Span("ext", (1.0, 0.0), (1.0, 0.0))) is None
        assert md.span_indices(b, md.Span("ext", (7.0, 0.0), (0.0, 0.0))) is None

    def test_an_open_boundary_runs_only_forward(self):
        b = L.boundaries[1]
        assert md.span_indices(b, md.Span("contact", (0.0, -4.0), (20.0, -4.0))) == [0]
        assert md.span_indices(b, md.Span("contact", (20.0, -4.0), (0.0, -4.0))) is None

    def test_the_strata_go_down(self):
        f = md.GravityField(0.0, (Stratum(-4.0, 18.0, 0.5, 0.5), Stratum(-2.0, 20.0, 0.5, 0.5)))
        assert "field" in _rules(replace(L, field=f))


class TestTheEdges:
    def test_a_segment_that_does_not_exist(self):
        m = _with_boundary(T, 0, segments=(md.SegmentAttr(4, divisions=3),))
        assert "segment_attr" in _rules(m)
        assert "segment_attr" not in _rules(_with_boundary(T, 0, segments=(md.SegmentAttr(3, divisions=3),)))

    def test_no_external_boundary(self):
        m = replace(T, boundaries=(T.boundaries[1],))
        assert "external" in _rules(m)

    def test_a_mesh_with_a_node_that_does_not_exist(self):
        good = md.StoredMesh(((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)), ((0, 1, 2),), (0,), (), {}, (), "x")
        assert "mesh" not in _rules(replace(T, mesh=good))
        bad = replace(good, elements=((0, 1, 3),))
        assert "mesh" in _rules(replace(T, mesh=bad))
