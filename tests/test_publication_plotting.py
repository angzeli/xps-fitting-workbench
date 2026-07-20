import copy

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import numpy as np

from xps_fitting.plotting import export_figure, plot_xps_fit
from xps_fitting.result import FitResult


def result_fixture() -> FitResult:
    energy = np.linspace(280, 292, 101); background = np.linspace(5, 7, energy.size)
    first = 20 * np.exp(-((energy - 285) / 0.7) ** 2); second = 8 * np.exp(-((energy - 288) / 0.9) ** 2)
    total = background + first + second; raw = total + np.sin(energy) * 0.05
    return FitResult(energy, raw, background, {"aromatic_C-C_C=C": first, "imide_N-C=O": second}, total, raw - total, {}, fit_statistics={"aicc": 10, "bic": 12}, configuration={"region": "C 1s"})


def test_single_plot_layers_residual_and_no_mutation() -> None:
    result = result_fixture(); before = copy.deepcopy(result.to_dict())
    figure, axes = plot_xps_fit(result, core_level="C1s", show_residual=True, component_style="filled_to_background", peak_labels=True, area_percentages=True, fit_statistics=True)
    assert isinstance(figure, Figure) and len(axes) == 2 and isinstance(axes[0], Axes)
    assert axes[0].xaxis_inverted()
    assert len(axes[0].lines) >= 5
    assert result.to_dict() == before
    assert any(label.startswith("aromatic C-C/C=C") for label in axes[0].get_legend_handles_labels()[1])
    plt.close(figure)


def test_publication_exports(tmp_path) -> None:
    figure, axis = plot_xps_fit(result_fixture(), component_style="lines")
    paths = export_figure(figure, tmp_path / "figure", formats=("png", "svg", "pdf"), metadata={"Title": "synthetic XPS"})
    assert isinstance(axis, Axes) and all(path.stat().st_size > 100 for path in paths.values())
    assert paths["png"].read_bytes().startswith(b"\x89PNG")
    assert b"<svg" in paths["svg"].read_bytes()[:500]
    assert paths["pdf"].read_bytes().startswith(b"%PDF")
    plt.close(figure)
