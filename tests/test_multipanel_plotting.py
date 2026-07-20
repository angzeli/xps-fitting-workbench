import copy

import matplotlib.pyplot as plt
import numpy as np

from xps_fitting.plotting import VISIBLE_SPINE_WIDTH, export_figure, figure_size_preset, plot_fit_comparison, plot_xps_series
from xps_fitting.result import FitResult


def make_result(sample: str, scale: float = 1) -> FitResult:
    x = np.linspace(280, 292, 81); bg = np.full_like(x, 3.0); peak = scale * 10 * np.exp(-((x - 285) / 0.8) ** 2)
    total = bg + peak
    return FitResult(x, total, bg, {"aromatic_C-C_C=C": peak}, total, np.zeros_like(x), {"aromatic_C-C_C=C.centre": 285, "aromatic_C-C_C=C.fwhm": 1.3}, fit_statistics={"aicc": 10 / scale, "bic": 12 / scale}, configuration={"name": sample, "region": "C 1s"}, metadata={"sample_name": sample})


def test_series_consistency_labels_limits_legend_and_no_mutation(tmp_path) -> None:
    results = [make_result("PDI-H-COOH"), make_result("PDI-Me-COOH", 1.2), make_result("PDI-OMe-COOH", 0.8)]
    before = copy.deepcopy([result.to_dict() for result in results])
    figure, axes = plot_xps_series(results, x_limits=(292, 280), tick_spacing=2, normalised=True)
    assert all(axis.get_xlim() == axes[0, 0].get_xlim() for axis in axes.ravel())
    component_colours = [axis.collections[0].get_facecolor()[0].tolist() for axis in axes.ravel()]
    assert component_colours[0] == component_colours[1] == component_colours[2]
    assert [text.get_text() for text in axes[0, 0].texts][1] == "(a)"
    assert len(figure.legends) == 1 and [result.to_dict() for result in results] == before
    assert tuple(figure.get_size_inches()) == figure_size_preset("double-column")
    for axis in axes.ravel():
        assert all(spine.get_linewidth() == VISIBLE_SPINE_WIDTH for spine in axis.spines.values() if spine.get_visible())
    assert export_figure(figure, tmp_path / "series.pdf")["pdf"].stat().st_size > 100
    plt.close(figure)


def test_model_comparison_has_statistics_and_stability() -> None:
    figure, axes = plot_fit_comparison({"C1s_4": make_result("four"), "C1s_5": make_result("five", 1.1)}, show_residual=False)
    assert "AICc" in axes[0, 0].texts[-1].get_text()
    assert "aromatic_C-C_C=C" in figure._xps_component_stability
    plt.close(figure)
