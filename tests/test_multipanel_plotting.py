import copy

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np

from xps_fitting.plotting import (
    VISIBLE_SPINE_WIDTH,
    component_colour,
    export_figure,
    figure_size_preset,
    plot_fit_comparison,
    plot_xps_series,
)
from xps_fitting.result import FitResult


def make_result(sample: str, scale: float = 1) -> FitResult:
    x = np.linspace(280, 292, 81)
    bg = np.full_like(x, 3.0)
    peak = scale * 10 * np.exp(-(((x - 285) / 0.8) ** 2))
    total = bg + peak
    return FitResult(
        x,
        total,
        bg,
        {"aromatic_C-C_C=C": peak},
        total,
        np.zeros_like(x),
        {"aromatic_C-C_C=C.centre": 285, "aromatic_C-C_C=C.fwhm": 1.3},
        fit_statistics={"aicc": 10 / scale, "bic": 12 / scale},
        configuration={"name": sample, "region": "C 1s"},
        metadata={"sample_name": sample},
    )


def test_series_consistency_labels_limits_legend_and_no_mutation(tmp_path) -> None:
    results = [make_result("PDI-H-COOH"), make_result("PDI-Me-COOH", 1.2), make_result("PDI-OMe-COOH", 0.8)]
    before = copy.deepcopy([result.to_dict() for result in results])
    figure, axes = plot_xps_series(results, x_limits=(292, 280), tick_spacing=2, normalised=True)
    assert all(axis.get_xlim() == axes[0, 0].get_xlim() for axis in axes.ravel())
    component_colours = [axis.collections[0].get_facecolor()[0].tolist() for axis in axes.ravel()]
    assert component_colours[0] == component_colours[1] == component_colours[2]
    assert axes[0, 0].get_title(loc="left").startswith("(a) PDI-H-COOH")
    assert axes[0, 0].get_title(loc="right") == "C 1s"
    assert len(figure.legends) == 1 and [result.to_dict() for result in results] == before
    assert "Background" not in [text.get_text() for text in figure.legends[0].get_texts()]
    assert figure.legends[0].get_frame().get_visible()
    assert all(text.get_fontweight() == "bold" for text in figure.legends[0].get_texts())
    assert tuple(figure.get_size_inches()) == figure_size_preset("double-column")
    for axis in axes.ravel():
        assert all(
            spine.get_visible() and spine.get_linewidth() == VISIBLE_SPINE_WIDTH for spine in axis.spines.values()
        )
    assert export_figure(figure, tmp_path / "series.pdf")["pdf"].stat().st_size > 100
    plt.close(figure)


def test_model_comparison_has_statistics_and_stability() -> None:
    figure, axes = plot_fit_comparison(
        {"C1s_4": make_result("four"), "C1s_5": make_result("five", 1.1)}, show_residual=False
    )
    assert "AICc" in axes[0, 0].texts[-1].get_text()
    assert "aromatic_C-C_C=C" in figure._xps_component_stability
    assert "chemical correctness" in figure.legends[0].get_title().get_text()
    plt.close(figure)


def test_multipanel_uses_the_plain_satellite_label_and_semantic_colour() -> None:
    energy = np.linspace(286, 294, 81)
    background = np.full_like(energy, 4.0)
    satellite = 3 * np.exp(-(((energy - 291) / 0.8) ** 2))
    total = background + satellite
    results = [
        FitResult(
            energy,
            total,
            background,
            {"pi-pi_star": satellite},
            total,
            np.zeros_like(energy),
            {"pi-pi_star.centre": 291.0},
            metadata={"sample_name": sample},
        )
        for sample in ("PDI-H-COOH", "PDI-OMe-COOH")
    ]
    figure, axes = plot_xps_series(results)
    labels = [text.get_text() for text in figure.legends[0].get_texts()]
    assert "π–π* satellite" in labels
    assert all(text.get_fontweight() == "bold" for text in figure.legends[0].get_texts())
    expected = mcolors.to_rgb(component_colour("pi-pi_star"))
    assert all(
        collection.get_facecolor()[0][:3].tolist() == list(expected)
        for axis in axes.ravel()
        for collection in axis.collections
    )
    plt.close(figure)
