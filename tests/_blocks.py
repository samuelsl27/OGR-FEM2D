# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A rectangular block of triangles for the tests of spec 002 (not a test file:
the runner only collects test_*.py). Not the mesher of spec 003: the
simplest mesh on which a linear field is exact.

block(six, nx, ny, w, h, x0) cuts each of nx x ny rectangles of the block
[x0, x0 + w] x [0, h] by its diagonal from bottom left to top right into two
anticlockwise triangles, with mid-side nodes for six-node triangles (side k
from corner k to k + 1, mid-side node k + 3).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Block:
    nodes: list[tuple[float, float]]
    elements: list[tuple[int, ...]]
    columns: int                       # nodes per row
    rows: int
    six: bool

    def at(self, i: int, j: int) -> int:
        return j * self.columns + i

    def left(self) -> list[int]:
        return [self.at(0, j) for j in range(self.rows)]

    def bottom(self) -> list[int]:
        return [self.at(i, 0) for i in range(self.columns)]

    def top_edges(self) -> list[tuple[int, ...]]:
        """The sides on the top, left to right: (first, second) corners, and
        for six nodes (first, mid, second)."""
        step = 2 if self.six else 1
        j = self.rows - 1
        if self.six:
            return [(self.at(i, j), self.at(i + 1, j), self.at(i + 2, j))
                    for i in range(0, self.columns - 1, step)]
        return [(self.at(i, j), self.at(i + 1, j)) for i in range(self.columns - 1)]


def block(six: bool, nx: int = 3, ny: int = 2, w: float = 2.0, h: float = 1.5,
          x0: float = 0.0) -> Block:
    step = 2 if six else 1
    cols, rows = nx * step + 1, ny * step + 1
    nodes = [(x0 + w * i / (cols - 1), h * j / (rows - 1))
             for j in range(rows) for i in range(cols)]
    at = lambda i, j: j * cols + i
    elements = []
    for j in range(0, rows - 1, step):
        for i in range(0, cols - 1, step):
            a, b = at(i, j), at(i + step, j)
            c, d = at(i + step, j + step), at(i, j + step)
            if six:
                mab, mbc = at(i + 1, j), at(i + 2, j + 1)
                mcd, mda, mac = at(i + 1, j + 2), at(i, j + 1), at(i + 1, j + 1)
                elements += [(a, b, c, mab, mbc, mac), (a, c, d, mac, mcd, mda)]
            else:
                elements += [(a, b, c), (a, c, d)]
    return Block(nodes, elements, cols, rows, six)
