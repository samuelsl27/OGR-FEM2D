# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The live bridge between the MCP server and an open window (spec 006, T34;
D8), on the core's protocol (``ogr_core.api.bridge``): what names this
program's bridge, so that an OGR Slip2D window and an OGR FEM2D one never
attach to each other's server.

The window serves it (``gui/agent_bridge.py``); the MCP server routes every
call to the window when one answers (``WindowRouter``), and works on its
own models otherwise.

No Qt here.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.api.bridge import BridgeConfig

CONFIG = BridgeConfig("ogr-fem2d-bridge/1", "OGR FEM2D", ".ogr-fem2d",
                      menu="Tools > Agent Bridge (MCP)",
                      summary_op="project_summary", list_op="project_list")
