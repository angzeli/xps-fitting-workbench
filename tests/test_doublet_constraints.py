import numpy as np
import pytest

from xps_fitting.configuration import FitConfig
from xps_fitting.constraints import cl2p_doublet
from xps_fitting.lineshapes import pseudo_voigt
from xps_fitting.optimiser import fit_spectrum
from xps_fitting.spectrum import Spectrum


def test_fitted_doublet_links_are_exact() -> None:
    x = np.linspace(195, 207, 401)
    y = 10 + pseudo_voigt(x, 900, 200, 1.2, 0.4) + pseudo_voigt(x, 450, 201.6, 1.2, 0.4)
    result = fit_spectrum(Spectrum(x, y), FitConfig("cl", "Cl 2p", cl2p_doublet("Cl", 199.8, 800, fraction=0.4)))
    p = result.fitted_parameters
    assert p["Cl_2p1/2.centre"] == pytest.approx(p["Cl_2p3/2.centre"] + 1.6)
    assert p["Cl_2p1/2.area"] == pytest.approx(p["Cl_2p3/2.area"] / 2)
    assert p["Cl_2p1/2.fwhm"] == p["Cl_2p3/2.fwhm"]
