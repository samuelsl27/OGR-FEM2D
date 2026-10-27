# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Reference implementation of the engine, in plain Python.

Written to be read: one function per step of the formulation, loops where the
source has sums, and the equation each one comes from in its docstring. It is
the oracle of the tests of the compiled core (ADR-0001), so it is validated
against closed-form solutions before it is used as one (spec 001, plan).

Author: Samuel Sáez López (UPCT)
"""
