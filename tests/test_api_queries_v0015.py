# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.15 (spec 006, T32) — what a query refuses is refused saying it (RF-7):
a line with two points the same, n < 2, a distance on
a boundary without its side. Before, the query's ValueError escaped the
operation as it was (found in T31); now it is an ``InvalidArgument`` that
says what is wrong, also through ``results_table``.
"""
from __future__ import annotations

from test_api_results_v0013 import _Calculated, _refused

from ogr_core.api import InvalidArgument


class TestRefusedSayingIt:
    def test_the_lines_and_the_boundary(self):
        with _Calculated() as c:
            for kw, words in (
                    ({"points_xy": [[2.0, -2.0], [2.0, -2.0]]}, "two consecutive points"),
                    ({"points_xy": [[2.0, -2.0], [8.0, -2.0]], "n": 1}, "n >= 2")):
                _refused(lambda: c.call("results_query", quantity="sigma_yy", kind="line", **kw),
                         InvalidArgument, "cannot be made so", words)
                _refused(lambda: c.call("results_table", path="t.csv", quantity="sigma_yy",
                                        kind="line", **kw), InvalidArgument, words)
            _refused(lambda: c.call("results_query", quantity="sigma_yy", kind="boundary",
                                    boundary="ext", distance=0.5),
                     InvalidArgument, "needs its side")
