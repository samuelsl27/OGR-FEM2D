# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.11 (spec 005, T5) — calculate a model, write its results and open them
with their state (RF-1 to RF-3; D7, D13).

Invariants protected:

* **the results are the engine's**: ``<root>.h5`` beside ``<root>.ogrfem2d``,
  every stage the engine's outcome, with the model's fingerprint, the
  versions, the engine's variant and what decided the result;
* **every state** (RF-3): valid; stale when the model changed after the
  calculation (and its results only when asked for explicitly); missing;
  damaged; incomplete, with the stages before the one that failed and the
  engine's error; cancelled between stages;
* **another version is not stale** (D7): it is valid, and says who wrote it;
* **a model that cannot be translated writes nothing**: its error, and the
  previous ``.h5`` stays.
"""
from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path

import h5py

import _models
from ogr_fem2d.engine import analysis
from ogr_fem2d.model import model as md
from ogr_fem2d.model import ogr_file, translate
from ogr_fem2d.results import calculate as calc
from ogr_fem2d.results import store


def _model():
    m = _models.meshed(_models.with_stages(_models.tunnel(), 2))
    return replace(m, assignments=(m.assignments[0], replace(m.assignments[1], excavated=(False, True))))


M = _model()


def _saved(d, m=M):
    path = Path(d) / "modelo.ogrfem2d"
    ogr_file.write(m, path)
    return path


class TestCalculate:
    def test_the_results_are_the_engines(self):
        with tempfile.TemporaryDirectory() as d:
            path = _saved(d)
            done = calc.calculate(M, path)
            assert done.path == Path(d) / "modelo.h5" and done.status == store.COMPLETE
            opened = calc.open_results(path)
            assert opened.status == calc.VALID and opened.other_version == ""
            r = opened.results
            for k, out in enumerate(analysis.run(translate.to_engine(M))):
                assert r.outcome(k) == out, k
            assert r.header.engine_variant == "reference" and r.header.written_by == calc.written_by()
            assert [s["id"] for s in map(r.stage_info, range(2))] == ["1", "2"]

    def test_a_model_that_cannot_be_translated_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            path = _saved(d)
            calc.results_path(path).write_bytes(b"previous")
            try:
                calc.calculate(replace(M, mesh=None), path)
            except md.ModelError:
                pass
            else:
                raise AssertionError("calculated without a mesh")
            assert calc.results_path(path).read_bytes() == b"previous"


class TestTheStates:
    def test_stale_missing_damaged(self):
        with tempfile.TemporaryDirectory() as d:
            path = _saved(d)
            assert calc.open_results(path).status == calc.MISSING
            calc.calculate(M, path)
            changed = replace(M, materials=(replace(M.materials[0], E=2.0e7),))
            opened = calc.open_results(path, changed)
            assert opened.status == calc.STALE
            try:
                opened.results
            except calc.NotValidError as err:
                assert "stale" in str(err)
            else:
                raise AssertionError("stale results given as they are")
            assert opened.read_anyway().n_stages == 2
            calc.results_path(path).write_bytes(b"garbage")
            opened = calc.open_results(path)
            assert opened.status == calc.DAMAGED and "HDF5" in opened.message
            try:
                opened.read_anyway()
            except calc.NotValidError:
                pass
            else:
                raise AssertionError("damaged results read")

    def test_incomplete_keeps_the_stages_before(self):
        """A release of the whole external boundary in stage 2 leaves the
        model free there: the engine stops, stage 1 stays."""
        free = md.Condition(md.FREE, md.Span("ext"), active=(False, True), name="Suelto")
        m = replace(M, conditions=(free,))
        with tempfile.TemporaryDirectory() as d:
            path = _saved(d, m)
            done = calc.calculate(m, path)
            assert (done.status, done.stages, done.stopped_at) == (store.INCOMPLETE, 1, 1)
            opened = calc.open_results(path)
            assert opened.status == calc.INCOMPLETE and "InsufficientRestraintError" in opened.message
            r = opened.read_anyway()
            assert r.n_stages == 1 and r.outcome(0) == analysis.run(translate.to_engine(M))[0]

    def test_cancelled_between_stages(self):
        with tempfile.TemporaryDirectory() as d:
            path = _saved(d)
            done = calc.calculate(M, path, should_stop=lambda: True)
            assert (done.status, done.stages, done.stopped_at) == (store.CANCELLED, 1, 1)
            opened = calc.open_results(path)
            assert opened.status == calc.CANCELLED and "'2'" in opened.message

    def test_another_version_is_valid_and_said(self):
        with tempfile.TemporaryDirectory() as d:
            path = _saved(d)
            calc.calculate(M, path)
            with h5py.File(calc.results_path(path), "a") as f:
                f.attrs["written_by"] = "OGR FEM2D 0.0.0"
            opened = calc.open_results(path)
            assert opened.status == calc.VALID and "OGR FEM2D 0.0.0" in opened.other_version
