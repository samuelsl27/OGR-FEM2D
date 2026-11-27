# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The recovery as v0.0.14 wrote it (``ogr_fem2d/results/recovery.py`` at
76cadf5), kept for one test only: the recovery of v0.0.15 has the same fits
and the same sums in the same order with lighter bookkeeping, and the test
holds it to this one bit for bit (``test_results_recovery_v0015.py``).
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np

from ogr_fem2d.results.recovery import ELEMENT, NONE, SIDES, SPR, Recovered, fit


def recover(nodes, elements, element_material, active, points_xy, point_element,
            values) -> Recovered:
    """The values at the nodes of every active element, material by
    material, of ``values`` (P, c) at the integration points."""
    nodes = np.asarray(nodes, dtype=float)
    elements = np.asarray(elements, dtype=np.int64)
    material = np.asarray(element_material)
    active = np.asarray(active, dtype=bool)
    points_xy = np.asarray(points_xy, dtype=float)
    values = np.asarray(values, dtype=float)
    n_el, n_per = elements.shape
    degree = 2 if n_per == 6 else 1
    comps = values.shape[1]
    point_element = np.asarray(point_element)
    per = len(point_element) // n_el
    out = np.full((n_el, n_per, comps), np.nan)
    source = np.full((n_el, n_per), NONE, dtype=np.int8)
    notes = {"patches": 0, "patches_refused": 0, "nodes_by_element": 0}

    for mat in sorted(set(material[active].tolist())):
        zone = np.flatnonzero(active & (material == mat))
        # the sides of the zone, and those with one element: the boundary
        side_count: dict = defaultdict(int)
        for e in zone:
            for a, b, _m in SIDES:
                side_count[tuple(sorted((elements[e][a], elements[e][b])))] += 1
        boundary = set()
        for e in zone:
            for a, b, m in SIDES:
                if side_count[tuple(sorted((elements[e][a], elements[e][b])))] == 1:
                    boundary.update((int(elements[e][a]), int(elements[e][b])))
                    if n_per == 6:
                        boundary.add(int(elements[e][m]))
        around: dict = defaultdict(list)
        for e in zone:
            for a in range(3):
                around[int(elements[e][a])].append(int(e))
        total: dict = {}
        count: dict = defaultdict(int)

        def add(node, value):
            total[node] = total[node] + value if node in total else value.copy()
            count[node] += 1

        for centre_node in sorted(around):
            if centre_node in boundary:
                continue
            patch = around[centre_node]
            idx = np.concatenate([np.arange(e * per, (e + 1) * per) for e in patch])
            poly = fit(points_xy[idx], values[idx], degree, nodes[centre_node])
            if poly is None:
                notes["patches_refused"] += 1
                continue
            notes["patches"] += 1
            determined = {centre_node}
            for e in patch:
                local = list(elements[e][:3]).index(centre_node)
                if n_per == 6:
                    for a, b, m in SIDES:
                        if local in (a, b):
                            determined.add(int(elements[e][m]))
                determined.update(int(n) for n in elements[e] if int(n) in boundary)
            ordered = sorted(determined)
            got = poly(nodes[ordered])
            for node, value in zip(ordered, got):
                add(node, value)

        # the nodes no patch determined: the field of their own elements
        fallback: dict = {}
        for e in zone:
            missing = [a for a in range(n_per) if int(elements[e][a]) not in total]
            if not missing:
                continue
            idx = np.arange(e * per, (e + 1) * per)
            own = fit(points_xy[idx], values[idx], degree - 1, points_xy[idx].mean(axis=0))
            if own is None:                       # degree - 1 = 0 or 1 always fits here
                own = fit(points_xy[idx], values[idx], 0, points_xy[idx].mean(axis=0))
            for a in missing:
                node = int(elements[e][a])
                fallback.setdefault(node, []).append(own(nodes[[node]])[0])
        for node, got in fallback.items():
            total[node], count[node] = np.mean(got, axis=0), 1
        notes["nodes_by_element"] += len(fallback)

        for e in zone:
            for a in range(n_per):
                node = int(elements[e][a])
                out[e, a] = total[node] / count[node]
                source[e, a] = ELEMENT if node in fallback else SPR
    return Recovered(out, source, notes)
