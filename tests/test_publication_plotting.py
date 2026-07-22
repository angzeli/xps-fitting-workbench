import copy
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from xps_fitting.plotting import (
    VISIBLE_SPINE_WIDTH,
    export_figure,
    figure_size_preset,
    fitted_region_y_limits,
    load_theme,
    plot_xps_fit,
)
from xps_fitting.plotting.configuration import load_plot_config
from xps_fitting.result import FitResult

ROOT = Path(__file__).resolve().parents[1]


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


@pytest.mark.parametrize(("region", "baseline"), [("C 1s", 4.0), ("N 1s", 24.0), ("O 1s", 22.0), ("Cl 2p", 2.0)])
def test_fitted_region_limits_are_baseline_relative_for_every_region(region, baseline) -> None:
    energy = np.linspace(0, 10, 101)
    background = np.linspace(baseline, baseline + 0.5, energy.size)
    component = 10 * np.exp(-(((energy - 5) / 0.8) ** 2))
    total = background + component
    raw = total + 0.02 * np.sin(energy)
    result = FitResult(
        energy,
        raw,
        background,
        {"aromatic_C-C_C=C": component},
        total,
        raw - total,
        {},
        configuration={"region": region},
    )

    figure, axis = plot_xps_fit(result, core_level=region, component_display_mode="filled_to_background")
    expected = fitted_region_y_limits(raw, background, total, load_theme("angze_publication"))
    assert axis.get_ylim() == pytest.approx(expected)
    assert axis.get_ylim()[0] > 0
    baseline_fraction = (float(np.median(background)) - expected[0]) / (expected[1] - expected[0])
    assert 0.03 <= baseline_fraction <= 0.18
    assert expected[1] > max(float(np.max(raw)), float(np.max(total)))
    assert expected[0] < min(float(np.min(raw)), float(np.min(background)), float(np.min(total)))
    plt.close(figure)


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


def test_plain_text_satellite_legend_is_fully_bold_and_exports(tmp_path) -> None:
    energy = np.linspace(286, 294, 81)
    background = np.full_like(energy, 4.0)
    satellite = 3 * np.exp(-(((energy - 291) / 0.8) ** 2))
    total = background + satellite
    result = FitResult(
        energy,
        total,
        background,
        {"pi-pi_star": satellite},
        total,
        np.zeros_like(energy),
        {"pi-pi_star.centre": 291.0},
    )
    figure, axis = plot_xps_fit(result, component_display_mode="filled_to_background")
    satellite_label = next(text for text in axis.get_legend().get_texts() if "satellite" in text.get_text())
    assert satellite_label.get_text() == "π–π* satellite"
    assert satellite_label.get_fontweight() == "bold"
    assert "$" not in satellite_label.get_text()
    paths = export_figure(figure, tmp_path / "plain-satellite", formats=("png", "pdf"))
    assert all(path.stat().st_size > 100 for path in paths.values())
    assert b"/FontFile2" in paths["pdf"].read_bytes()
    plt.close(figure)


def test_publication_tick_and_inside_title_controls() -> None:
    figure, axis = plot_xps_fit(
        result_fixture(),
        core_level="C 1s",
        sample_label="PDI-H-COOH",
        x_limits=(292, 280),
        tick_spacing=2,
        x_minor_interval=1,
        show_y_ticks=False,
        show_top_ticks=False,
        show_sample_title=False,
        core_level_label_position=(0.97, 0.96),
    )
    figure.canvas.draw()

    assert axis.get_title(loc="left") == ""
    assert axis.get_title(loc="right") == ""
    core_labels = [text for text in axis.texts if text.get_gid() == "core-level-label"]
    assert len(core_labels) == 1
    assert core_labels[0].get_text() == "C 1s"
    assert core_labels[0].get_position() == (0.97, 0.96)
    assert core_labels[0].get_transform() == axis.transAxes

    assert all(not tick.tick1line.get_visible() and not tick.tick2line.get_visible() for tick in axis.yaxis.majorTicks)
    assert all(not tick.label1.get_visible() and not tick.label2.get_visible() for tick in axis.yaxis.majorTicks)
    assert all(tick.tick1line.get_visible() and not tick.tick2line.get_visible() for tick in axis.xaxis.majorTicks)
    assert all(tick.tick1line.get_visible() and not tick.tick2line.get_visible() for tick in axis.xaxis.minorTicks)
    assert {round(value, 6) for value in axis.xaxis.get_minorticklocs() if 280 < value < 292} == {
        281,
        283,
        285,
        287,
        289,
        291,
    }
    assert all(tick.tick1line.get_markeredgewidth() == 1.8 for tick in axis.xaxis.majorTicks)
    assert all(tick.tick1line.get_markeredgewidth() == 1.2 for tick in axis.xaxis.minorTicks)
    assert all(
        tick.tick1line.get_markersize() < axis.xaxis.majorTicks[0].tick1line.get_markersize()
        for tick in axis.xaxis.minorTicks
    )
    assert all(spine.get_visible() and spine.get_linewidth() == 1.8 for spine in axis.spines.values())
    plt.close(figure)


def test_deprecated_component_style_alias_remains_available() -> None:
    with pytest.warns(DeprecationWarning, match="component_style is deprecated"):
        figure, _ = plot_xps_fit(result_fixture(), component_style="hidden")
    plt.close(figure)


def test_pdi_publication_recipes_have_exact_outputs_and_no_svg() -> None:
    expected = {
        "c1s_publication.json": ("C 1s", "pdi_h_cooh_c1s"),
        "n1s_publication.json": ("N 1s", "pdi_h_cooh_n1s"),
        "o1s_publication.json": ("O 1s", "pdi_h_cooh_o1s"),
        "cl2p_publication.json": ("Cl 2p", "pdi_h_cooh_cl2p"),
        "survey_publication.json": ("Survey", "pdi_h_cooh_survey"),
    }
    for filename, (core_level, output_name) in expected.items():
        config = load_plot_config(ROOT / "configs" / "plots" / filename)
        assert config.core_level == core_level
        assert config.output_filename == output_name
        assert config.output_formats == ("png", "pdf")
        assert config.dpi == 600
        assert config.show_y_ticks is False and config.show_top_ticks is False

    sample = json.loads((ROOT / "configs" / "plots" / "pdi_publication.json").read_text())
    assert sample["regions"] == ["Survey", "C1s", "N1s", "O1s", "Cl2p"]
    assert sample["output_filename"] == "pdi_h_cooh_xps_panel"
    assert sample["output_formats"] == ["png", "pdf"]
