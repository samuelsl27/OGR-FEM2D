# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The initial state of the engine from the model: the stress at every
integration point and the self weight of every material (spec 004, RF-7,
D11, D14).

The mode of initial loading of each material (D11; D03, P05 and M10 of the
interface analysis) says what its elements start with:

==========================  ==================  ===========
mode                        initial stress      self weight
==========================  ==================  ===========
field_stress                the field           none
field_stress_and_body_force the field           its gamma
body_force                  none                its gamma
none                        none                none
==========================  ==================  ===========

The field is the model's (constant, or gravitational with a horizontal
surface and horizontal strata, D14), taken to each point by the
preprocessors of spec 002 (``engine.initial_stress``: JCZ 2007 Eqs.
2.28-2.30, 13.1 and 13.5; in axisymmetry the field must be in radial
equilibrium, T&G 1951 Eq. 177), through ``conventions``, the one place of
the change of sign. A field that the preprocessor refuses is an error of the
model, rule ``field``. When no point starts with any stress, the engine gets
None (zero everywhere), not a list of zeros.

**A point on the bottom of a stratum takes the K of its element's stratum**
(found in T4). The preprocessor of spec 002 takes K and Kz from the stratum
the point's height falls in, and a point exactly on the bottom of a stratum
falls in the one above. With the strata on material boundaries, the mesh has
element sides on them, and the six-node triangle has integration points at
the middle of its sides (spec 002, D1): the element below got, at those
points, the K of the stratum above, a field not in equilibrium inside it, and
displacements of 2e-5 of their scale where there should be none. Here the
vertical stress is the column above the point, continuous (JCZ Eq. 13.1),
and K and Kz are those of the stratum that holds the element's centroid
(Eq. 13.5 per stratum: the horizontal stress jumps at the contact, and each
element has its side of the jump).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ..engine import initial_stress as ini
from ..engine.model import POINTS_PER_ELEMENT, EngineModel, Problem
from . import conventions
from . import model as md

WITH_FIELD = (md.FIELD_STRESS, md.FIELD_AND_BODY)
WITH_WEIGHT = (md.FIELD_AND_BODY, md.BODY_FORCE)


def unit_weight(material: md.Material) -> float:
    """The self weight the engine gets for a material (D11)."""
    return float(material.unit_weight) if material.initial_loading in WITH_WEIGHT else 0.0


def initial_stresses(m: md.Model, base: EngineModel):
    """The stress of every integration point of ``base`` (whose materials
    are those of ``m``, in its order), or None when every point starts at
    zero."""
    starts = [m.materials[k].initial_loading in WITH_FIELD for k in base.element_material]
    if not any(starts):
        return None
    try:
        field = conventions.field_stresses(base, m.field)
        if isinstance(m.field, md.GravityField):
            field = _per_element_stratum(base, m.field, field)
    except ini.InitialStressError as err:
        raise md.ModelError([Problem("field", "field stress", str(err))]) from None
    per = POINTS_PER_ELEMENT[(base.nodes_per_element, base.analysis)]
    zero = (0.0, 0.0, 0.0, 0.0)
    out = []
    for e, start in enumerate(starts):
        out.extend(field[e * per:(e + 1) * per] if start else (zero,) * per)
    if all(s == zero for s in out):
        return None
    return tuple(out)


def _stratum_of(y: float, f: md.GravityField):
    for s in f.strata:
        if y >= s.bottom:
            return s
    raise ini.InitialStressError(f"y = {y:.6g} is below the last stratum")


def _per_element_stratum(base: EngineModel, f: md.GravityField, field):
    """The gravitational field with K and Kz of the stratum of each
    element's centroid (see the module's notes); the vertical stress is the
    preprocessor's, the column above the point."""
    per = POINTS_PER_ELEMENT[(base.nodes_per_element, base.analysis)]
    out = []
    for e, element in enumerate(base.elements):
        corners = [base.nodes[n] for n in element[:3]]
        s = _stratum_of(sum(p[1] for p in corners) / 3.0, f)
        for sxx, syy, szz, txy in field[e * per:(e + 1) * per]:
            out.append((s.k * syy, syy, s.kz * syy, txy))
    return tuple(out)
