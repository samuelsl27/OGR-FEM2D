# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.13 (spec 006, T11; spec 004 modified) — a model being drawn is a
document: saved and opened, not calculated.

Until this version ``ogr_file`` asked the whole model valid to write it and
to read it, and the engineer could not save the work until the model was
finished (the anomaly of T11). Now a file holds a model valid AS A DOCUMENT
(``model.validate_document``): what it may still break are the rules of
``model.DRAWING_RULES`` (no external yet, and the geometry of ``regions``).

Invariants protected:

* **a model being drawn goes to the file and back unchanged**: an empty
  one, one without its external, one whose boundaries still cross, one with
  a region without its material; the same model (``==``) and the same
  bytes written again, its problems said by ``model.problems``;
* **what a document needs is still refused**, writing and reading: a
  material with nu = 0.7, an assignment to a material that does not exist,
  a load on a boundary that does not exist;
* **it is not calculated**: the engine refuses a model being drawn, naming
  what is unfinished.
"""
from __future__ import annotations

from dataclasses import replace

import _models
from ogr_fem2d.model import edit, ogr_file, translate
from ogr_fem2d.model import model as md


def _drawings():
    lay = _models.layers()
    crossing = edit.add_boundary(lay, md.MATERIAL, ((5.0, -1.0), (5.0, -9.0)), boundary_id="x")
    return {
        "empty": md.Model(),
        "no external": edit.add_boundary(md.Model(), md.EXCAVATION, ((0, 0), (1, 0), (1, 1))),
        "crossing": crossing,
        "unassigned": replace(lay, assignments=lay.assignments[:1]),
    }


def _refused(fn, rule):
    try:
        fn()
    except md.ModelError as err:
        assert err.problems[0].rule == rule, str(err)
    else:
        raise AssertionError(f"accepted; expected {rule!r}")


class TestADocument:
    def test_to_the_file_and_back(self):
        expected = {"empty": {"external"}, "no external": {"external"},
                    "crossing": {"crossing"}, "unassigned": {"region_unassigned"}}
        for name, m in _drawings().items():
            text = ogr_file.dumps(m)
            back = ogr_file.loads(text)
            assert back == m and ogr_file.dumps(back) == text, name
            assert {p.rule for p in md.problems(back)} == expected[name], name

    def test_what_a_document_needs_is_still_refused(self):
        m = _models.layers()
        for broken, rule in (
                (replace(m, materials=(replace(m.materials[0], nu=0.7),) + m.materials[1:]),
                 "material"),
                (replace(m, assignments=(replace(m.assignments[0], material="none"),)
                         + m.assignments[1:]), "assignment"),
                (replace(m, loads=(md.DistributedLoad(md.Span("nope"), 1.0, 1.0, factors=(1.0,)),)),
                 "load")):
            _refused(lambda: ogr_file.dumps(broken), rule)
            data = ogr_file.to_dict(broken)
            _refused(lambda: ogr_file.from_dict(data), rule)

    def test_not_calculated(self):
        for name, m in _drawings().items():
            try:
                translate.to_engine(m)
            except md.ModelError as err:
                assert err.problems, name
            else:
                raise AssertionError(f"{name}: a model being drawn went to the engine")
