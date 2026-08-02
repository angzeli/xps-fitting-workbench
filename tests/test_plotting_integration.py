"""Check numerical curve equivalence across supported plotting input paths."""

import json

import matplotlib.pyplot as plt
import numpy as np

from xps_fitting.configuration import FitConfig, PeakConfig
from xps_fitting.export import export_result
from xps_fitting.lineshapes import gaussian
from xps_fitting.optimiser import fit_spectrum
from xps_fitting.plotting import fit_result_from_dict, load_curve_result, plot_xps_fit, validate_result_curves
from xps_fitting.spectrum import Spectrum


def test_end_to_end_plot_sources_are_numerically_consistent(tmp_path) -> None:
    energy = np.linspace(280, 290, 201)
    intensity = 4 + gaussian(energy, 120, 285, 1.2)
    config = FitConfig(
        "integration",
        "C 1s",
        [
            PeakConfig(
                "aromatic_C-C_C=C", 284.8, (284.4, 285.4), 110, fwhm=1.4, fwhm_bounds=(1.0, 1.8), line_shape="gaussian"
            )
        ],
    )
    fitted = fit_spectrum(Spectrum(energy, intensity, region="C 1s"), config)
    validate_result_curves(fitted)
    paths = export_result(fitted, tmp_path, "integration")
    from_csv = load_curve_result(paths["csv"], paths["json"])
    from_xlsx = load_curve_result(paths["xlsx"], paths["json"])
    serialised_path = tmp_path / "full_result.json"
    serialised_path.write_text(json.dumps(fitted.to_dict()))
    from_json = load_curve_result(serialised_path)
    from_memory_dict = fit_result_from_dict(fitted.to_dict())
    for candidate in (from_csv, from_xlsx, from_json, from_memory_dict):
        validate_result_curves(candidate)
        np.testing.assert_allclose(candidate.energy, fitted.energy, rtol=0, atol=1e-12)
        np.testing.assert_allclose(candidate.total_fit, fitted.total_fit, rtol=1e-12, atol=1e-12)
        figure, axis = plot_xps_fit(candidate, component_display_mode="hidden")
        plotted_raw, plotted_background, plotted_total = (axis.lines[index].get_ydata() for index in range(3))
        np.testing.assert_allclose(plotted_raw, fitted.raw_intensity)
        np.testing.assert_allclose(plotted_background, fitted.background)
        np.testing.assert_allclose(plotted_total, fitted.total_fit)
        plt.close(figure)
