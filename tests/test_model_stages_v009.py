# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.9 (spec 004, T3) — the stages of a model and the edits that depend on
them (RF-3, RF-4, D10).

Invariants protected:

* **a stage inserted copies the one before it** (D10, own proposal), or the
  first one when it goes in front: the excavated flags, the active flags of
  the restraints, the factors of the imposed displacements and of the loads;
  its id is new and its place is the one asked;
* **deleting a stage takes its column away** from every table, and the
  only stage cannot be deleted; renaming changes only the name;
* **an edit in stage k writes stages k to N, or k alone** with "this stage
  only" (P20, D03 §2 of the interface analysis), for excavation, conditions
  and loads;
* **RF-4**: excavating a region in one stage only, before a later stage,
  makes it come back, and is refused; a material other than the region's in
  a later stage, or in one stage only of several, is refused; in the first
  stage of all it changes the region's material;
* **an edit never changes the model it was given** (the model is a value).
"""
from __future__ import annotations

from dataclasses import replace

import _models
from ogr_fem2d.model import model as md
from ogr_fem2d.model import stages

S = _models.strip()
DISP = md.Condition(md.DISPLACEMENT, md.Span("ext", (0.0, 0.0), (0.0, -20.0)), ux=0.01,
                    factors=(0.5,), name="Empuje")


def _three():
    """The strip with an imposed displacement, three stages whose tables
    differ from stage to stage."""
    m = replace(S, conditions=S.conditions + (DISP,))
    m = stages.insert_stage(m, 1, "2", "Dos")
    m = stages.insert_stage(m, 2, "3", "Tres")
    m = stages.set_load_factor(m, 0, "2", 2.0)
    m = stages.set_load_factor(m, 0, "3", 3.0)
    m = stages.set_condition_factor(m, 3, "3", None)
    m = stages.set_condition_active(m, 1, "2", False, this_stage_only=True)
    return m


class TestInsertDeleteRename:
    def test_the_tables_of_three_stages(self):
        m = _three()
        assert [s.id for s in m.stages] == ["1", "2", "3"]
        assert m.loads[0].factors == (1.0, 2.0, 3.0)
        assert m.conditions[3].factors == (0.5, 0.5, None)
        assert m.conditions[1].active == (True, False, True)

    def test_an_inserted_stage_copies_the_one_before_it(self):
        m = stages.insert_stage(_three(), 2, "2b", "Entre")
        assert [s.id for s in m.stages] == ["1", "2", "2b", "3"]
        assert m.loads[0].factors == (1.0, 2.0, 2.0, 3.0)
        assert m.conditions[1].active == (True, False, False, True)
        assert m.conditions[3].factors == (0.5, 0.5, 0.5, None)

    def test_in_front_it_copies_the_first(self):
        m = stages.insert_stage(_three(), 0, "0", "Inicio")
        assert [s.id for s in m.stages] == ["0", "1", "2", "3"]
        assert m.loads[0].factors == (1.0, 1.0, 2.0, 3.0)

    def test_at_the_end_it_copies_the_last(self):
        m = stages.insert_stage(_three(), 3, "4", "Cuatro")
        assert m.loads[0].factors == (1.0, 2.0, 3.0, 3.0)
        assert m.conditions[3].factors == (0.5, 0.5, None, None)

    def test_an_id_already_there_is_refused(self):
        try:
            stages.insert_stage(_three(), 1, "3")
        except md.ModelError as err:
            assert err.problems[0].rule == "stage"
        else:
            raise AssertionError("a repeated stage id was accepted")

    def test_delete_takes_the_column_away(self):
        m = stages.delete_stage(_three(), "2")
        assert [s.id for s in m.stages] == ["1", "3"]
        assert m.loads[0].factors == (1.0, 3.0)
        assert m.conditions[1].active == (True, True)
        assert m.assignments[0].excavated == (False, False)

    def test_the_only_stage_stays(self):
        try:
            stages.delete_stage(S, "1")
        except md.ModelError as err:
            assert "only stage" in err.problems[0].message
        else:
            raise AssertionError("the only stage was deleted")

    def test_rename_changes_the_name_only(self):
        m = _three()
        r = stages.rename_stage(m, "2", "Excavación")
        assert r.stages[1] == md.Stage("2", "Excavación") and replace(r, stages=m.stages) == m


class TestPropagation:
    def test_from_k_on_or_in_k_alone(self):
        m = _three()
        on = stages.set_load_factor(m, 0, "2", 9.0)
        only = stages.set_load_factor(m, 0, "2", 9.0, this_stage_only=True)
        assert on.loads[0].factors == (1.0, 9.0, 9.0)
        assert only.loads[0].factors == (1.0, 9.0, 3.0)

    def test_excavation_from_k_on(self):
        t = _models.with_stages(_models.tunnel(), 3)
        t = replace(t, assignments=(t.assignments[0], replace(t.assignments[1],
                                                             excavated=(False, False, False))))
        m = stages.set_excavated(t, (0.0, 0.0), "2", True)
        assert m.assignments[1].excavated == (False, True, True)
        assert stages.set_excavated(m, (0.0, 0.0), "3", True, this_stage_only=True) == m

    def test_the_model_given_is_not_changed(self):
        m = _three()
        before = repr(m)
        stages.set_load_factor(m, 0, "1", 7.0)
        stages.insert_stage(m, 0, "x")
        assert repr(m) == before


class TestRF4:
    def _tunnel(self):
        t = _models.with_stages(_models.tunnel(), 3)
        return replace(t, assignments=(t.assignments[0], replace(t.assignments[1],
                                                                excavated=(False, False, False))))

    def test_excavating_in_one_stage_only_makes_it_come_back(self):
        try:
            stages.set_excavated(self._tunnel(), (0.0, 0.0), "2", True, this_stage_only=True)
        except md.ModelError as err:
            assert err.problems[0].rule == "reactivated"
        else:
            raise AssertionError("an excavated region came back")

    def test_filling_an_excavation_is_refused(self):
        m = stages.set_excavated(self._tunnel(), (0.0, 0.0), "2", True)
        try:
            stages.set_excavated(m, (0.0, 0.0), "3", False)
        except md.ModelError as err:
            assert err.problems[0].rule == "reactivated"
        else:
            raise AssertionError("a filled excavation was accepted")

    def test_a_change_of_material_between_stages_is_refused(self):
        m = replace(self._tunnel(), materials=(md.Material("rock", "Roca", 1e7, 0.2),
                                               md.Material("soft", "Blanda", 1e6, 0.3)))
        for kwargs in ({"stage_id": "2"}, {"stage_id": "1", "this_stage_only": True}):
            try:
                stages.assign_material(m, (5.0, 0.0), "soft", **kwargs)
            except md.ModelError as err:
                assert err.problems[0].rule == "material_change", kwargs
            else:
                raise AssertionError(f"a change of material in a stage was accepted: {kwargs}")
        first = stages.assign_material(m, (5.0, 0.0), "soft", "1")
        assert first.assignments[0].material == "soft"
        assert stages.assign_material(m, (5.0, 0.0), "rock", "3") == m        # the same material

    def test_a_region_without_an_assignment_gets_one(self):
        t = _models.tunnel()
        bare = replace(t, assignments=t.assignments[:1])
        m = stages.assign_material(bare, (0.5, 0.0), "rock")
        assert m.assignments[1] == md.Assignment((0.5, 0.0), "rock", (False,))
        assert md.problems(m) == []
