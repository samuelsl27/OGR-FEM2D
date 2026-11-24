# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.13 (spec 006, T16) — the MCP server (RF-6; D1, D14).

Invariants protected:

* **the tools are exactly the operations**: one per operation of
  ``ogr_fem2d.api``, none more, with the operation's own parameters (the
  required ones required) and its docstring for a description;
* **an agent is told what a tool does to its world**: a tool that edits a
  model, writes a file or stops a process is not read-only, and the others
  are;
* **a tool is its operation**: what it answers is what the operation
  answers; an error comes back as an error with its code and hint;
* **nothing unknown is taken in silence** (RF-7): the SDK drops an argument
  it does not know without a word, and here it is refused by name.
"""
from __future__ import annotations

import inspect
import json

import importlib.util

from ogr_core.testing.leaks import root_logging_kept

from ogr_fem2d import api

#: The SDK is the extra [mcp]; without it (the CI installs the wheel without
#: extras until it is told otherwise) these tests say they cannot run here.
HAVE_MCP = importlib.util.find_spec("mcp") is not None
if HAVE_MCP:
    import anyio
    from mcp import Client
    from ogr_fem2d.mcp import server


def _server():
    if not HAVE_MCP:
        import pytest
        pytest.skip("the MCP SDK (the extra [mcp]) is not installed here")
    ws = api.workspace()
    with root_logging_kept():
        return ws, server.build_server(ws)


def _ask(srv, fn):
    async def go():
        async with Client(srv) as c:
            return await fn(c)
    with root_logging_kept():
        return anyio.run(go)


class TestTheTools:
    def test_exactly_the_operations_with_their_parameters(self):
        ws, srv = _server()
        try:
            tools = _ask(srv, lambda c: c.list_tools())
            by_name = {t.name: t for t in tools.tools}
            assert set(by_name) == set(api.OPERATIONS)
            for name, op in api.OPERATIONS.items():
                params = [p for p in inspect.signature(op.func).parameters.values()
                          if p.name != "ws"]
                schema = by_name[name].input_schema
                assert list(schema["properties"]) == [p.name for p in params], name
                required = {p.name for p in params if p.default is inspect.Parameter.empty}
                assert set(schema.get("required", [])) == required, name
                assert by_name[name].description == inspect.cleandoc(op.func.__doc__), name
                writes = op.mutates or name in server.WRITES
                assert by_name[name].annotations.read_only_hint is (not writes), name
        finally:
            ws.shutdown()


class TestATool:
    def test_is_its_operation(self):
        ws, srv = _server()
        try:
            async def scenario(c):
                made = await c.call_tool("project_new", {"name": "Túnel"})
                settings = await c.call_tool("project_settings", {"units": "metric_mpa"})
                bad = await c.call_tool("project_new", {"analysis": "3d"})
                misspelled = await c.call_tool("project_new", {"nmae": "x"})
                return made, settings, bad, misspelled
            made, settings, bad, misspelled = _ask(srv, scenario)
            got = json.loads(made.content[0].text)
            assert got["name"] == "Túnel" and got["project_id"] in ws.projects
            assert json.loads(settings.content[0].text)["units"] == "metric_mpa"
            assert ws.get(got["project_id"]).project.model.units == "metric_mpa"
            assert bad.is_error and "[E_NOT_FOUND]" in bad.content[0].text
            assert "plane_strain" in bad.content[0].text
            assert misspelled.is_error and "'nmae'" in misspelled.content[0].text
            assert "Did you mean 'name'" in misspelled.content[0].text
            assert len(ws.projects) == 1                   # the misspelled one made nothing
        finally:
            ws.shutdown()
