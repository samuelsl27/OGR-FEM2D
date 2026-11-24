# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.12 (spec 006, T5) — assigning a material, one region at a time
(spec 004, D15, RF-4; the anomaly found in T5).

Until T5 the region of the point was found with the whole model valid: with
another region still without its material, the search failed, and the edit
took the region for one without an assignment and added a second one where
there was one already (``region_twice``). OGR Slip2D does not have it as a
fault, by another design: there a click is appended to a history, the last
one inside a region wins, and a region nobody assigned takes the first
material. Here a region has one assignment and none by default (D15).

Invariants protected:

* **reassigning a region changes its assignment**, also with another
  region still without its material: no second one is added;
* **a region without one takes a new one**, and the model, once every
  region has its material, is valid;
* **what cannot be assigned is refused, saying why**: a point on a boundary
  or outside the model, a geometry whose regions cannot be found (a
  crossing), a region that already holds two assignments; never a silent
  assignment that would count only later.
"""
from __future__ import annotations

from dataclasses import replace

import _models
from ogr_fem2d.model import cuts, edit, stages
from ogr_fem2d.model import model as md


def _half_assigned():
    lay = _models.layers()              # top (y > -4) and bottom regions
    return replace(lay, assignments=lay.assignments[:1])


def _refused(fn, rule: str):
    try:
        fn()
    except md.ModelError as err:
        assert err.problems[0].rule == rule, str(err)
    else:
        raise AssertionError(f"accepted; expected {rule!r}")


class TestOneRegionAtATime:
    def test_reassigning_with_another_region_unassigned(self):
        m = _half_assigned()
        out = stages.assign_material(m, (3.0, -1.0), "bottom")
        assert len(out.assignments) == 1 and out.assignments[0].material == "bottom"
        assert {p.rule for p in md.problems(out)} == {"region_unassigned"}
        # the second region of the list, in the whole model
        out = stages.assign_material(_models.layers(), (3.0, -7.0), "top")
        assert [a.material for a in out.assignments] == ["top", "top"]

    def test_the_region_without_one_takes_a_new_one(self):
        out = stages.assign_material(_half_assigned(), (3.0, -7.0), "bottom")
        assert len(out.assignments) == 2 and md.problems(out) == []

    def test_drawing_assigning_and_cutting(self):
        # a square, its material, then a line across: the new region is the
        # one without its material, and assigning it finishes the model
        m = edit.add_boundary(md.Model(), md.EXTERNAL, ((0, 0), (10, 0), (10, 10), (0, 10)))
        m = edit.add_material(edit.add_material(m, E=1.0, nu=0.2), E=2.0, nu=0.2)
        m = stages.assign_material(m, (5.0, 8.0), "m1")
        m = cuts.cut(edit.add_boundary(m, md.MATERIAL, ((0, 3), (10, 3))), "mat1").model
        assert {p.rule for p in md.problems(m)} == {"region_unassigned"}
        m = stages.assign_material(m, (5.0, 8.0), "m2")          # the old one, changed
        m = stages.assign_material(m, (5.0, 1.0), "m1")          # the new one
        assert [a.material for a in m.assignments] == ["m2", "m1"] and md.problems(m) == []


class TestRefused:
    def test_on_a_boundary_or_outside(self):
        _refused(lambda: stages.assign_material(_half_assigned(), (3.0, -4.0), "top"),
                 "assignment_outside")
        _refused(lambda: stages.assign_material(_half_assigned(), (30.0, -4.0), "top"),
                 "assignment_outside")
        # on an arc: the hole of the tunnel, at 0.6, 0.8
        _refused(lambda: stages.assign_material(_models.tunnel(), (0.6, 0.8), "rock"),
                 "assignment_outside")
        assert stages.assign_material(_models.tunnel(), (0.6, 0.7), "rock").assignments[1]             .material == "rock"

    def test_regions_that_cannot_be_found(self):
        m = edit.add_boundary(_half_assigned(), md.MATERIAL, ((5.0, -1.0), (5.0, -9.0)),
                              boundary_id="cross")
        _refused(lambda: stages.assign_material(m, (3.0, -7.0), "bottom"), "crossing")
        no_external = replace(_half_assigned(), boundaries=_half_assigned().boundaries[1:])
        _refused(lambda: stages.assign_material(no_external, (3.0, -7.0), "bottom"), "external")

    def test_a_region_with_two(self):
        m = _half_assigned()
        m = replace(m, assignments=m.assignments + (md.Assignment((3.0, -1.0), "top", (False,)),))
        _refused(lambda: stages.assign_material(m, (8.0, -1.0), "bottom"), "region_twice")
