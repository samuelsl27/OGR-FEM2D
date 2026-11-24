# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.12 (spec 006, T6) — what ``calculate`` tells as it goes (RF-9, D9).

Invariants protected:

* **the events come in order**: a stage started, then done, stage by
  stage, and the end with the status and how many stages were written;
* **also when it stops**: a stage that fails says so with its reason, and
  the end says ``incomplete``; a cancellation ends after the last stage
  solved, ``cancelled``;
* **a stage done says whether it was solved, its steps and its last
  iteration**, those of its outcome (in elasticity one step of one
  iteration, or of none in a stage that changes nothing);
* **it is told, it decides nothing**: the results with ``progress`` are the
  engine's, bit for bit, on a model of three stages and on case 007 opened
  from its ``modelo.ogrfem2d``.
"""
from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path

import _cases_model
import _models
from ogr_fem2d.engine import analysis
from ogr_fem2d.model import model as md
from ogr_fem2d.model import ogr_file, translate
from ogr_fem2d.results import calculate as calc
from ogr_fem2d.results import store


def _three():
    m = _models.meshed(_models.with_stages(_models.tunnel(), 3))
    return replace(m, assignments=(m.assignments[0],
                                   replace(m.assignments[1], excavated=(False, True, True))))


def _run(m, **kw):
    heard = []
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "modelo.ogrfem2d"
        ogr_file.write(m, path)
        done = calc.calculate(m, path, progress=heard.append, **kw)
        r = calc.open_results(path).read_anyway()
        outcomes = [r.outcome(k) for k in range(r.n_stages)]
    return done, heard, outcomes


def _events(heard):
    return [(p.event, p.stage) for p in heard]


class TestEvents:
    def test_in_order(self):
        done, heard, _ = _run(_three())
        assert _events(heard) == [(calc.STARTED, 0), (calc.DONE, 0), (calc.STARTED, 1),
                                  (calc.DONE, 1), (calc.STARTED, 2), (calc.DONE, 2),
                                  (calc.FINISHED, 3)]
        assert [p.stage_id for p in heard[:2]] == ["1", "1"] and heard[0].stages == 3
        end = heard[-1]
        assert (end.status, end.stage_id) == (store.COMPLETE, "") and done.stages == 3

    def test_steps_and_iterations_of_the_outcome(self):
        # stage 1 is the field stress in equilibrium, and stage 3 repeats
        # stage 2: neither changes anything, and neither is solved (spec 002);
        # stage 2 excavates, one step of one iteration
        _, heard, outcomes = _run(_three())
        done = [p for p in heard if p.event == calc.DONE]
        assert [p.solved for p in done] == [out.solved for out in outcomes] == [False, True, False]
        for p, out in zip(done, outcomes):
            last = max((it for step, it, _r in out.history if step == out.steps), default=0)
            assert (p.steps, p.iteration) == (out.steps, last)
        assert [(p.steps, p.iteration) for p in done] == [(1, 0), (1, 1), (1, 0)]

    def test_a_stage_that_fails(self):
        free = md.Condition(md.FREE, md.Span("ext"), active=(False, True, True), name="Suelto")
        _, heard, _ = _run(replace(_three(), conditions=(free,)))
        assert _events(heard) == [(calc.STARTED, 0), (calc.DONE, 0), (calc.STARTED, 1),
                                  (calc.FAILED, 1), (calc.FINISHED, 1)]
        assert "InsufficientRestraintError" in heard[3].reason
        assert heard[-1].status == store.INCOMPLETE and heard[-1].reason == heard[3].reason

    def test_cancelled(self):
        _, heard, _ = _run(_three(), should_stop=lambda: True)
        assert _events(heard) == [(calc.STARTED, 0), (calc.DONE, 0), (calc.FINISHED, 1)]
        assert heard[-1].status == store.CANCELLED and "'2'" in heard[-1].reason
        assert heard[-1].stage_id == ""          # the end names no stage


class TestNothingChanges:
    def test_the_engines_numbers_bit_for_bit(self):
        m = _three()
        _, _, outcomes = _run(m)
        assert outcomes == analysis.run(translate.to_engine(m))

    def test_case_007_from_its_file(self):
        m = ogr_file.read(_cases_model.path("007-cavidad-esferica-malla-general"))
        _, heard, outcomes = _run(m)
        assert outcomes == analysis.run(translate.to_engine(m))
        assert heard[-1].status == store.COMPLETE
