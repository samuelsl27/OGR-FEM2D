# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.15 (spec 006, T36; spec 005, D6 as modified by the owner on
2026-11-27) — the values recovered at the nodes, written when calculating
and marked with their method, so that the first drawing of a stage does
not wait for them (D15).

Invariants protected:

* **what is read is what would be recovered**: the stress and the strain
  recovered from the file a calculation wrote are, bit for bit, those
  recovered again from its fields, in every stage (excavated elements
  included), and the queries give the same rows with them and without;
* **they are used only for the method they are of**: a mark other than
  ``recovery.METHOD`` (a method improved since) makes the reader recover
  again (D6's reason: a better method is seen on old results), and a file
  without them (``recovered=False``, or an earlier program's) is read as
  before;
* **once per node and material**: the table and its index give back the
  values per element node, NaN for an element not active; values that
  differ for one node and material are refused, as they would not come
  back the same;
* a group that is not as written is a damaged file, said at once.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import h5py
import numpy as np

import _results
from ogr_fem2d.model import ogr_file
from ogr_fem2d.results import calculate as calc
from ogr_fem2d.results import queries as qy
from ogr_fem2d.results import recovery, store

KINDS = ("stress", "strain")


class _Calculated:
    def __init__(self, recovered=True):
        self.recovered = recovered

    def __enter__(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "modelo.ogrfem2d"
        self.m = _results.excavated_tunnel(3)
        ogr_file.write(self.m, self.path)
        calc.calculate(self.m, self.path, recovered=self.recovered)
        return self

    def results(self):
        return calc.open_results(self.path).results

    def __exit__(self, *exc):
        self.dir.cleanup()


def _again(view, kind):
    return qy.recover(view.mesh, view.active, view.tensor(kind))


def _same(a, b):
    return (np.array_equal(a.values, b.values, equal_nan=True)
            and np.array_equal(a.source, b.source) and a.notes == b.notes)


class TestWhatIsReadIsWhatWouldBeRecovered:
    def test_every_stage_and_both_tensors(self):
        with _Calculated() as c:
            r = c.results()
            excavated = 0
            for k in range(r.n_stages):
                for kind in KINDS:
                    assert r.recovered(k, kind, recovery.METHOD) is not None, (k, kind)
                    view = qy.View(r, k)
                    kept = view.recovered(kind)
                    assert _same(kept, _again(view, kind)), (k, kind)
                excavated += int((~view.active).sum())
                assert np.isnan(kept.values[~view.active]).all()
            assert excavated > 0                          # inactive elements were seen

    def test_the_queries_give_the_same_rows(self):
        with _Calculated() as c, _Calculated(recovered=False) as bare:
            assert bare.results().recovered(1, "stress", recovery.METHOD) is None
            for q in ("sigma_1", "sigma_xx", "eps_v", "gamma_max"):
                a = qy.line(qy.View(c.results(), 2), q, [(1.5, 0.0), (9.5, 0.0)], 30).rows
                b = qy.line(qy.View(bare.results(), 2), q, [(1.5, 0.0), (9.5, 0.0)], 30).rows
                assert [x.value for x in a] == [x.value for x in b], q


class TestOnlyForItsMethod:
    def test_another_mark_is_recovered_again(self):
        with _Calculated() as c:
            with h5py.File(calc.results_path(c.path), "r+") as f:
                f["stages"]["0001"]["recovered"]["stress"].attrs["method"] = "spr-by-material/0"
            r = c.results()
            assert r.recovered(1, "stress", recovery.METHOD) is None
            assert r.recovered(1, "strain", recovery.METHOD) is not None
            calls = []
            real = recovery.recover
            recovery.recover = lambda *a: calls.append(1) or real(*a)
            try:
                qy.View(r, 1).recovered("stress")
                assert calls == [1]                       # recovered again
                qy.View(r, 1).recovered("strain")
                qy.View(r, 0).recovered("stress")
                assert calls == [1]                       # those of its method: read
            finally:
                recovery.recover = real


class TestTheTable:
    def test_back_the_same_and_nan_where_inactive(self):
        with _Calculated() as c:
            view = qy.View(c.results(), 2)
            rec = _again(view, "stress")
            table, at = store.node_table(rec.values, view.mesh.element_material,
                                         view.mesh.elements)
            assert len(table) < 0.5 * rec.values.shape[0] * rec.values.shape[1]
            assert (at[~view.active] == -1).all() and (at[view.active] >= 0).all()
            assert np.array_equal(store.from_node_table(table, at), rec.values, equal_nan=True)

    def test_values_that_differ_for_one_node_are_refused(self):
        elements = np.array([[0, 1, 2], [2, 1, 3]])
        values = np.ones((2, 3, 4))
        values[1, 0, 0] = 2.0                             # node 2, material 0, two values
        try:
            store.node_table(values, np.array([0, 0]), elements)
        except ValueError as err:
            assert "differ" in str(err)
        else:
            raise AssertionError("two values of one node and material were taken")
        table, at = store.node_table(values, np.array([0, 1]), elements)   # two materials
        assert len(table) == 6


class TestDamaged:
    def test_a_group_not_as_written(self):
        with _Calculated() as c:
            with h5py.File(calc.results_path(c.path), "r+") as f:
                del f["stages"]["0002"]["recovered"]["strain"]["at"]
            opened = calc.open_results(c.path)
            assert opened.status == calc.DAMAGED
            assert "recovered/strain" in opened.message
