# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The spherical cavity of spec 002 (case 003, ficha VER-STR-09), built for the
engine, and the spherical quantities the tests compare (not a test file: the
runner only collects test_*.py).

The model (validacion/casos/003-cavidad-esferica-elastica/caso.md): the
quarter annulus a <= R <= b of the meridian plane, x = r >= 0, y = z >= 0,
axisymmetric; v = 0 on the plane of symmetry y = 0; u_r = 0 on the axis
x = 0, which the engine holds by itself (D1 bis); the outer sphere fixed;
the hydrostatic field everywhere and one stage with no load: the cavity,
which the mesh does not have, is excavated by the initial-stress term.

Signs: the engine is tension-positive with u outward (D1); the closed forms
of the spec's comprobaciones/soluciones_cerradas.py are compression-positive
with u inward. The conversion is here, in one place.
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

from ogr_fem2d.engine import analysis
from ogr_fem2d.engine import initial_stress as ini
from ogr_fem2d.engine import model as m
from ogr_fem2d.engine.mesh_radial import quarter_annulus
from ogr_fem2d.engine.reference.elastic import Elastic

_CHECKS = (Path(__file__).resolve().parents[1] / "spec" / "features"
           / "002-motor-elastico" / "comprobaciones" / "soluciones_cerradas.py")
# Loaded by its path under its own name: spec 001 has a module of the same
# name (tests/_hole.py), and whichever came first would take the name.
_spec = importlib.util.spec_from_file_location("soluciones_cerradas_002", _CHECKS)
closed = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = closed
_spec.loader.exec_module(closed)

A, P0, E, NU = closed.A, closed.P0, closed.E, closed.NU


def model(b, n_radial, n_theta, growth, nodes_per_element=6, steps=1, tolerance=1e-10,
          max_iterations=5):
    mesh = quarter_annulus(A, b, n_radial, n_theta, growth, nodes_per_element)
    restraints = [m.Restraint(n, False, True) for n in mesh.x_axis if n not in mesh.outer]
    restraints += [m.Restraint(n, True, True) for n in mesh.outer]
    stage = m.Stage(active=(True,) * len(mesh.elements), restraints=tuple(restraints),
                    steps=steps, tolerance=tolerance, max_iterations=max_iterations)
    base = m.EngineModel(m.AXISYMMETRIC, tuple(mesh.nodes), tuple(map(tuple, mesh.elements)),
                         (m.Material(Elastic(E, NU)),), (0,) * len(mesh.elements), (stage,))
    field = ini.constant_field(base, P0, P0, P0, 0.0)
    return mesh, m.EngineModel(base.analysis, base.nodes, base.elements, base.materials,
                               base.element_material, base.stages, field)


def excavate(b, n_radial, n_theta, growth, nodes_per_element=6, variant=None, **stage):
    mesh, engine_model = model(b, n_radial, n_theta, growth, nodes_per_element, **stage)
    kwargs = {} if variant is None else {"variant": variant}
    return mesh, engine_model, analysis.run(engine_model, **kwargs)[0]


def radial_inward(mesh, outcome, node):
    """u_R positive inward at a node."""
    x, y = mesh.nodes[node]
    big_r = math.hypot(x, y)
    return -(outcome.displacement[2 * node] * x + outcome.displacement[2 * node + 1] * y) / big_r


def spherical_compressive(xy, stress):
    """(R, sigma_R, sigma_t meridian, sigma_t hoop, tau_Rt) at a point,
    compression positive: the meridional components by rotating the in-plane
    tensor to the direction of R; the hoop one is sigma_zz of the engine."""
    x, y = xy
    big_r = math.hypot(x, y)
    c, s = x / big_r, y / big_r
    s_rr, s_zz, s_hoop, t_rz = stress
    sigma_big_r = s_rr * c * c + s_zz * s * s + 2.0 * t_rz * s * c
    sigma_merid = s_rr * s * s + s_zz * c * c - 2.0 * t_rz * s * c
    tau = (s_zz - s_rr) * s * c + t_rz * (c * c - s * s)
    return big_r, -sigma_big_r, -sigma_merid, -s_hoop, -tau


def first_ring_points(mesh, engine_model, outcome):
    """(xy, stress) of the integration points of the elements between the
    first two corner radii."""
    points = ini.integration_point_coordinates(engine_model)
    per = len(points) // len(engine_model.elements)
    limit = mesh.radii[1] * (1 + 1e-12)
    out = []
    for e, element in enumerate(engine_model.elements):
        if max(math.hypot(*mesh.nodes[n]) for n in element) <= limit:
            for g in range(e * per, (e + 1) * per):
                out.append((points[g], outcome.stresses[g]))
    return out


def worst_errors(mesh, engine_model, outcome, reference):
    """The worst relative errors (sigma_t on the first ring, both tangential
    components; u_R on the hole) against ``reference``(R) -> (sigma_R,
    sigma_t, u_in)."""
    sigma_t = 0.0
    for xy, stress in first_ring_points(mesh, engine_model, outcome):
        big_r, _, merid, hoop, _ = spherical_compressive(xy, stress)
        want = reference(big_r)[1]
        sigma_t = max(sigma_t, abs(merid / want - 1), abs(hoop / want - 1))
    u = max(abs(radial_inward(mesh, outcome, n) / reference(A)[2] - 1) for n in mesh.hole)
    return sigma_t, u
