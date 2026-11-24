# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The registry of the operations of OGR FEM2D (spec 006, RF-6): one, on the
core's ``Registry`` (ADR-0005). The modules of ``ops`` register into it; the
interface, the command line and the MCP server call through it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.api import Registry

OPERATIONS = Registry()
