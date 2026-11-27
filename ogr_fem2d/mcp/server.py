# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The MCP server of OGR FEM2D (spec 006, T16; D1): one tool per operation of
``ogr_fem2d.api``, so an agent builds, meshes, calculates and reads a model
with the same operations as the interface and the command line (H5).

The tools are made FROM the registry, not written by hand (OGR Slip2D
writes them by hand, for their descriptions): each tool takes the
operation's own parameters, with their types, and its description is the
operation's docstring. So the two cannot drift, and a test checks that the
tools are exactly the operations. A tool that edits a model, writes a file
or stops a process says so in its annotations (not read-only); one that
only reads, read-only.

Errors: an ``OgrApiError`` comes back as a ``ToolError`` with its coded
text (``[E_NOT_FOUND] Unknown … Did you mean …? Hint: …``), which is what
lets an agent recover; anything else as ``[E_INTERNAL]`` with its type.

Over standard input and output, on models in a working folder, without
OAuth (D1): ``python -m ogr_fem2d.mcp --workdir <folder>``.

**The live bridge (D8, spec 006 T34)**: when an OGR FEM2D window has Tools >
Agent Bridge (MCP) on, every call goes to that window (the core's
``WindowRouter``), where it is drawn and undone with Edit > Undo; a call
that names a model or a job of the server's own stays with it; without a
window, the server works on its own models. ``--attach`` works only on a
window, and says what to open when there is none.

This module imports the SDK (the extra ``[mcp]``); ``ogr_fem2d.api`` does
not.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import inspect
import typing
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from ogr_core.api import OgrApiError

import ogr_fem2d
from .. import api

INSTRUCTIONS = """OGR FEM2D: 2-D geotechnical analysis by finite elements (elastic in this
version): plane strain or axisymmetry, construction stages, field stress.
Units are those the model keeps whatever it shows: m, kN, kPa, kN/m3, degrees;
x to the right, y up. Field stress is compression positive; a normal load is
positive into the ground; the results come compression positive.
Workflow: project_new (or project_open a .ogrfem2d, a .ogr of OGR Slip2D, a .dxf)
-> boundary_add / boundary_circle (an external one, excavations, materials,
stages; cuts with the others become vertices) -> material_set (E and nu have no
default) -> material_assign at a point of each region -> field_set ->
condition_set, load_set -> mesh_settings (a graded mesh needs boundary_nodes)
-> mesh_generate -> project_save -> analysis_run (wait seconds, or job_get) ->
results_open -> results_query / results_summary / results_report.
project_validate says why a model cannot be calculated. Every edit is one step
of project_history. Results that are not valid (stale, incomplete) are read only
with allow_invalid=true, and then every answer says their state."""


#: the operations that edit no model but write a file or stop a process:
#: not read-only for an agent either
WRITES = ("project_save", "project_close", "analysis_run", "job_cancel", "results_table",
          "results_report")


def _wrapper(name: str, op, run):
    """A function with the operation's parameters (``ws`` out) that calls
    it by name, for the SDK to read its schema from."""
    hints = typing.get_type_hints(op.func)
    params = [p.replace(annotation=hints.get(p.name, Any))
              for p in inspect.signature(op.func).parameters.values() if p.name != "ws"]

    def tool(**kwargs):
        return run(name, **kwargs)

    tool.__name__ = name
    tool.__doc__ = op.func.__doc__
    tool.__signature__ = inspect.Signature(params, return_annotation=dict)
    tool.__annotations__ = {p.name: p.annotation for p in params} | {"return": dict}
    return tool


class _Server(MCPServer):
    """The SDK checks the arguments of a tool against its schema, and
    drops a name it does not know without a word: an agent that misspelled
    ``name`` would get a model without one. Here such a name is refused, as
    ``api.call`` refuses it (RF-7)."""

    async def call_tool(self, name, arguments, context=None):
        try:
            api.check_arguments(name, arguments or {})
        except OgrApiError as err:
            raise ToolError(str(err)) from None
        return await super().call_tool(name, arguments, context)


def build_server(ws, only_window: bool = False, router=None) -> MCPServer:
    """An ``MCPServer`` with one tool per operation, over ``ws``; each call
    to the open window when there is one (``router``, by default the core's
    ``WindowRouter`` with this program's bridge)."""
    if router is None:
        from ogr_core.api.bridge import WindowRouter
        from ..api.bridge import CONFIG
        router = WindowRouter(CONFIG, ws, local_call=api.call, only_window=only_window)
    srv = _Server("ogr-fem2d", title="OGR FEM2D",
                    description="2-D geotechnical finite-element analysis: build, mesh, "
                                "calculate and read models.",
                    instructions=INSTRUCTIONS, version=ogr_fem2d.__version__)

    def run(op_name: str, /, **kwargs) -> dict:
        kwargs = {k: v for k, v in kwargs.items()}
        try:
            return router.call(op_name, **kwargs)
        except ToolError:
            raise
        except OgrApiError as err:
            raise ToolError(str(err)) from None
        except Exception as err:  # noqa: BLE001 - said to the agent, with its type
            raise ToolError(f"[E_INTERNAL] {type(err).__name__}: {err}") from None

    names = []
    for name, op in api.OPERATIONS.items():
        reads = not op.mutates and name not in WRITES
        ann = ToolAnnotations(readOnlyHint=reads, destructiveHint=False)
        doc = inspect.cleandoc(op.func.__doc__ or name)
        srv.tool(name=name, description=doc, annotations=ann)(_wrapper(name, op, run))
        names.append(name)
    srv._fem_tools = tuple(names)
    srv._fem_router = router
    return srv
