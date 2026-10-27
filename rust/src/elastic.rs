// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
//! Linear isotropic elasticity in plane strain: the twin of
//! ogr_fem2d/engine/reference/elastic.py.
//!
//! Source: Zienkiewicz, O. C. and Taylor, R. L. (2000). *The Finite Element
//! Method*, 5th ed., vol. 1, §4.2.4, Eqs. (4.15)-(4.16), p. 91: with eps_z = 0,
//! sigma_z = nu (sigma_x + sigma_y), and D on (eps_x, eps_y, gamma_xy).
//! Stresses tension-positive (spec 001, D1), stress vector
//! (sigma_xx, sigma_yy, sigma_zz, tau_xy).

/// The 3x3 matrix D of Eq. (4.16), on (eps_x, eps_y, gamma_xy).
pub fn plane_strain_matrix(young: f64, poisson: f64) -> [[f64; 3]; 3] {
    let factor = young * (1.0 - poisson) / ((1.0 + poisson) * (1.0 - 2.0 * poisson));
    let ratio = poisson / (1.0 - poisson);
    let shear = (1.0 - 2.0 * poisson) / (2.0 * (1.0 - poisson));
    [
        [factor, factor * ratio, 0.0],
        [factor * ratio, factor, 0.0],
        [0.0, 0.0, factor * shear],
    ]
}

/// (d_sigma_xx, d_sigma_yy, d_sigma_zz, d_tau_xy) for a strain increment
/// (d_eps_xx, d_eps_yy, d_gamma_xy): Eq. (4.16), and sigma_z of Eq. (4.15).
pub fn stress_increment(young: f64, poisson: f64, strain: [f64; 3]) -> [f64; 4] {
    let d = plane_strain_matrix(young, poisson);
    let s_xx = d[0][0] * strain[0] + d[0][1] * strain[1];
    let s_yy = d[1][0] * strain[0] + d[1][1] * strain[1];
    let t_xy = d[2][2] * strain[2];
    [s_xx, s_yy, poisson * (s_xx + s_yy), t_xy]
}
