# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The lengths the window shows and reads, in the model's unit system (spec
006, T23; spec 004, D5).

The model keeps its values in m, kN, kPa and kN/m³ whatever system it shows;
the system changes only what is shown and how what is typed is read. This
is the one place of the window where a length crosses between the two: the
cursor's coordinates, a typed point, the table of coordinates and the
grid's spacing go through it, so that choosing feet shows feet and a point
typed in feet lands where it says.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.units import Quantity as Q
from ogr_core.units.unit_system import get_system

from ..model import model as md


def system(m: md.Model | None):
    return get_system(md.DEFAULT_UNITS if m is None else m.units)


def length_factor(m: md.Model | None) -> float:
    """The units shown in one metre (3.28… in feet)."""
    return system(m).to_user(1.0, Q.LENGTH)


def length_label(m: md.Model | None) -> str:
    return system(m).label_for(Q.LENGTH)


def to_user(m: md.Model | None, p) -> tuple[float, float]:
    """A point in metres, in the units shown."""
    s = system(m)
    return s.to_user(p[0], Q.LENGTH), s.to_user(p[1], Q.LENGTH)


def from_user(m: md.Model | None, p) -> tuple[float, float]:
    """A point in the units shown, in metres."""
    s = system(m)
    return s.from_user(p[0], Q.LENGTH), s.from_user(p[1], Q.LENGTH)
