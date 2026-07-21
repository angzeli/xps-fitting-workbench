import copy

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from xps_fitting.plotting import VISIBLE_SPINE_WIDTH, export_figure, figure_size_preset, load_theme, plot_xps_fit
from xps_fitting.result import FitResult


def result_fixture() -> FitResult:
    energy = np.linspace(280, 292, 101)
    background = np.linspace(5, 7, energy.size)
    first = 20 * np.exp(-(((energy - 285) / 0.7) ** 2))
    second = 8 * np.exp(-(((energy - 288) / 0.9) ** 2))
    total = background + first + second
    raw = total + np.sin(energy) * 0.05
    return FitResult(
        energy,
        raw,
        background,
        {"aromatic_C-C_C=C": first, "imide_N-C=O": second},
        total,
        raw - total,
        {},
        fit_statistics={"aicc": 10, "bic": 12},
        configuration={"region": "C 1s"},
    )


def test_single_plot_layers_residual_and_no_mutation() -> None:
    result = result_fixture()
    before = copy.deepcopy(result.to_dict())
    figure, axes = plot_xps_fit(
        result,
        core_level="C1s",
        show_residual=True,
        component_display_mode="filled_to_background",
        peak_labels=True,
        area_percentages=True,
        fit_statistics=True,
    )
    assert isinstance(figure, Figure) and len(axes) == 2 and isinstance(axes[0], Axes)
    assert axes[0].xaxis_inverted()
    assert len(axes[0].lines) >= 5
    assert result.to_dict() == before
    assert any(label.startswith("Aromatic C=C/C–C") for label in axes[0].get_legend_handles_labels()[1])
    for axis in axes:
        assert all(
            spine.get_visible() and spine.get_linewidth() == VISIBLE_SPINE_WIDTH for spine in axis.spines.values()
        )
    assert tuple(figure.get_size_inches()) == figure_size_preset("detailed-publication")
    plt.close(figure)


def test_publication_hierarchy_and_legend_styling() -> None:
    theme = load_theme("angze_publication")
    figure, axis = plot_xps_fit(
        result_fixture(),
        core_level="C 1s",
        sample_label="PDI-H-COOH",
        component_display_mode="filled_to_background",
    )
    figure.canvas.draw()
    assert tuple(figure.get_size_inches()) == (8.0, 6.0)
    assert axis.get_title(loc="left") == "PDI-H-COOH"
    assert axis.get_title(loc="right") == "C 1s"
    assert all(spine.get_visible() and spine.get_linewidth() == 1.8 for spine in axis.spines.values())
    assert all(text.get_fontweight() == "bold" for text in (*axis.get_xticklabels(), *axis.get_yticklabels()))
    lines = {line.get_label(): line for line in axis.lines}
    assert lines["Total fit"].get_linewidth() == theme.fit_line_width == 2.0
    assert lines["Experimental"].get_markersize() == theme.marker_size == 4.0
    legend = axis.get_legend()
    assert legend is not None and legend.get_frame().get_visible()
    assert legend.get_frame().get_linewidth() == theme.legend_frame_linewidth == 1.0
    assert all(text.get_fontweight() == "bold" for text in legend.get_texts())
    legend_labels = [text.get_text() for text in legend.get_texts()]
    assert "Background" not in legend_labels
    assert legend_labels[:2] == ["Experimental", "Total fit"]
    assert "Aromatic C=C/C–C" in legend_labels
    assert axis.collections[0].get_alpha() == theme.component_alpha == 0.28
    assert axis.get_ylim()[1] > max(result_fixture().raw_intensity) * 1.08
    plt.close(figure)


def test_publication_exports(tmp_path) -> None:
    figure, axis = plot_xps_fit(result_fixture(), component_display_mode="lines")
    paths = export_figure(figure, tmp_path / "figure", formats=("png", "pdf"), metadata={"Title": "synthetic XPS"})
    assert isinstance(axis, Axes) and all(path.stat().st_size > 100 for path in paths.values())
    assert paths["png"].read_bytes().startswith(b"\x89PNG")
    assert paths["pdf"].read_bytes().startswith(b"%PDF")
    with pytest.raises(ValueError, match="No file was written"):
        export_figure(figure, tmp_path / "unsupported", formats=("png", "svg"))
    assert not (tmp_path / "unsupported.png").exists()
    assert not (tmp_path / "unsupported.svg").exists()
    plt.close(figure)


def test_deprecated_component_style_alias_remains_available() -> None:
    with pytest.warns(DeprecationWarning, match="component_style is deprecated"):
        figure, _ = plot_xps_fit(result_fixture(), component_style="hidden")
    plt.close(figure)
