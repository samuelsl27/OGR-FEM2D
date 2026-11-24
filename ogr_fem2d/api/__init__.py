# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The operations of OGR FEM2D, without Qt (spec 006, part B; ADR-0005).

Every action on a model is an operation with a name, typed arguments and a
JSON-safe answer, on the core's framework (``ogr_core.api``): the
interface, the command line and the MCP server call them through
``call(ws, name, **kwargs)`` and none of them knows who calls (RF-6).

    from ogr_fem2d import api

    ws = api.workspace(workdir="proyectos")
    pid = api.call(ws, "project_new", name="Túnel")["project_id"]

This package does not import Qt, the interface or the MCP SDK.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import inspect

from ogr_core.api import unknown

from .messages import say
from .registry import OPERATIONS
from .workspace import make as workspace


def check_arguments(name: str, kwargs) -> None:
    """An argument the operation ``name`` does not take is refused by its
    name, with the closest ones it takes (RF-7)."""
    op = OPERATIONS.get(name)
    if op is not None:
        params = inspect.signature(op.func).parameters
        takes = [p for p in params if p != "ws"]
        for key in kwargs:
            if key not in params or key == "ws":
                raise unknown(say("fem.argument.of", op=name), key, takes)


def call(ws, name: str, /, **kwargs):
    """Run the operation ``name`` on ``ws``, refusing an argument it does
    not take (``check_arguments``). The interface, the command line and the
    MCP server all call through here, so none of them passes on a name
    nobody reads."""
    check_arguments(name, kwargs)
    return OPERATIONS.call(ws, name, **kwargs)


from . import ops  # noqa: E402,F401  (registers the operations)

__all__ = ["OPERATIONS", "call", "workspace"]
