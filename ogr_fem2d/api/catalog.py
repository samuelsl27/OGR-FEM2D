# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The catalogue of the operations, written from the registry (spec 006,
T18): ``docs/operaciones/catalogo.md`` is this text, and a test keeps them
the same, so the page cannot fall behind the code.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import inspect
import typing

from .registry import OPERATIONS

HEADER = """# Catálogo de operaciones

> Spec 006, parte B (RF-6, RF-7). Escrito desde el registro (`ogr_fem2d/api/catalog.py`): un test
> comprueba que esta página es la del código. Las descripciones son las de cada operación, en
> inglés, como las ve un agente por el servidor MCP.

Cada operación se llama igual desde Python (`api.call(ws, nombre, **argumentos)`), la línea de
órdenes (`python -m ogr_fem2d.cli call nombre --json '{…}'`) y el servidor MCP (una herramienta por
operación). Un argumento que no existe se rechaza por su nombre. Los valores van en m, kN, kPa y kN/m³;
la tensión de campo y los resultados, en compresión positiva. «Edita» quiere decir que es un paso de
deshacer (`project_history`).
"""


def _type(hint) -> str:
    """``str``, ``float o None``, ``list o None``…"""
    args = typing.get_args(hint)
    if args:
        return " o ".join(_type(a) for a in args)     # a | would split the table
    if hint is type(None):
        return "None"
    if hint is typing.Any:
        return "any"
    return getattr(hint, "__name__", None) or str(hint).replace("typing.", "")


def markdown() -> str:
    out = [HEADER]
    by_set: dict[str, list] = {}
    for name, op in OPERATIONS.items():
        by_set.setdefault(op.toolset, []).append((name, op))
    for toolset in sorted(by_set):
        out.append(f"## {toolset}\n")
        for name, op in sorted(by_set[toolset]):
            hints = typing.get_type_hints(op.func)
            doc = inspect.cleandoc(op.func.__doc__ or "")
            out.append(f"### `{name}`{' (edita)' if op.mutates else ''}\n")
            out.append(doc + "\n")
            rows = []
            for p in inspect.signature(op.func).parameters.values():
                if p.name == "ws":
                    continue
                default = "obligatorio" if p.default is inspect.Parameter.empty else \
                    f"`{p.default!r}`"
                rows.append(f"| `{p.name}` | `{_type(hints.get(p.name, ''))}` | {default} |")
            if rows:
                out.append("| Argumento | Tipo | Por defecto |\n|---|---|---|\n" + "\n".join(rows) + "\n")
    return "\n".join(out)
