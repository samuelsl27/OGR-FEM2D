# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.11 (spec 005, T12) — a query as a table (RF-14; D15).

Invariants protected:

* **the header declares it all**: the program, the quantity and its name,
  the unit, the convention, the stage, the method, the kind of query and
  the fingerprint;
* **the units shown**: the same query in MPa is the one in kPa divided by
  1000; in feet, the coordinates are the metres times 3.2808...;
* **the columns are the fixed ones**, and every number reads back as it was
  written (repr); a row without value has an empty value and its reason in
  ``source``;
* **a history** is a table with a row per stage;
* **an unknown unit system** is an error (the core would put kPa in its
  place in silence).
"""
from __future__ import annotations

import csv
import io
import tempfile

import _results
from ogr_core.units import Quantity as Q
from ogr_core.units.unit_system import get_system
from ogr_fem2d.results import queries as qy
from ogr_fem2d.results import table


def _parsed(text):
    lines = text.splitlines()
    head = [line for line in lines if line.startswith("# ")]
    rows = list(csv.reader(io.StringIO("\n".join(line for line in lines if not line.startswith("#")))))
    return head, rows[0], rows[1:]


def _query(d):
    view = qy.View(_results.calculated(_results.loaded_layers(), d), 0)
    return view, qy.line(view, "sigma_1", [(5.0, -9.0), (5.0, -11.0)], 3)


class TestTheTable:
    def test_the_header_and_the_columns(self):
        with tempfile.TemporaryDirectory() as d:
            _view, q = _query(d)
            head, columns, rows = _parsed(table.to_csv(q, "metric_mpa", fingerprint="f00d"))
            text = "\n".join(head)
            for want in ("OGR FEM2D", "sigma_1", "Sigma 1 (in plane)", "unit: MPa", "compression positive",
                         "query: line", "stage: 0", "superconvergent patch recovery", "f00d"):
                assert want in text, want
            assert tuple(columns) == table.COLUMNS
            assert rows[-1][5] == "" and rows[-1][8] == "outside"
            assert rows[0][8] == "spr"

    def test_mpa_is_kpa_over_1000_and_numbers_read_back(self):
        with tempfile.TemporaryDirectory() as d:
            _view, q = _query(d)
            _h, _c, kpa = _parsed(table.to_csv(q, "metric_kpa"))
            _h, _c, mpa = _parsed(table.to_csv(q, "metric_mpa"))
            for row_k, row_m, r in zip(kpa, mpa, q.rows):
                if r.value is None:
                    continue
                assert float(row_k[5]) == r.value
                assert float(row_m[5]) == get_system("metric_mpa").to_user(r.value, Q.PRESSURE)
                assert abs(float(row_m[5]) - r.value / 1000.0) <= 1e-12 * abs(r.value)
                assert float(row_k[3]) == r.y and float(row_m[3]) == r.y
            _h, _c, feet = _parsed(table.to_csv(q, "imperial_ksf"))
            assert abs(float(feet[1][3]) - q.rows[1].y * 3.280839895013123) < 1e-12

    def test_a_history_and_an_unknown_system(self):
        with tempfile.TemporaryDirectory() as d:
            results = _results.calculated(_results.excavated_tunnel(2), d)
            h = qy.history(results, "u", 3.0, 0.5)
            head, _c, rows = _parsed(table.to_csv(h))
            assert [r[1] for r in rows] == ["0", "1"] and "a row per stage" in "\n".join(head)
            try:
                table.to_csv(h, "metric_xyz")
            except ValueError as err:
                assert "metric_xyz" in str(err)
            else:
                raise AssertionError("an unknown unit system")
