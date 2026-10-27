# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The NumPy variant of the engine (spec 001, RF-3 and T11): the same
computation as the Python reference, vectorised over all the integration
points, behind the common interface (ogr_fem2d.engine.interface).

It exists to be measured against the Rust variant (criterion 5 of ADR-0001),
so it is vectorised for real: no loop over points in Python. Every step of
the reference is done for all the points at once:

* strains B du and internal forces B^T sigma with the dN/dx, dN/dy arrays;
* the elastic predictor of Eq. (4.16) of Zienkiewicz and Taylor (2000);
* the Mohr-Coulomb return of de Souza Neto, Perić and Owen (2008), §8.2:
  every candidate (main plane, right edge, left edge, apex) is computed for
  every point, and the one the reference would take is chosen with masks,
  in the reference's order (elastic, plane, edge, apex) and with its
  tolerance and its edge criterion (SUMC, line 97);
* the consistent tangent of §8.2.4 and Appendix A.3, from the same matrices P
  of mohr_coulomb.principal_derivatives;
* weight B^T D B with einsum.

The formulas and their sources are those of the reference modules, cited
there; this module only changes how they are evaluated. Its identity with
the reference (to 1e-10, at material points and on a mesh) is checked in
tests/test_numpy_variant_v001.py.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import numpy as np

from ogr_fem2d.engine import interface
from ogr_fem2d.engine.reference import mohr_coulomb as mc
from ogr_fem2d.engine.reference.solver import StateUpdateError

TOLERANCE = mc.TOLERANCE


def _in_order(s: np.ndarray) -> np.ndarray:
    """s[:, 0] >= s[:, 1] >= s[:, 2] within the tolerance (mc._in_order)."""
    delta = TOLERANCE * np.maximum(1.0, np.abs(s).max(axis=1))
    return (s[:, 0] + delta >= s[:, 1]) & (s[:, 1] + delta >= s[:, 2])


