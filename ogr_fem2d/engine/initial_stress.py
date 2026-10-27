# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The initial stress fields, computed outside the engine (spec 002, RF-7, D3
and its amendment; task T8).

The engine receives one stress per integration point (rule 11 of AGENTS.md,
model.EngineModel.initial_stresses) and knows nothing of fields; this module
computes the two usual ones at those points. It takes the geotechnical
convention, COMPRESSION POSITIVE, and gives the engine's, tension positive
(spec 001, D1): the conversion is here, in one place.

* Constant field: the major and minor principal stresses sigma_1 >= sigma_3
  in the plane, the out-of-plane sigma_z, and the angle of sigma_1 from the
  x axis, anticlockwise. A tensor whose principal axes are rotated by theta
  from (x, y) is L^T diag(sigma_1, sigma_3) L with L the rotation of
  Jaeger, Cook and Zimmerman (2007), *Fundamentals of Rock Mechanics*, 4th
  ed., §2.3, Eqs. (2.28)-(2.30), p. 19 (the inverse of tau' = L tau L^T):
      sigma_xx = sigma_1 cos^2 theta + sigma_3 sin^2 theta
      sigma_yy = sigma_1 sin^2 theta + sigma_3 cos^2 theta
      tau_xy   = (sigma_1 - sigma_3) sin theta cos theta,
  which are Eqs. (2.25)-(2.27) with the roles of the two frames exchanged.
* Gravitational field with a horizontal surface and horizontal strata:
  the vertical stress is the weight of the column above, sigma_v =
  int gamma dz (JCZ 2007, §13.2, Eq. 13.1, p. 400), and the horizontal ones
  are k sigma_v (Eq. 13.5, p. 401), with K in the plane and Kz out of it,
  per stratum (spec 002, D3). Variable K and an irregular surface are not
  here (D3).
* Axisymmetry (amendment of D3): radial equilibrium carries
  (sigma_r - sigma_theta) / r (Timoshenko and Goodier 1951, §116, Eq. 177,
  p. 343), so a field uniform in r is in equilibrium only with sigma_r =
  sigma_theta, and tau_rz must vanish on the axis. The gravitational field
  needs K = Kz, and the constant one sigma_r = sigma_theta and tau_rz = 0;
  anything else is refused with the reason, because the engine would turn
  it into a load nobody applied.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .model import AXISYMMETRIC, EngineModel
from .reference import solver

Stress = tuple[float, float, float, float]


class InitialStressError(ValueError):
    """A field that cannot be built as given."""


def integration_point_coordinates(m: EngineModel) -> list[tuple[float, float]]:
    """(x, y) of every integration point of ``m``, in the order of
    EngineModel.initial_stresses (element by element, then the rule's)."""
    engine = solver.Model(list(m.nodes), list(m.elements),
                          [m.materials[k].law for k in m.element_material], frozenset(),
                          m.analysis)
    return [p.xy for p in solver.integration_points(engine)]


# ------------------------------------------------------------ constant field
def constant(sigma_1: float, sigma_3: float, sigma_z: float, angle: float,
             analysis: str) -> Stress:
    """The engine's stress (tension positive) of a constant field given
    compression positive; ``angle`` of sigma_1 from x, anticlockwise, in
    degrees."""
    if sigma_1 < sigma_3:
        raise InitialStressError(f"sigma_1 = {sigma_1} < sigma_3 = {sigma_3}: sigma_1 is "
                                 "the major principal stress")
    t = math.radians(angle)
    c, s = math.cos(t), math.sin(t)
    sxx = sigma_1 * c * c + sigma_3 * s * s
    syy = sigma_1 * s * s + sigma_3 * c * c
    txy = (sigma_1 - sigma_3) * s * c
    if analysis == AXISYMMETRIC:
        scale = max(abs(sigma_1), abs(sigma_3), abs(sigma_z), 1.0)
        if abs(txy) > 1e-12 * scale or abs(sxx - sigma_z) > 1e-12 * scale:
            raise InitialStressError(
                f"in axisymmetry a constant field needs sigma_r = sigma_theta and "
                f"tau_rz = 0 (radial equilibrium, Timoshenko and Goodier 1951, Eq. 177): "
                f"this one has sigma_r = {sxx:.6g}, sigma_theta = sigma_z = {sigma_z:.6g}, "
                f"tau_rz = {txy:.6g} (spec 002, D3 amendment)")
    return -sxx, -syy, -sigma_z, -txy


def constant_field(m: EngineModel, sigma_1: float, sigma_3: float, sigma_z: float,
                   angle: float) -> tuple[Stress, ...]:
    """The same constant stress at every integration point of ``m``."""
    s = constant(sigma_1, sigma_3, sigma_z, angle, m.analysis)
    return (s,) * m.n_points


# ------------------------------------------------------- gravitational field
@dataclass(frozen=True)
class Stratum:
    """A horizontal stratum, from the bottom of the one above (or the
    surface) down to ``bottom``: its unit weight and its K in the plane and
    Kz out of it."""
    bottom: float
    unit_weight: float
    k: float
    kz: float


def gravitational(y: float, surface: float, strata: list[Stratum], analysis: str) -> Stress:
    """The engine's stress (tension positive) at depth surface - y: sigma_v
    the weight of the column above (Eq. 13.1), K sigma_v and Kz sigma_v of
    the stratum the point is in (Eq. 13.5)."""
    if y > surface:
        raise InitialStressError(f"y = {y:.6g} is above the surface {surface:.6g}")
    sigma_v, top = 0.0, surface
    for layer in strata:
        if y >= layer.bottom:
            sigma_v += layer.unit_weight * (top - y)
            return (-layer.k * sigma_v, -sigma_v, -layer.kz * sigma_v, 0.0)
        sigma_v += layer.unit_weight * (top - layer.bottom)
        top = layer.bottom
    raise InitialStressError(f"y = {y:.6g} is below the last stratum ({top:.6g})")


def _check_strata(surface: float, strata: list[Stratum], analysis: str) -> None:
    top = surface
    for i, layer in enumerate(strata):
        if not layer.bottom < top:
            raise InitialStressError(f"stratum {i}: its bottom {layer.bottom:.6g} is not below "
                                     f"its top {top:.6g}")
        if min(layer.unit_weight, layer.k, layer.kz) < 0.0:
            raise InitialStressError(f"stratum {i}: unit weight, K and Kz must be >= 0")
        if analysis == AXISYMMETRIC and layer.k != layer.kz:
            raise InitialStressError(
                f"stratum {i}: in axisymmetry K = Kz is needed (K = {layer.k}, Kz = "
                f"{layer.kz}): with sigma_r != sigma_theta the field is not in radial "
                "equilibrium (Timoshenko and Goodier 1951, Eq. 177; spec 002, D3 amendment)")
        top = layer.bottom


def gravitational_field(m: EngineModel, surface: float, strata: list[Stratum]
                        ) -> tuple[Stress, ...]:
    """The gravitational stress at every integration point of ``m``."""
    _check_strata(surface, strata, m.analysis)
    return tuple(gravitational(y, surface, strata, m.analysis)
                 for _, y in integration_point_coordinates(m))
