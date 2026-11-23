# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.9 (spec 004, T18) — every value that decides the result and was not
drawn, listed (rule 12).

Invariants protected:

* **the list says what the model and the translation used**: the default
  restraint, the initial loading of each material, every mesh setting, and
  the solver settings, which are the engine's defaults the translation puts
  in every stage (D9), as the engine input shows;
* **the convention of a point load in axisymmetry is said** when there is
  one (spec 002, D2);
* **the unit system shown is said not to change the values** (D5).

Rule 7, for every setting of the model, is in the tests of T1 to T14 (the
table is in the changelog v0.0.9, T18).
"""
from __future__ import annotations

from dataclasses import replace

import _models
from ogr_fem2d.model import model as md
from ogr_fem2d.model import translate


def _as_dict(m):
    return {what: value for what, value, _why in translate.deciding_values(m)}


class TestTheList:
    def test_what_the_model_and_the_translation_used(self):
        m = translate.mesh(_models.layers())
        values = _as_dict(m)
        assert values["default_restraint"] == m.default_restraint
        assert values["material 'top': initial_loading"] == md.FIELD_AND_BODY
        assert values["mesh: boundary_nodes"] == 60 and values["mesh: nodes_per_element"] == 6
        stage = translate.to_engine(m).stages[0]
        assert (values["solver: steps"], values["solver: tolerance"], values["solver: max_iterations"],
                values["solver: max_cuts"]) == (stage.steps, stage.tolerance, stage.max_iterations,
                                                 stage.max_cuts)

    def test_it_follows_the_model(self):
        m = replace(_models.strip(), default_restraint=md.Y)
        assert _as_dict(m)["default_restraint"] == md.Y

    def test_the_ring_in_axisymmetry(self):
        s = _models.strip()
        assert "point loads" not in _as_dict(replace(s, analysis=md.AXISYMMETRIC))
        m = replace(s, analysis=md.AXISYMMETRIC,
                    loads=(md.PointLoad((1.0, 0.0), 1.0, factors=(1.0,)),))
        assert _as_dict(m)["point loads"] == "the force of the whole ring"

    def test_the_units_shown(self):
        whys = {what: why for what, _v, why in translate.deciding_values(replace(_models.strip(),
                                                                                    units="metric_mpa"))}
        assert "'metric_mpa' is only what is shown" in whys["units"]
