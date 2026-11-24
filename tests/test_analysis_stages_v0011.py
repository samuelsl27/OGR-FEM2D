# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.11 (spec 005, T3) — the engine gives its stages one at a time (D7).

Invariants protected:

* **the same numbers**: ``run`` is ``list(stages())``, and a model of three
  stages (an excavation and a stage that changes nothing) gives the same
  outcomes either way. Cases 003 to 007 gave the same outcomes bit for bit
  before and after the change (a digest of every field, changelog v0.0.11,
  T3); cases 001 and 002 do not go through the analysis;
* **a stage that fails keeps the ones before it**: the generator gives the
  first stage, and then the error of the second (restraints that leave the
  model free), with the stage's index;
* **the input is checked first**: an invalid model raises before any stage.
"""
from __future__ import annotations

from dataclasses import replace

import _models
from ogr_fem2d.engine import analysis
from ogr_fem2d.engine import model as em
from ogr_fem2d.model import translate


def _engine():
    m = _models.meshed(_models.with_stages(_models.tunnel(), 3))
    m = replace(m, assignments=(m.assignments[0],
                                replace(m.assignments[1], excavated=(False, True, True))))
    return translate.to_engine(m)


class TestTheStages:
    def test_run_is_the_list_of_the_stages(self):
        engine = _engine()
        a, b = analysis.run(engine), list(analysis.stages(engine))
        assert len(a) == 3 and a == b
        assert [o.solved for o in a] == [False, True, False]

    def test_a_failing_stage_keeps_the_ones_before(self):
        engine = _engine()
        loose = replace(engine.stages[1], restraints=())
        engine = replace(engine, stages=(engine.stages[0], loose, engine.stages[2]))
        got = []
        try:
            for outcome in analysis.stages(engine):
                got.append(outcome)
        except analysis.InsufficientRestraintError as err:
            assert err.stage == 1
        else:
            raise AssertionError("the loose stage did not fail")
        assert len(got) == 1 and got[0] == analysis.run(replace(engine, stages=engine.stages[:1]))[0]

    def test_the_input_is_checked_first(self):
        engine = _engine()
        bad = replace(engine, element_material=(5,) * len(engine.elements))
        stages = analysis.stages(bad)
        try:
            next(stages)
        except em.InputError:
            pass
        else:
            raise AssertionError("an invalid model gave a stage")
