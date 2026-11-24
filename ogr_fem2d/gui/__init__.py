# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The interface of OGR FEM2D (spec 006, parts C and D), with PySide6 and the
pieces of the suite (``ogr_ui``, ADR-0005). The only package of this
program that imports Qt; it edits a model only through the operations of
``ogr_fem2d.api`` (``session.Session``).

Author: Samuel Sáez López (UPCT)
"""
