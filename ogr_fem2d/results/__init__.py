# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The results of a calculation and their interpretation, without Qt (spec 005).

* ``quantities``: the catalogue of the field quantities, each with its
  definition and its source (D2, D3, D16);
* ``strains``: B u at every integration point (D6);
* ``store``: the results file, ``modelo.h5`` (D6, D13; ADR-0003);
* ``calculate``: calculate a model and write its results; open them, with
  their state (D7, D13);
* ``locate``, ``recovery``, ``queries`` and ``table``: the point in its
  element (D11), the values at the nodes (D5), the queries (D9, D12, D14)
  and the exported table (D15).

Author: Samuel Sáez López (UPCT)
"""
