"""Area-normalised peak profiles on coordinate arrays expressed in like units."""

from __future__ import annotations

import numpy as np
from scipy.special import voigt_profile


def gaussian(x: np.ndarray, area: float, centre: float, fwhm: float) -> np.ndarray:
    """Evaluate a Gaussian on ``x`` with integral ``area`` and the supplied FWHM."""
    sigma = fwhm / (2 * np.sqrt(2 * np.log(2)))
    return area * np.exp(-0.5 * ((x - centre) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))


def lorentzian(x: np.ndarray, area: float, centre: float, fwhm: float) -> np.ndarray:
    """Evaluate a Lorentzian on ``x`` with integral ``area`` and supplied FWHM."""
    gamma = fwhm / 2
    return area * gamma / (np.pi * ((x - centre) ** 2 + gamma**2))


def pseudo_voigt(x: np.ndarray, area: float, centre: float, fwhm: float, fraction: float = 0.5) -> np.ndarray:
    """Mix equal-FWHM profiles using a Lorentzian fraction in ``[0, 1]``."""
    if not 0 <= fraction <= 1:
        raise ValueError("fraction must lie in [0, 1]")
    return fraction * lorentzian(x, area, centre, fwhm) + (1 - fraction) * gaussian(x, area, centre, fwhm)


def voigt(x: np.ndarray, area: float, centre: float, fwhm_g: float, fwhm_l: float) -> np.ndarray:
    """Evaluate an area-normalised Voigt from Gaussian and Lorentzian FWHM values."""
    sigma = fwhm_g / (2 * np.sqrt(2 * np.log(2)))
    gamma = fwhm_l / 2
    return area * voigt_profile(x - centre, sigma, gamma)


LINE_SHAPES = {"gaussian": gaussian, "lorentzian": lorentzian, "pseudo_voigt": pseudo_voigt, "voigt": voigt}
