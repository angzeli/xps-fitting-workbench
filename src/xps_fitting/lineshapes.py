"""Area-normalised peak line shapes using FWHM throughout."""

from __future__ import annotations

import numpy as np
from scipy.special import voigt_profile


def gaussian(x: np.ndarray, area: float, centre: float, fwhm: float) -> np.ndarray:
    """Evaluate an area-normalised Gaussian using coordinates and FWHM in like units."""
    sigma = fwhm / (2 * np.sqrt(2 * np.log(2)))
    return area * np.exp(-0.5 * ((x - centre) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))


def lorentzian(x: np.ndarray, area: float, centre: float, fwhm: float) -> np.ndarray:
    """Evaluate an area-normalised Lorentzian using coordinates and FWHM in like units."""
    gamma = fwhm / 2
    return area * gamma / (np.pi * ((x - centre) ** 2 + gamma**2))


def pseudo_voigt(x: np.ndarray, area: float, centre: float, fwhm: float, fraction: float = 0.5) -> np.ndarray:
    """Mix equal-FWHM Lorentzian and Gaussian profiles by Lorentzian fraction."""
    if not 0 <= fraction <= 1:
        raise ValueError("fraction must lie in [0, 1]")
    return fraction * lorentzian(x, area, centre, fwhm) + (1 - fraction) * gaussian(x, area, centre, fwhm)


def voigt(x: np.ndarray, area: float, centre: float, fwhm_g: float, fwhm_l: float) -> np.ndarray:
    """Evaluate an area-normalised Voigt profile from Gaussian and Lorentzian FWHM."""
    sigma = fwhm_g / (2 * np.sqrt(2 * np.log(2)))
    gamma = fwhm_l / 2
    return area * voigt_profile(x - centre, sigma, gamma)


LINE_SHAPES = {"gaussian": gaussian, "lorentzian": lorentzian, "pseudo_voigt": pseudo_voigt, "voigt": voigt}
