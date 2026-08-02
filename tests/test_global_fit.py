"""Verify two-pass consensus shapes while retaining spectrum-specific areas."""

import numpy as np

from xps_fitting.configuration import FitConfig, PeakConfig
from xps_fitting.global_fit import fit_shared_shapes
from xps_fitting.lineshapes import pseudo_voigt
from xps_fitting.spectrum import Spectrum


def test_two_pass_global_shapes_are_linked() -> None:
    x = np.linspace(0, 10, 201)
    spectra = [Spectrum(x, 2 + pseudo_voigt(x, area, 5 + shift, 1.2, 0.3)) for area, shift in [(100, 0), (180, 0.1)]]
    config = FitConfig(
        "shared",
        "test",
        [PeakConfig("p", 5, (4.5, 5.5), 120, fwhm=1.4, fwhm_bounds=(0.8, 1.8), fraction=0.3, fixed=("fraction",))],
    )
    results = fit_shared_shapes(spectra, config, shared=("fwhm",))
    assert results[0].fitted_parameters["p.fwhm"] == results[1].fitted_parameters["p.fwhm"]
    assert results[0].fitted_parameters["p.area"] != results[1].fitted_parameters["p.area"]
