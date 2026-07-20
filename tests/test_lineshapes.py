import numpy as np
import pytest

from xps_fitting.lineshapes import gaussian, lorentzian, pseudo_voigt, voigt


def test_requested_area_is_recovered() -> None:
    x = np.linspace(-100, 100, 200_001)
    for curve in (gaussian(x, 7, 0, 2), lorentzian(x, 7, 0, 2), pseudo_voigt(x, 7, 0, 2, 0.3), voigt(x, 7, 0, 2, 1)):
        assert np.trapz(curve, x) == pytest.approx(7, rel=0.01)


def test_gaussian_and_lorentzian_fwhm() -> None:
    for function in (gaussian, lorentzian):
        assert function(np.array([1.0]), 1, 0, 2)[0] == pytest.approx(function(np.array([0.0]), 1, 0, 2)[0] / 2)
