# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.11 (spec 005, T17) — rules 7 and 12 on what spec 005 adds.

Invariants protected:

* **rule 7, no setting does nothing**: each option of the queries, of the
  table and of the calculation moves what it gives (the number of points,
  where they are, their values, the stage, the quantity, the units, the
  name in axisymmetry, the gzip level (the size of the file, its numbers
  the same), the stop between stages);
* **rule 12, the defaults that decide the result go with it**: a query
  carries its settings (the points, the distance 0 and the side, by
  default) and its method (the recovery), the table writes them in its
  header with the convention and the unit, and the results file keeps what
  decided the calculation (``translate.deciding_values``) and the engine's
  variant.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import h5py
import numpy as np

import _results
from ogr_fem2d.model import ogr_file, translate
from ogr_fem2d.results import calculate as calc
from ogr_fem2d.results import queries as qy
from ogr_fem2d.results import store
from ogr_fem2d.results import table


def _values(q):
    return [r.value for r in q.rows]


class TestRule7:
    def test_every_option_of_the_queries_moves_what_they_give(self):
        m = _results.excavated_tunnel(2)
        with tempfile.TemporaryDirectory() as d:
            results = _results.calculated(m, d)
            v1, v0 = qy.View(results, 1), qy.View(results, 0)
            line = [(1.5, 0.0), (4.0, 0.0)]
            moves = {
                "n": (qy.line(v1, "u", line, 3), qy.line(v1, "u", line, 5)),
                "vertices or n": (qy.line(v1, "u", line, None), qy.line(v1, "u", line, 3)),
                "the stage": (qy.line(v0, "u", line, 3), qy.line(v1, "u", line, 3)),
                "the quantity": (qy.line(v1, "u_x", line, 3), qy.line(v1, "u_y", line, 3)),
                "n per segment": (qy.on_boundary(v1, "u", m, "hole", 1),
                                  qy.on_boundary(v1, "u", m, "hole", 2)),
                "the distance": (qy.on_boundary(v1, "u", m, "hole", 1, 0.1, qy.OUTSIDE),
                                 qy.on_boundary(v1, "u", m, "hole", 1, 0.3, qy.OUTSIDE)),
                "the side": (qy.on_boundary(v1, "sigma_1", m, "hole", 1, 0.1, qy.INSIDE),
                             qy.on_boundary(v1, "sigma_1", m, "hole", 1, 0.1, qy.OUTSIDE)),
            }
            for what, (a, b) in moves.items():
                assert _values(a) != _values(b) or [r.reason for r in a.rows] != \
                    [r.reason for r in b.rows], what

    def test_the_options_of_the_table(self):
        with tempfile.TemporaryDirectory() as d:
            view = qy.View(_results.calculated(_results.loaded_layers(), d), 0)
            q = qy.line(view, "sigma_z", [(5.0, -1.0), (5.0, -3.0)], 3)
            assert table.to_csv(q, "metric_kpa") != table.to_csv(q, "metric_mpa")
            assert table.to_csv(q, analysis="plane_strain") != table.to_csv(q, analysis="axisymmetric")
            assert table.to_csv(q, query_id=1) != table.to_csv(q, query_id=2)

    def test_the_options_of_the_calculation(self):
        m = _results.excavated_tunnel(2)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "modelo.ogrfem2d"
            ogr_file.write(m, path)
            sizes = []
            for level in (None, 4):
                calc.calculate(m, path, level=level)
                sizes.append(calc.results_path(path).stat().st_size)
                stress = store.read(calc.results_path(path)).field(1, "stress")
            assert sizes[0] != sizes[1]
            calc.calculate(m, path, level=None)
            assert np.array_equal(store.read(calc.results_path(path)).field(1, "stress"), stress,
                                  equal_nan=True)                   # the size moves, not the numbers
            assert calc.calculate(m, path).status != calc.calculate(m, path, should_stop=lambda: True).status


class TestRule12:
    def test_a_query_carries_its_settings_and_its_method(self):
        m = _results.excavated_tunnel()
        with tempfile.TemporaryDirectory() as d:
            view = qy.View(_results.calculated(m, d), 0)
            q = qy.on_boundary(view, "sigma_1", m, "hole")
            settings = dict(q.settings)
            assert settings["distance"] == 0.0 and settings["side"] == "on it"
            assert settings["points"] == "at the vertices" and "patch recovery" in q.method
            head = table.to_csv(q)
            for want in ("settings: boundary = hole", "distance = 0.0", "compression positive",
                         "patch recovery", "unit: kPa"):
                assert want in head, want

    def test_the_file_keeps_what_decided_the_calculation(self):
        m = _results.excavated_tunnel()
        with tempfile.TemporaryDirectory() as d:
            results = _results.calculated(m, d)
            decided = [what for what, _v, _y in results.deciding]
            assert decided == [what for what, _v, _y in translate.deciding_values(m)]
            assert "solver: tolerance" in decided and results.header.engine_variant == "reference"
            with h5py.File(results.path, "r") as f:
                assert "tension positive" in f.attrs["sign_convention"]
