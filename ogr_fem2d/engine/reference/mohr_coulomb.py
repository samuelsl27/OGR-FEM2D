# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Perfectly plastic Mohr-Coulomb in plane strain: implicit (backward Euler)
elastic predictor / return mapping in principal stresses.

Source: de Souza Neto, E. A., Perić, D. and Owen, D. R. J. (2008).
*Computational Methods for Plasticity*, Wiley, §8.2, pp. 295-324:

* yield function of the main plane, with sigma_1 >= sigma_2 >= sigma_3 and
  tension positive (p. 297):
      Phi = sigma_1 - sigma_3 + (sigma_1 + sigma_3) sin(phi) - 2 c cos(phi);
* non-associative flow vectors, phi replaced by the dilatancy psi
  (Eqs. 8.54, 8.55, 8.58, 8.59):
      N1 = (1 + sin psi) e1 x e1 - (1 - sin psi) e3 x e3       main plane
      N6 = (1 + sin psi) e1 x e1 - (1 - sin psi) e2 x e2       right edge
      N2 = (1 + sin psi) e2 x e2 - (1 - sin psi) e3 x e3       left edge
* principal stress update, Eq. (8.68):
      sigma_j = sigma_j_trial - sum_i dgamma_i (2G [N_i,dev]_j + K tr N_i);
* the selection strategy of Box 8.4: main plane first, then the edge chosen by
      (1 - sin psi) s1 - 2 s2 + (1 + sin psi) s3 >= 0  ->  right edge
  (as subroutine SUMC applies it, p. 311, line 97), then the apex;
* the apex p = c cot(phi), Eq. (8.81), with Eq. (8.82); it "does not make
  sense" with psi = 0 (p. 300; SUMC stops with an error, p. 313, line 223):
  here it raises ReturnMappingError.

Perfect plasticity (c constant, H = 0): by Remark 8.1 (p. 300) all four
return equations are linear, and they are solved here in closed form: the
Newton iterations of Boxes 8.5-8.7 converge in one step for them.

Each return is built from Eq. (8.68) and the flow vectors, not copied from
the boxes: the text of Box 8.6 for sigma_1 at the left edge has dgamma_b
where Eq. (8.78) and SUMC (p. 313, line 196) have dgamma_a. The tests check
every return against the plane equations it must satisfy, which is what
catches a slip of that kind.

Plane strain: the trial stress is three-dimensional with eps_zz = 0, so
sigma_zz is a principal stress and the plastic strain may have a zz
component (the elastic one then cancels it).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .elastic import stress_increment

#: Relative tolerance of the yield check and of the sextant check. The returns
#: are closed-form, exact up to rounding, so the tolerance only has to absorb
#: rounding: 1e-12 of the stress scale is about a thousand ulps of double
#: precision, and far below any physical stress.
TOLERANCE = 1e-12


class ReturnMappingError(ValueError):
    """The stress cannot be returned to the surface (apex with psi = 0)."""


@dataclass(frozen=True)
class MohrCoulomb:
    """Material: E, nu, cohesion c, friction phi and dilatancy psi (radians),
    with 0 <= psi <= phi as in the source."""
    young: float
    poisson: float
    cohesion: float
    phi: float
    psi: float

    @property
    def shear_modulus(self) -> float:
        return self.young / (2.0 * (1.0 + self.poisson))

    @property
    def bulk_modulus(self) -> float:
        return self.young / (3.0 * (1.0 - 2.0 * self.poisson))


@dataclass(frozen=True)
class Update:
    """Result of one stress update at one integration point."""
    stress: tuple[float, float, float, float]   # sigma_xx, yy, zz, tau_xy
    region: str            # "elastic", "plane", "right edge", "left edge", "apex"
    #: (dgamma_a, dgamma_b) on the plane and the edges; at the apex,
    #: (volumetric plastic strain increment, 0), Eq. (8.82).
    dgamma: tuple[float, float]


def principal_in_plane(s_xx: float, s_yy: float, t_xy: float
                       ) -> tuple[float, float, float]:
    """In-plane principal stresses (larger, smaller) and the angle theta of
    the larger one from the x axis: the eigen-decomposition of the 2x2
    tensor, written out."""
    centre = 0.5 * (s_xx + s_yy)
    radius = math.hypot(0.5 * (s_xx - s_yy), t_xy)
    theta = 0.5 * math.atan2(2.0 * t_xy, s_xx - s_yy)
    return centre + radius, centre - radius, theta


def yield_function(m: MohrCoulomb, s1: float, s3: float) -> float:
    """Phi of the main plane for sigma_1 >= sigma_3 (p. 297)."""
    return s1 - s3 + (s1 + s3) * math.sin(m.phi) - 2.0 * m.cohesion * math.cos(m.phi)


def _stress_change(m: MohrCoulomb, flow: tuple[float, float, float]
                   ) -> tuple[float, float, float]:
    """2G [N_dev]_j + K tr N for a flow vector given by its principal values:
    the term of Eq. (8.68) that multiplies dgamma."""
    g, k = m.shear_modulus, m.bulk_modulus
    trace = sum(flow)
    return tuple(2.0 * g * (n - trace / 3.0) + k * trace for n in flow)


def _flows(m: MohrCoulomb) -> dict[str, tuple[float, float, float]]:
    sp = math.sin(m.psi)
    return {"N1": (1.0 + sp, 0.0, -(1.0 - sp)),
            "N6": (1.0 + sp, -(1.0 - sp), 0.0),
            "N2": (0.0, 1.0 + sp, -(1.0 - sp))}


