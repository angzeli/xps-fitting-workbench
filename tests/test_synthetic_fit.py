"""Characterize deterministic multistart recovery and diagnostic export."""

import numpy as np
import pytest

from xps_fitting.configuration import FitConfig, PeakConfig
from xps_fitting.lineshapes import pseudo_voigt
from xps_fitting.optimiser import fit_spectrum
from xps_fitting.plotting import plot_fit
from xps_fitting.spectrum import Spectrum


def test_synthetic_recovery_is_deterministic(tmp_path) -> None:
    x = np.linspace(280, 292, 481)
    rng = np.random.default_rng(5)
    y = 20 + pseudo_voigt(x, 1000, 285.0, 1.3, 0.3) + rng.normal(0, 0.15, x.size)
    config = FitConfig(
        "one",
        "C 1s",
        [
            PeakConfig(
                "C-C", 284.8, (284.5, 285.5), 900, fwhm=1.5, fwhm_bounds=(1, 2), fraction=0.3, fixed=("fraction",)
            )
        ],
        multistart=2,
        random_seed=9,
    )
    first = fit_spectrum(Spectrum(x, y, region="C 1s"), config)
    second = fit_spectrum(Spectrum(x, y, region="C 1s"), config)
    assert first.fitted_parameters["C-C.centre"] == pytest.approx(285, abs=0.01)
    assert first.fitted_parameters["C-C.area"] == pytest.approx(1000, rel=0.02)
    assert first.fit_statistics["rss"] == second.fit_statistics["rss"]
    assert first.fit_statistics["rms_residual"] == pytest.approx(np.sqrt(np.mean(first.residual**2)))
    assert first.fit_statistics["residual_mean"] == pytest.approx(np.mean(first.residual))
    assert first.fit_statistics["max_abs_residual"] == pytest.approx(np.max(np.abs(first.residual)))
    assert first.convergence["backend"] == "lmfit"
    output = tmp_path / "diagnostic.png"
    plot_fit(first, output)
    assert output.stat().st_size > 0 and first.to_dict()["energy"][0] == 280
