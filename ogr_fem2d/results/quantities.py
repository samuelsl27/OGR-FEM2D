# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The field quantities (spec 005, RF-5 to RF-7; D1, D2, D3, D16): the
catalogue, and each quantity computed from the user's tensors.

Every quantity here is in the USER'S convention (D1): stresses compression
positive, strains shortening positive, displacements along +x and +y. The
engine's numbers become the user's in ``model/conventions.py`` and nowhere
else; this module only receives what that module gives.

The tensors, as NumPy arrays whose last axis is:

* a stress: (xx, yy, zz, xy), as the engine's (docs/motor/entrada.md); in
  axisymmetry (r, z, theta, rz);
* a strain: (xx, yy, zz, xy) with the ENGINEERING shear strain gamma_xy
  (``strain4`` makes it from the engine's three components in plane strain,
  where eps_z = 0, and four in axisymmetry);
* a displacement: (u_x, u_y).

Sources (spec 005, plan, "Formulación"; read on the page):

* Jaeger, J. C., Cook, N. G. W. and Zimmerman, R. W. (2007). *Fundamentals
  of Rock Mechanics*, 4th ed. Blackwell (JCZ):

  - principal stresses in the plane, Eqs. (2.37)-(2.38), p. 21, and the
    angle of sigma_1, Eq. (2.33) with the branches (2.41)-(2.44), p. 21,
    0 <= theta_1 < 180 degrees from x, anticlockwise. Written for tau, they
    hold for any symmetric tensor, so in the user's components too;
  - the mean normal stress, Eq. (2.153), p. 40;
  - J2, Eq. (2.163), p. 41. Its neighbour (2.162) is printed with tau_xx^2
    where the deviator s_xx^2 belongs (a hydrostatic state would give a J2
    that is not zero), and (2.149) with (sigma_3 - sigma_3)^2 where
    (sigma_3 - sigma_1)^2 belongs: errata of the book, seen on the page
    (changelog v0.0.11, T1). Neither is used;
  - the differential stress, sigma_1 - sigma_3 of the triaxial test, ch. 6,
    p. 151; here between the greatest and the least of the three;
  - strains in two dimensions, Eqs. (2.181)-(2.186), pp. 45-46, and the
    engineering shear strain gamma = 2 eps, p. 46; the principal strains,
    Eq. (2.195), p. 47, printed without the square root of the bracket that
    its stress twin (2.37) has: an erratum, the root is the right form (the
    strain is a tensor, Eq. 2.193, and "all theorems pertaining to principal
    stresses carry over directly to strains", p. 47);
  - the volumetric strain, the first invariant, Eq. (2.231), p. 53.

* de Souza Neto, E. A., Perić, D. and Owen, D. R. J. (2008). *Computational
  Methods for Plasticity*. Wiley: the von Mises effective stress
  q = sqrt(3 J2), Eq. (6.111), p. 163.

The out-of-plane direction is principal: in a plane problem tau_xz = tau_yz
= 0, so z is an eigenvector of the stress (JCZ §2.5), and the three
principal stresses are sigma_1, sigma_3 and sigma_z, ordered (D2).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

STRESS, STRAIN, DISPLACEMENT = "stress", "strain", "displacement"
#: the core's quantities (ogr_core.units.Quantity) of each unit
PRESSURE, LENGTH, DIMENSIONLESS, ANGLE = "pressure", "length", "dimensionless", "angle"

CONVENTION = {STRESS: "compression positive", STRAIN: "shortening positive",
              DISPLACEMENT: "along +x and +y"}


@dataclass(frozen=True)
class Quantity:
    """An entry of the catalogue (D16)."""
    id: str
    kind: str                 # STRESS, STRAIN or DISPLACEMENT
    unit: str                 # the core's quantity of its unit
    label: str                # in plane strain
    label_axi: str            # in axisymmetry (RF-6)
    definition: str
    source: str

    @property
    def key(self) -> str:
        """The translatable key of its label (rule 2; the 006 translates)."""
        return f"results.quantity.{self.id}"

    @property
    def convention(self) -> str:
        return CONVENTION[self.kind] if self.unit != ANGLE else "from +x, anticlockwise, degrees"

    def name(self, analysis: str) -> str:
        return self.label_axi if analysis == "axisymmetric" else self.label


_JCZ = "Jaeger, Cook and Zimmerman (2007)"
CATALOGUE: tuple[Quantity, ...] = (
    Quantity("sigma_xx", STRESS, PRESSURE, "Sigma xx", "Sigma r (radial)",
             "the normal stress along x", "-"),
    Quantity("sigma_yy", STRESS, PRESSURE, "Sigma yy", "Sigma z (axial)",
             "the normal stress along y", "-"),
    Quantity("sigma_z", STRESS, PRESSURE, "Sigma z (out of plane)", "Sigma theta (circumferential)",
             "the normal stress out of the plane; in axisymmetry, the hoop stress", "-"),
    Quantity("tau_xy", STRESS, PRESSURE, "Tau xy", "Tau rz", "the shear stress in the plane", "-"),
    Quantity("sigma_1", STRESS, PRESSURE, "Sigma 1 (in plane)", "Sigma 1 (in the meridian plane)",
             "the major principal stress in the plane: (sxx + syy)/2 + [txy^2 + (sxx - syy)^2/4]^(1/2)",
             f"{_JCZ}, Eq. (2.37)"),
    Quantity("sigma_3", STRESS, PRESSURE, "Sigma 3 (in plane)", "Sigma 3 (in the meridian plane)",
             "the minor principal stress in the plane: (sxx + syy)/2 - [txy^2 + (sxx - syy)^2/4]^(1/2)",
             f"{_JCZ}, Eq. (2.38)"),
    Quantity("theta_1", STRESS, ANGLE, "Angle of sigma 1", "Angle of sigma 1",
             "the angle of sigma_1 from +x, anticlockwise, 0 <= theta < 180: tan 2 theta = "
             "2 txy / (sxx - syy) on the branch of Eqs. (2.41)-(2.44)",
             f"{_JCZ}, Eqs. (2.33), (2.41)-(2.44)"),
    Quantity("sigma_I", STRESS, PRESSURE, "Sigma I (greatest)", "Sigma I (greatest)",
             "the greatest of sigma_1, sigma_3 and sigma_z (z is a principal direction)",
             f"{_JCZ}, §2.5"),
    Quantity("sigma_II", STRESS, PRESSURE, "Sigma II (intermediate)", "Sigma II (intermediate)",
             "the intermediate of sigma_1, sigma_3 and sigma_z", f"{_JCZ}, §2.5"),
    Quantity("sigma_III", STRESS, PRESSURE, "Sigma III (least)", "Sigma III (least)",
             "the least of sigma_1, sigma_3 and sigma_z", f"{_JCZ}, §2.5"),
    Quantity("p", STRESS, PRESSURE, "Mean stress", "Mean stress",
             "p = (sxx + syy + szz) / 3", f"{_JCZ}, Eq. (2.153)"),
    Quantity("q", STRESS, PRESSURE, "Von Mises stress", "Von Mises stress",
             "q = sqrt(3 J2), J2 = [(sxx - syy)^2 + (syy - szz)^2 + (szz - sxx)^2]/6 + txy^2",
             "de Souza Neto, Perić and Owen (2008), Eq. (6.111); " f"{_JCZ}, Eq. (2.163)"),
    Quantity("sigma_diff", STRESS, PRESSURE, "Differential stress", "Differential stress",
             "sigma_I - sigma_III", f"{_JCZ}, ch. 6, p. 151"),
    Quantity("u_x", DISPLACEMENT, LENGTH, "Horizontal displacement", "Radial displacement",
             "the displacement along +x", "-"),
    Quantity("u_y", DISPLACEMENT, LENGTH, "Vertical displacement", "Axial displacement",
             "the displacement along +y", "-"),
    Quantity("u", DISPLACEMENT, LENGTH, "Total displacement", "Total displacement",
             "sqrt(u_x^2 + u_y^2)", "-"),
    Quantity("eps_xx", STRAIN, DIMENSIONLESS, "Strain xx", "Strain r (radial)",
             "the normal strain along x", f"{_JCZ}, Eq. (2.181)"),
    Quantity("eps_yy", STRAIN, DIMENSIONLESS, "Strain yy", "Strain z (axial)",
             "the normal strain along y", f"{_JCZ}, Eq. (2.182)"),
    Quantity("eps_z", STRAIN, DIMENSIONLESS, "Strain z (out of plane)",
             "Strain theta (circumferential)",
             "the normal strain out of the plane: 0 in plane strain, u_r / r in axisymmetry",
             "Zienkiewicz and Taylor (2000), Eqs. (5.5)-(5.6)"),
    Quantity("gamma_xy", STRAIN, DIMENSIONLESS, "Shear strain xy (engineering)",
             "Shear strain rz (engineering)", "gamma_xy = 2 eps_xy",
             f"{_JCZ}, Eq. (2.185) and p. 46"),
    Quantity("eps_v", STRAIN, DIMENSIONLESS, "Volumetric strain", "Volumetric strain",
             "eps_xx + eps_yy + eps_z", f"{_JCZ}, Eq. (2.231)"),
    Quantity("gamma_max", STRAIN, DIMENSIONLESS, "Maximum shear strain (engineering, in plane)",
             "Maximum shear strain (engineering, in the meridian plane)",
             "eps_1 - eps_3 = [gamma_xy^2 + (eps_xx - eps_yy)^2]^(1/2), twice the tensorial one",
             f"{_JCZ}, Eq. (2.195) and p. 46"),
)

BY_ID = {q.id: q for q in CATALOGUE}


def get(quantity_id: str) -> Quantity:
    try:
        return BY_ID[quantity_id]
    except KeyError:
        raise KeyError(f"no quantity {quantity_id!r}; the catalogue has "
                       f"{', '.join(BY_ID)}") from None


# ------------------------------------------------------------- the tensors
def strain4(engine_shaped, analysis: str) -> np.ndarray:
    """(xx, yy, zz, xy) of a strain given as the engine's B u gives it:
    (xx, yy, gamma_xy) in plane strain (eps_z = 0), (r, z, theta, gamma_rz)
    in axisymmetry. The values are taken as they are: the sign is the
    caller's."""
    e = np.asarray(engine_shaped, dtype=float)
    if analysis == "axisymmetric":
        return e
    out = np.zeros(e.shape[:-1] + (4,))
    out[..., 0], out[..., 1], out[..., 3] = e[..., 0], e[..., 1], e[..., 2]
    return out


def principal_in_plane(s) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """sigma_1 >= sigma_3 in the plane and the angle of sigma_1 (degrees,
    0 <= theta < 180), JCZ Eqs. (2.33), (2.37)-(2.38), (2.41)-(2.44)."""
    s = np.asarray(s, dtype=float)
    xx, yy, xy = s[..., 0], s[..., 1], s[..., 3]
    centre = 0.5 * (xx + yy)
    radius = np.sqrt(xy * xy + 0.25 * (xx - yy) ** 2)
    # 2 theta = atan2(2 txy, sxx - syy) is the branch of (2.41)-(2.44): with
    # cos 2 theta = (sxx - syy) / 2R and sin 2 theta = txy / R, Eq. (2.40)
    # gives d2 sigma / d theta2 = -4 R < 0, a maximum of sigma
    theta = 0.5 * np.degrees(np.arctan2(2.0 * xy, xx - yy))
    theta = np.where(theta < 0.0, theta + 180.0, theta)
    return centre + radius, centre - radius, theta


def principal_3d(s) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """sigma_I >= sigma_II >= sigma_III: sigma_1, sigma_3 and sigma_z
    ordered."""
    s = np.asarray(s, dtype=float)
    s1, s3, _ = principal_in_plane(s)
    ordered = np.sort(np.stack([s1, s3, s[..., 2]], axis=-1), axis=-1)
    return ordered[..., 2], ordered[..., 1], ordered[..., 0]


def j2(s) -> np.ndarray:
    """J2, JCZ Eq. (2.163), with tau_yz = tau_xz = 0."""
    s = np.asarray(s, dtype=float)
    xx, yy, zz, xy = s[..., 0], s[..., 1], s[..., 2], s[..., 3]
    return ((xx - yy) ** 2 + (yy - zz) ** 2 + (zz - xx) ** 2) / 6.0 + xy * xy


def stress_quantity(quantity_id: str, s) -> np.ndarray:
    """A stress quantity of the user's stresses ``s`` (compression
    positive), last axis (xx, yy, zz, xy)."""
    s = np.asarray(s, dtype=float)
    q = quantity_id
    simple = {"sigma_xx": 0, "sigma_yy": 1, "sigma_z": 2, "tau_xy": 3}
    if q in simple:
        return s[..., simple[q]].copy()
    if q in ("sigma_1", "sigma_3", "theta_1"):
        return principal_in_plane(s)[("sigma_1", "sigma_3", "theta_1").index(q)]
    if q in ("sigma_I", "sigma_II", "sigma_III"):
        return principal_3d(s)[("sigma_I", "sigma_II", "sigma_III").index(q)]
    if q == "p":
        return (s[..., 0] + s[..., 1] + s[..., 2]) / 3.0
    if q == "q":
        return np.sqrt(3.0 * j2(s))
    if q == "sigma_diff":
        big, _, small = principal_3d(s)
        return big - small
    raise KeyError(f"{q!r} is not a stress quantity")


def strain_quantity(quantity_id: str, e) -> np.ndarray:
    """A strain quantity of the user's strains ``e`` (shortening positive),
    last axis (xx, yy, zz, gamma_xy) (``strain4``)."""
    e = np.asarray(e, dtype=float)
    q = quantity_id
    simple = {"eps_xx": 0, "eps_yy": 1, "eps_z": 2, "gamma_xy": 3}
    if q in simple:
        return e[..., simple[q]].copy()
    if q == "eps_v":
        return e[..., 0] + e[..., 1] + e[..., 2]
    if q == "gamma_max":
        # eps_1 - eps_3 = 2 [eps_xy^2 + (eps_xx - eps_yy)^2 / 4]^(1/2), Eq. (2.195)
        # with eps_xy = gamma_xy / 2
        return np.sqrt(e[..., 3] ** 2 + (e[..., 0] - e[..., 1]) ** 2)
    raise KeyError(f"{q!r} is not a strain quantity")


def displacement_quantity(quantity_id: str, u) -> np.ndarray:
    """A displacement quantity of ``u`` (last axis (u_x, u_y))."""
    u = np.asarray(u, dtype=float)
    if quantity_id == "u_x":
        return u[..., 0].copy()
    if quantity_id == "u_y":
        return u[..., 1].copy()
    if quantity_id == "u":
        return np.hypot(u[..., 0], u[..., 1])
    raise KeyError(f"{quantity_id!r} is not a displacement quantity")


def of(quantity_id: str, tensor) -> np.ndarray:
    """The quantity of the tensor of its kind (stress, strain or
    displacement), in the user's convention."""
    kind = get(quantity_id).kind
    if kind == STRESS:
        return stress_quantity(quantity_id, tensor)
    if kind == STRAIN:
        return strain_quantity(quantity_id, tensor)
    return displacement_quantity(quantity_id, tensor)