class _Prepared:
    def __init__(self, g: interface.Geometry):
        self.g = g
        self.n_dofs = g.n_dofs
        m = g.materials
        self.kind = m[:, 0].astype(np.int64)
        young, poisson = m[:, 1], m[:, 2]
        self.cohesion, phi, psi = m[:, 3], m[:, 4], m[:, 5]
        self.mohr = self.kind == interface.MOHR_COULOMB
        # elastic constants (mc.MohrCoulomb.shear_modulus, bulk_modulus)
        self.g_mod = young / (2.0 * (1.0 + poisson))
        self.k_mod = young / (3.0 * (1.0 - 2.0 * poisson))
        self.poisson = poisson
        # Eq. (4.16): the plane strain matrix, as elastic.plane_strain_matrix
        factor = young * (1.0 - poisson) / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
        ratio = poisson / (1.0 - poisson)
        shear = (1.0 - 2.0 * poisson) / (2.0 * (1.0 - poisson))
        self.d11, self.d12, self.d33 = factor, factor * ratio, factor * shear
        d = np.zeros((len(m), 3, 3))
        d[:, 0, 0] = d[:, 1, 1] = self.d11
        d[:, 0, 1] = d[:, 1, 0] = self.d12
        d[:, 2, 2] = self.d33
        self.d_elastic = d
        self.sf, self.cf = np.sin(phi), np.cos(phi)
        self.sp = np.sin(psi)
        self.tan_phi = np.tan(phi)
        # the stress changes 2G N_dev + K tr N of the three flow vectors
        # (mc._flows and mc._stress_change), one row per point
        self.d1 = self._stress_change(1.0 + self.sp, 0.0, -(1.0 - self.sp))
        self.d6 = self._stress_change(1.0 + self.sp, -(1.0 - self.sp), 0.0)
        self.d2 = self._stress_change(0.0, 1.0 + self.sp, -(1.0 - self.sp))
        # dof index of the 12 values of each point
        self.dofs = np.empty((len(m), 12), dtype=np.int64)
        self.dofs[:, 0::2] = 2 * g.nodes
        self.dofs[:, 1::2] = 2 * g.nodes + 1
        # the whole B of each point (Eq. 2.4), for B^T D B
        b = np.zeros((len(m), 3, 12))
        b[:, 0, 0::2] = g.dndx
        b[:, 1, 1::2] = g.dndy
        b[:, 2, 0::2] = g.dndy
        b[:, 2, 1::2] = g.dndx
        self.b = b

    def _stress_change(self, n1, n2, n3):
        n = np.broadcast_arrays(n1, n2, n3, self.g_mod)[:3]
        trace = n[0] + n[1] + n[2]
        return np.stack([2.0 * self.g_mod * (x - trace / 3.0) + self.k_mod * trace
                         for x in n], axis=1)

    # ------------------------------------------------------- kinematics
    def strains(self, du: np.ndarray) -> np.ndarray:
        u = du[2 * self.g.nodes]
        v = du[2 * self.g.nodes + 1]
        return np.stack([(self.g.dndx * u).sum(axis=1),
                         (self.g.dndy * v).sum(axis=1),
                         (self.g.dndy * u + self.g.dndx * v).sum(axis=1)], axis=1)

    def internal_forces(self, stresses: np.ndarray) -> np.ndarray:
        w = self.g.weight[:, None]
        s_xx, s_yy, t_xy = stresses[:, 0:1], stresses[:, 1:2], stresses[:, 3:4]
        fx = w * (self.g.dndx * s_xx + self.g.dndy * t_xy)
        fy = w * (self.g.dndy * s_yy + self.g.dndx * t_xy)
        return (np.bincount((2 * self.g.nodes).ravel(), fx.ravel(), self.n_dofs)
                + np.bincount((2 * self.g.nodes + 1).ravel(), fy.ravel(), self.n_dofs))

    # ------------------------------------------------------ the material
    def integrate(self, start: np.ndarray, strains: np.ndarray) -> interface.Integration:
        n = len(start)
        ex, ey, gxy = strains[:, 0], strains[:, 1], strains[:, 2]
        ds_xx = self.d11 * ex + self.d12 * ey
        ds_yy = self.d12 * ex + self.d11 * ey
        t_xx = start[:, 0] + ds_xx
        t_yy = start[:, 1] + ds_yy
        t_zz = start[:, 2] + self.poisson * (ds_xx + ds_yy)
        t_xy = start[:, 3] + self.d33 * gxy
        stresses = np.stack([t_xx, t_yy, t_zz, t_xy], axis=1)
        tangents = self.d_elastic.copy()
        plastic = np.zeros(n, dtype=bool)
        if not self.mohr.any():
            return interface.Integration(stresses, plastic, tangents)

        # (ii) spectral decomposition: two in-plane principal stresses and zz
        centre = 0.5 * (t_xx + t_yy)
        radius = np.hypot(0.5 * (t_xx - t_yy), t_xy)
        theta = 0.5 * np.arctan2(2.0 * t_xy, t_xx - t_yy)
        named = np.stack([centre + radius, centre - radius, t_zz], axis=1)  # hi, lo, zz
        # descending, ties kept in (hi, lo, zz) order as Python's sort does
        order = np.argsort(-named, axis=1, kind="stable")
        trial = np.take_along_axis(named, order, axis=1)
        s1, s2, s3 = trial[:, 0], trial[:, 1], trial[:, 2]

        # (iii) the trial yield function and the elastic points
        c = self.cohesion
        two_c_cos = 2.0 * c * self.cf
        sf, sp = self.sf, self.sp
        phi_trial = s1 - s3 + (s1 + s3) * sf - two_c_cos
        scale = np.maximum(np.maximum(np.abs(c), np.abs(trial).max(axis=1)), 1.0)
        elastic = phi_trial <= TOLERANCE * scale

        # (iv.a) main plane, for every point
        d1 = self.d1
        ga = lambda x: (x[:, 0] - x[:, 2]) + (x[:, 0] + x[:, 2]) * sf  # noqa: E731
        a = ga(d1)
        dg = phi_trial / a
        plane = trial - dg[:, None] * d1
        on_plane = _in_order(plane)

        # (iv.c) edges, both computed, the SUMC criterion chooses
        right = (1.0 - sp) * s1 - 2.0 * s2 + (1.0 + sp) * s3 >= 0.0
        gb_right = lambda x: (x[:, 0] - x[:, 1]) + (x[:, 0] + x[:, 1]) * sf  # noqa: E731
        gb_left = lambda x: (x[:, 1] - x[:, 2]) + (x[:, 1] + x[:, 2]) * sf  # noqa: E731
        db = np.where(right[:, None], self.d6, self.d2)
        phi_b = np.where(right, s1 - s2 + (s1 + s2) * sf, s2 - s3 + (s2 + s3) * sf) - two_c_cos
        r11, r12 = ga(d1), ga(db)
        r21 = np.where(right, gb_right(d1), gb_left(d1))
        r22 = np.where(right, gb_right(db), gb_left(db))
        det = r11 * r22 - r12 * r21
        with np.errstate(divide="ignore", invalid="ignore"):
            dga = (phi_trial * r22 - r12 * phi_b) / det
            dgb = (r11 * phi_b - r21 * phi_trial) / det
        edge = trial - dga[:, None] * d1 - dgb[:, None] * db
        on_edge = _in_order(edge)

        # the region each point takes, in the reference's order
        mohr = self.mohr
        is_plane = mohr & ~elastic & on_plane
        is_edge = mohr & ~elastic & ~on_plane & on_edge
        is_apex = mohr & ~elastic & ~on_plane & ~on_edge
        refused = is_apex & ((sp == 0.0) | (sf == 0.0))
        if refused.any():
            k = int(np.argmax(refused))
            raise StateUpdateError(
                int(self.g.element[k]), int(self.g.index[k]), None, None,
                "return to the apex with psi = 0 (or phi = 0): the flow rule "
                "produces no volumetric plastic strain, so no state satisfies "
                "it (de Souza Neto et al. 2008, p. 300)")
        with np.errstate(divide="ignore", invalid="ignore"):
            apex = np.repeat((c / self.tan_phi)[:, None], 3, axis=1)   # Eq. (8.81)
        returned = np.where(is_plane[:, None], plane,
                            np.where(is_edge[:, None], edge,
                                     np.where(is_apex[:, None], apex, trial)))

        # (v) assembly: back to (hi, lo, zz), then the in-plane tensor
        new = np.empty_like(returned)
        np.put_along_axis(new, order, returned, axis=1)
        hi, lo = new[:, 0], new[:, 1]
        cs, sn = np.cos(theta), np.sin(theta)
        assembled = np.stack([hi * cs * cs + lo * sn * sn,
                              hi * sn * sn + lo * cs * cs,
                              new[:, 2],
                              (hi - lo) * sn * cs], axis=1)
        yielded = is_plane | is_edge | is_apex
        stresses = np.where(yielded[:, None], assembled, stresses)
        plastic = yielded

        # the consistent tangent of the Mohr-Coulomb points
        tangents[mohr] = self._tangent(order, trial, returned, theta, sf, d1, db,
                                       dg, r11, r12, r21, r22, det, ga,
                                       right, gb_right, gb_left,
                                       elastic, is_plane, is_edge, is_apex)[mohr]
        return interface.Integration(stresses, plastic, tangents)

    def _tangent(self, order, trial, returned, theta, sf, d1, db, dg,
                 r11, r12, r21, r22, det, ga, right, gb_right, gb_left,
                 elastic, is_plane, is_edge, is_apex):
        """mohr_coulomb.principal_derivatives and mohr_coulomb._tangent, for
        all the points."""
        n = len(trial)
        eye = np.broadcast_to(np.eye(3), (n, 3, 3))
        # gradients of the planes, as vectors over the sorted principal values
        g_a = np.stack([1.0 + sf, np.zeros(n), -(1.0 - sf)], axis=1)
        g_b = np.where(right[:, None],
                       np.stack([1.0 + sf, -(1.0 - sf), np.zeros(n)], axis=1),
                       np.stack([np.zeros(n), 1.0 + sf, -(1.0 - sf)], axis=1))
        a = ga(d1)
        with np.errstate(divide="ignore", invalid="ignore"):
            p_plane = eye - d1[:, :, None] * g_a[:, None, :] / a[:, None, None]
            inv = np.stack([np.stack([r22 / det, -r12 / det], axis=1),
                            np.stack([-r21 / det, r11 / det], axis=1)], axis=1)
        dga = inv[:, 0, 0, None] * g_a + inv[:, 0, 1, None] * g_b
        dgb = inv[:, 1, 0, None] * g_a + inv[:, 1, 1, None] * g_b
        p_edge = eye - d1[:, :, None] * dga[:, None, :] - db[:, :, None] * dgb[:, None, :]
        p = np.where(is_plane[:, None, None], p_plane,
                     np.where(is_edge[:, None, None], p_edge,
                              np.where(is_apex[:, None, None], 0.0, eye)))
        g, k = self.g_mod, self.k_mod
        lam = k - 2.0 * g / 3.0
        de = lam[:, None, None] * np.ones((n, 3, 3)) + 2.0 * g[:, None, None] * eye
        cmat = p @ de
        # positions of hi and lo in the sorted order
        h = np.argmax(order == 0, axis=1)
        l_ = np.argmax(order == 1, axis=1)
        rows = np.arange(n)
        c_hh, c_hl = cmat[rows, h, h], cmat[rows, h, l_]
        c_lh, c_ll = cmat[rows, l_, h], cmat[rows, l_, l_]
        gap = trial[rows, h] - trial[rows, l_]
        distinct = np.abs(gap) > TOLERANCE * np.maximum(
            1.0, np.maximum(np.abs(trial[rows, h]), np.abs(trial[rows, l_])))
        with np.errstate(divide="ignore", invalid="ignore"):
            shear = np.where(distinct,
                             g * (returned[rows, h] - returned[rows, l_]) / gap,
                             g * (p[rows, h, h] - p[rows, h, l_]))
        cs, sn = np.cos(theta), np.sin(theta)
        amat = np.stack([np.stack([cs * cs, sn * sn, -2.0 * sn * cs], axis=1),
                         np.stack([sn * sn, cs * cs, 2.0 * sn * cs], axis=1),
                         np.stack([sn * cs, -sn * cs, cs * cs - sn * sn], axis=1)],
                        axis=1)
        cp = np.zeros((n, 3, 3))
        cp[:, 0, 0], cp[:, 0, 1], cp[:, 1, 0], cp[:, 1, 1] = c_hh, c_hl, c_lh, c_ll
        cp[:, 2, 2] = shear
        return amat @ cp @ np.transpose(amat, (0, 2, 1))

    # ------------------------------------------------- the one call
    def update(self, start: np.ndarray, du: np.ndarray) -> interface.PointsUpdate:
        result = self.integrate(start, self.strains(du))
        stiffness = np.einsum("nki,nkl,nlj->nij", self.b, result.tangents, self.b)
        stiffness *= self.g.weight[:, None, None]
        return interface.PointsUpdate(result.stresses,
                                      self.internal_forces(result.stresses),
                                      result.plastic, result.tangents,
                                      stiffness.reshape(len(start), 144))


class NumpyVariant:
    """The NumPy variant behind the common interface (spec 001, T11)."""
    name = "numpy"

    def prepare(self, g: interface.Geometry) -> _Prepared:
        return _Prepared(g)


NUMPY = NumpyVariant()
