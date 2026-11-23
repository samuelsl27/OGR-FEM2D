# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The one place where the model's signs become the engine's (spec 004, RF-8,
D6; rule 10 of AGENTS.md).

The model, and its file, keep the user's convention:

* the field stress, COMPRESSION POSITIVE (the geotechnical custom);
* a NORMAL load, positive when it pushes into the ground (D08 of the
  interface analysis: "empuja hacia el interior");
* the other orientations of a load, positive along the core's direction
  (``ogr_core.loads.DistributedLoad.direction_vector``): a force, as the
  engine's;
* displacements along +x and +y, as the engine's.

The engine is TENSION POSITIVE, and its normal traction on a side is
positive outward of the element, a pull (docs/motor/entrada.md). So two
things change sign, here and nowhere else: the field stress (through
``engine.initial_stress``, which takes compression positive and gives the
engine's, spec 002) and the normal load.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ..engine import initial_stress as ini
from ..engine.model import EngineModel
from . import model as md

Stress = tuple[float, float, float, float]


def field_stresses(base: EngineModel, f: md.ConstantField | md.GravityField
                   ) -> tuple[Stress, ...]:
    """The field at every integration point of ``base``, the engine's sign
    (tension positive), from the model's (compression positive)."""
    if isinstance(f, md.ConstantField):
        return ini.constant_field(base, f.sigma_1, f.sigma_3, f.sigma_z, f.angle)
    return ini.gravitational_field(base, f.surface, list(f.strata))


def engine_normal(value: float) -> float:
    """The engine's normal traction (outward of the element, a pull) of a
    model's normal load (into the ground, a push)."""
    return -value
