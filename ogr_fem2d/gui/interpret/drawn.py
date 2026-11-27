# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A field as the canvas draws it (spec 006, T31; D11, D15): the bands of
colour and the iso-lines of ``results_field``'s triangles, as polygons in
model coordinates. No Qt here.

* **The colours are the settings'**: the bands are ``settings.levels()``
  and each is painted with ``settings.band_colours()``, the same function
  the legend paints with, so the two cannot disagree (guide §6). A value
  outside the range takes the colour of its end, as ``ContourSettings``
  does (a narrow range still shows the whole model).
* **Material by material**: ``results_field`` gives every element its own
  vertices, so that two materials never mix (D11). Here the vertices of
  ONE material at one place are merged, so the bands of a material are
  whole polygons and not one per element: with the mesh of case 005 that
  takes the contouring from 0.59 s to 0.33 s and the polygons from 371 111
  vertices to 20 502, which the canvas then fills at once at any zoom. Two
  materials keep their own vertices, so the bands still break between
  them.
* **The contouring** is matplotlib's (``tricontourf``, ``tricontour``), on
  the linear subtriangles: the drawing is an image, not a number (D11); a
  value is read with the query, not off the colours.
* **A smooth gradient** is drawn as ``SMOOTH_BANDS`` thin bands, each with
  the colour ``settings.colour_for`` gives its centre: a vector canvas has
  no gradient over a triangle, and at that count the steps are not seen.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from ogr_ui.contours import ContourMode, ContourSettings

SMOOTH_BANDS = 96
#: places closer than this (m) are one place, for merging the vertices of a material
MERGE_DECIMALS = 9


@dataclass(frozen=True)
class Drawn:
    """What the canvas paints: per band its colour and its rings (each an
    (N, 2) array, closed), and the iso-lines as polylines."""
    bands: tuple                    # ((colour, (ring, ...)), ...)
    lines: tuple                    # (polyline, ...)
    vertices: int                   # how many, of the bands' rings


def merging(xy, triangles, material):
    """ONE vertex per (material, place): the vertices kept (their indices)
    and the triangles on them. It depends only on the mesh drawn, so the
    window works it out once per stage and level (0.48 s with case 005)."""
    xy = np.asarray(xy, dtype=float)
    tris = np.asarray(triangles, dtype=np.int64)
    vmat = np.zeros(len(xy), dtype=np.int64)
    vmat[tris.ravel()] = np.repeat(np.asarray(material, dtype=np.int64), 3)
    # one number per (material, place), sorted once: the material and x as
    # the real part (the material in steps wider than the model), y as the
    # imaginary one (np.unique of rows took 0.57 s with case 005)
    x = np.round(xy[:, 0], MERGE_DECIMALS)
    y = np.round(xy[:, 1], MERGE_DECIMALS)
    width = 4.0 * (float(np.abs(x).max()) + 1.0) if len(x) else 1.0
    key = (x + vmat * width) + 1j * y
    _u, first, inverse = np.unique(key, return_index=True, return_inverse=True)
    return first, inverse.ravel()[tris]


def merged(xy, triangles, values, material, merge=None):
    """The triangles with ONE vertex per (material, place); the values of
    the vertices merged are the same (the recovery is continuous within a
    material, 005 D5), the first is kept. ``merge`` is ``merging``'s, if
    already worked out."""
    first, tris = merging(xy, triangles, material) if merge is None else merge
    return np.asarray(xy, dtype=float)[first], tris, np.asarray(values, dtype=float)[first]


def _rings(path) -> list:
    """The closed rings of a matplotlib path."""
    from matplotlib.path import Path
    out, ring = [], []
    for (x, y), code in zip(path.vertices, path.codes if path.codes is not None
                            else [Path.LINETO] * len(path.vertices)):
        if code == Path.MOVETO:
            if len(ring) > 2:
                out.append(np.array(ring))
            ring = [(x, y)]
        elif code == Path.CLOSEPOLY:
            if len(ring) > 2:
                out.append(np.array(ring))
            ring = []
        else:
            ring.append((x, y))
    if len(ring) > 2:
        out.append(np.array(ring))
    return out


def _polylines(path) -> list:
    from matplotlib.path import Path
    out, line = [], []
    codes = path.codes if path.codes is not None else [Path.LINETO] * len(path.vertices)
    for (x, y), code in zip(path.vertices, codes):
        if code == Path.MOVETO and line:
            if len(line) > 1:
                out.append(np.array(line))
            line = []
        if code != Path.CLOSEPOLY:
            line.append((x, y))
    if len(line) > 1:
        out.append(np.array(line))
    return out


def draw(xy, triangles, values, material, settings: ContourSettings, merge=None) -> Drawn:
    """The bands and the lines of a field with ``settings`` (its mode, its
    range, its intervals, its palette); ``merge``, ``merging``'s."""
    if settings.mode == ContourMode.OFF:
        return Drawn((), (), 0)
    from matplotlib.figure import Figure
    from matplotlib.tri import Triangulation
    pxy, ptris, pv = merged(xy, triangles, values, material, merge)
    bad = ~np.isfinite(pv)
    tri = Triangulation(pxy[:, 0], pxy[:, 1], ptris,
                        mask=bad[ptris].any(axis=1) if bad.any() else None)
    pv = np.where(bad, settings.vmin, pv)
    lo, hi = settings.vmin, settings.vmin + settings.span
    # a value outside the range takes its end's colour; matplotlib leaves a
    # value ON the top level unfilled, so the top is a hair below it
    clipped = np.clip(pv, lo, hi - 1e-9 * settings.span)
    ax = Figure().add_subplot()
    bands, lines, n = [], [], 0
    if settings.mode in (ContourMode.FILLED, ContourMode.FILLED_LINES, ContourMode.SMOOTH):
        fill = settings if settings.mode != ContourMode.SMOOTH else \
            replace(settings, intervals=SMOOTH_BANDS)
        levels = fill.levels()
        colours = ([settings.colour_for(lo + fill.span * (k + 0.5) / SMOOTH_BANDS)
                    for k in range(SMOOTH_BANDS)] if settings.mode == ContourMode.SMOOTH
                   else fill.band_colours())
        cs = ax.tricontourf(tri, clipped, levels=levels)
        for colour, path in zip(colours, cs.get_paths()):
            rings = _rings(path)
            n += sum(len(r) for r in rings)
            if rings:
                bands.append((colour, tuple(rings)))
    if settings.mode in (ContourMode.LINES, ContourMode.FILLED_LINES):
        inner = settings.levels()[1:-1]
        if inner:
            cs = ax.tricontour(tri, clipped, levels=inner)
            for path in cs.get_paths():
                lines.extend(_polylines(path))
    return Drawn(tuple(bands), tuple(lines), n)
