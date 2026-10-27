# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The finite-element engine.

It knows nothing of the interface (rule 11 of ``AGENTS.md``): it takes nodes,
elements, properties, initial stresses, restraints and stages, and returns
fields. Inside it, stresses are tension-positive, and the loads and imposed
displacements of a stage are totals (rule 10; spec 001, D1 and D2).

``reference`` is the readable Python implementation of every element and
material law: the oracle the compiled core is tested against (ADR-0001).

Author: Samuel Sáez López (UPCT)
"""
