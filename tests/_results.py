# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Models calculated into a results file, for the tests of spec 005 (not a
test file: the runner only collects test_*.py).

* ``loaded_layers()``: the two strata of tests/_models.py (a contact at
  y = -4 m, the gravitational field with the self weight) with a uniform
  normal load of 100 kPa on the whole surface: the horizontal stress jumps
  at the contact, and the ground moves;
* ``excavated_tunnel(stages)``: the tunnel of tests/_models.py with its hole
  excavated from the second stage (or in the only one);
* ``calculated(model, directory)``: the model written to
  ``directory/modelo.ogrfem2d``, calculated, and its results opened (valid).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import _models
from ogr_fem2d.model import model as md
from ogr_fem2d.model import ogr_file
from ogr_fem2d.results import calculate as calc


def loaded_layers() -> md.Model:
    m = _models.layers()
    load = md.DistributedLoad(md.Span("ext", (20.0, 0.0), (0.0, 0.0)), 100.0, 100.0, factors=(1.0,),
                              name="Sobrecarga")
    return _models.meshed(replace(m, loads=(load,)))


def excavated_tunnel(stages: int = 1) -> md.Model:
    m = _models.meshed(_models.with_stages(_models.tunnel(), stages))
    excavated = (True,) if stages == 1 else (False,) + (True,) * (stages - 1)
    return replace(m, assignments=(m.assignments[0], replace(m.assignments[1], excavated=excavated)))


def calculated(m: md.Model, directory) -> calc.Opened:
    path = Path(directory) / "modelo.ogrfem2d"
    ogr_file.write(m, path)
    calc.calculate(m, path)
    opened = calc.open_results(path, m)
    assert opened.status == calc.VALID, opened
    return opened.results
