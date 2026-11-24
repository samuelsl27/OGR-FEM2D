# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
``python -m ogr_fem2d.mcp --workdir <folder>``: the MCP server over standard
input and output, on the models of that folder (spec 006, T16).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="ogr-fem2d-mcp",
                                description="The MCP server of OGR FEM2D, over stdio.")
    p.add_argument("--workdir", default=".", help="the folder relative paths mean")
    ns = p.parse_args(argv)
    from .. import api
    from .server import build_server
    ws = api.workspace(workdir=Path(ns.workdir).resolve())
    try:
        build_server(ws).run("stdio")
    finally:
        ws.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