def _in_order(s: tuple[float, float, float]) -> bool:
    delta = TOLERANCE * max(1.0, *(abs(x) for x in s))
    return s[0] + delta >= s[1] and s[1] + delta >= s[2]


def return_principal(m: MohrCoulomb, trial: tuple[float, float, float]
                     ) -> tuple[tuple[float, float, float], str, tuple[float, float]]:
    """Return mapping of principal trial stresses ordered s1 >= s2 >= s3.

    Returns the updated principal stresses (same order and directions), the
    region and the multipliers. Box 8.4, steps (iii) and (iv)."""
    s1, s2, s3 = trial
    scale = max(abs(m.cohesion), *(abs(x) for x in trial), 1.0)
    phi_trial = yield_function(m, s1, s3)
    if phi_trial <= TOLERANCE * scale:
        return trial, "elastic", (0.0, 0.0)

    sf = math.sin(m.phi)
    two_c_cos = 2.0 * m.cohesion * math.cos(m.phi)
    flows = _flows(m)
    d1 = _stress_change(m, flows["N1"])

    # (iv.a) main plane: Phi(trial) - a dgamma = 0, a = d Phi / d(dgamma)
    a = (d1[0] - d1[2]) + (d1[0] + d1[2]) * sf      # = Eq. (8.72)
    dg = phi_trial / a
    plane = tuple(t - dg * d for t, d in zip(trial, d1))
    if _in_order(plane):
        return plane, "plane", (dg, 0.0)

    # (iv.c) edge: SUMC, p. 311, line 97
    sp = math.sin(m.psi)
    right = (1.0 - sp) * s1 - 2.0 * s2 + (1.0 + sp) * s3 >= 0.0
    if right:
        db = _stress_change(m, flows["N6"])
        # Phi_b of the plane on the right: sigma_1 - sigma_2 form
        phi_b = s1 - s2 + (s1 + s2) * sf - two_c_cos
        row_a = ((d1[0] - d1[2]) + (d1[0] + d1[2]) * sf,
                 (db[0] - db[2]) + (db[0] + db[2]) * sf)
        row_b = ((d1[0] - d1[1]) + (d1[0] + d1[1]) * sf,
                 (db[0] - db[1]) + (db[0] + db[1]) * sf)
    else:
        db = _stress_change(m, flows["N2"])
        # Phi_b of the plane on the left: sigma_2 - sigma_3 form
        phi_b = s2 - s3 + (s2 + s3) * sf - two_c_cos
        row_a = ((d1[0] - d1[2]) + (d1[0] + d1[2]) * sf,
                 (db[0] - db[2]) + (db[0] + db[2]) * sf)
        row_b = ((d1[1] - d1[2]) + (d1[1] + d1[2]) * sf,
                 (db[1] - db[2]) + (db[1] + db[2]) * sf)
    # Two linear equations: Phi_k(trial) - row_k . (dgamma_a, dgamma_b) = 0
    det = row_a[0] * row_b[1] - row_a[1] * row_b[0]
    dga = (phi_trial * row_b[1] - row_a[1] * phi_b) / det
    dgb = (row_a[0] * phi_b - row_b[0] * phi_trial) / det
    edge = tuple(t - dga * x - dgb * y for t, x, y in zip(trial, d1, db))
    if _in_order(edge):
        return edge, ("right edge" if right else "left edge"), (dga, dgb)

    # (iv.e) apex
    if math.sin(m.psi) == 0.0 or math.sin(m.phi) == 0.0:
        raise ReturnMappingError(
            "return to the apex with psi = 0 (or phi = 0): the flow rule "
            "produces no volumetric plastic strain, so no state satisfies it "
            "(de Souza Neto et al. 2008, p. 300)")
    p_trial = (s1 + s2 + s3) / 3.0
    p = m.cohesion / math.tan(m.phi)                  # Eq. (8.81)
    dev_volumetric = (p_trial - p) / m.bulk_modulus   # Eq. (8.82)
    return (p, p, p), "apex", (dev_volumetric, 0.0)


def update(m: MohrCoulomb, stress: tuple[float, float, float, float],
           strain_increment: tuple[float, float, float]) -> Update:
    """Box 8.4: elastic predictor, spectral decomposition, return, assembly.

    ``stress`` is (sigma_xx, sigma_yy, sigma_zz, tau_xy) at the start of the
    increment and ``strain_increment`` (d_eps_xx, d_eps_yy, d_gamma_xy) with
    d_eps_zz = 0 (plane strain)."""
    d = stress_increment(m.young, m.poisson, strain_increment)
    t_xx, t_yy, t_zz, t_xy = (stress[0] + d[0], stress[1] + d[1],
                              stress[2] + d[2], stress[3] + d[3])
    # (ii) spectral decomposition: two in-plane principal stresses and zz
    p_hi, p_lo, theta = principal_in_plane(t_xx, t_yy, t_xy)
    values = [("hi", p_hi), ("lo", p_lo), ("zz", t_zz)]
    values.sort(key=lambda kv: kv[1], reverse=True)
    trial = tuple(v for _, v in values)
    returned, region, dgamma = return_principal(m, trial)
    if region == "elastic":
        return Update((t_xx, t_yy, t_zz, t_xy), region, dgamma)
    # (v) assembly: sigma = sum sigma_i e_i x e_i, same directions
    new = {name: s for (name, _), s in zip(values, returned)}
    c, s = math.cos(theta), math.sin(theta)
    hi, lo = new["hi"], new["lo"]
    s_xx = hi * c * c + lo * s * s
    s_yy = hi * s * s + lo * c * c
    t_xy_new = (hi - lo) * s * c
    return Update((s_xx, s_yy, new["zz"], t_xy_new), region, dgamma)
