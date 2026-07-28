import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib import font_manager
from matplotlib.text import Text

from xps_fitting.plotting import (
    PlotConfig,
    PlotTheme,
    export_figure,
    plot_fit,
    plot_fit_comparison,
    plot_xps_fit,
    plot_xps_series,
)
from xps_fitting.plotting.survey import plot_survey_from_config
from xps_fitting.result import FitResult
from xps_fitting.spectrum import Spectrum
from xps_vgd_utils import plot_normalised_xps


def _result() -> FitResult:
    energy = np.linspace(280.0, 292.0, 81)
    background = np.full_like(energy, 3.0)
    component = 10 * np.exp(-(((energy - 285.0) / 0.8) ** 2))
    total = background + component
    return FitResult(
        energy,
        total,
        background,
        {"aromatic_C-C_C=C": component},
        total,
        np.zeros_like(energy),
        {"aromatic_C-C_C=C.centre": 285.0},
        configuration={"region": "C 1s"},
        metadata={"sample_name": "PDI-H-COOH"},
    )


def _assert_visible_text_family(figure, family: str = "Arial") -> None:
    figure.canvas.draw()
    texts = [artist for artist in figure.findobj(match=Text) if artist.get_visible() and artist.get_text()]
    assert texts
    assert all(artist.get_fontfamily() == [family] for artist in texts)
    assert all(artist.get_math_fontfamily() == "stix" for artist in texts)


def test_single_multipanel_and_comparison_figures_request_arial() -> None:
    single, _ = plot_xps_fit(_result(), fit_statistics=True, show_peak_positions=True)
    multipanel, _ = plot_xps_series([_result(), _result()])
    comparison, _ = plot_fit_comparison([_result(), _result()], show_residual=False)

    _assert_visible_text_family(single)
    _assert_visible_text_family(multipanel)
    _assert_visible_text_family(comparison)

    plt.close(single)
    plt.close(multipanel)
    plt.close(comparison)


def test_survey_figure_requests_arial(tmp_path) -> None:
    spectrum = Spectrum(
        np.linspace(0.0, 1200.0, 121),
        np.linspace(100.0, 200.0, 121),
        region="Survey",
        sample_name="PDI-H-COOH",
    )
    config = PlotConfig(output_formats=("png",), output_filename="survey", core_level="Survey")

    figure, _, _ = plot_survey_from_config(spectrum, config, tmp_path)

    _assert_visible_text_family(figure)
    plt.close(figure)


def test_diagnostic_figure_requests_arial() -> None:
    figure = plot_fit(_result())

    _assert_visible_text_family(figure)
    plt.close(figure)


def test_legacy_notebook_helper_requests_arial(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(plt, "show", lambda: None)
    data = pd.DataFrame(
        {
            "binding_energy_eV": [292.0, 286.0, 280.0],
            "normalised_intensity": [0.0, 1.0, 0.0],
            "core_level": ["C1s"] * 3,
            "spectrum_index": [0] * 3,
        }
    )

    plot_normalised_xps(data, tmp_path, "legacy", "Legacy C 1s", save=False)
    figure = plt.gcf()

    _assert_visible_text_family(figure)
    plt.close(figure)


def test_export_changes_only_the_requested_text_family(tmp_path) -> None:
    figure, axis = plt.subplots()
    text = axis.text(
        0.25,
        0.75,
        "Styled text",
        fontsize=13,
        fontweight="bold",
        fontstyle="italic",
        color="#123456",
        ha="right",
        va="top",
    )
    before = (
        text.get_fontsize(),
        text.get_fontweight(),
        text.get_fontstyle(),
        text.get_color(),
        text.get_ha(),
        text.get_va(),
        text.get_position(),
    )

    export_figure(
        figure,
        tmp_path / "custom-font.png",
        theme=PlotTheme("custom", font_family="Liberation Sans"),
    )

    assert text.get_fontfamily() == ["Liberation Sans"]
    assert (
        text.get_fontsize(),
        text.get_fontweight(),
        text.get_fontstyle(),
        text.get_color(),
        text.get_ha(),
        text.get_va(),
        text.get_position(),
    ) == before
    plt.close(figure)


def test_pdf_embeds_arial_text_and_stix_math_when_arial_is_installed(tmp_path) -> None:
    try:
        font_manager.findfont("Arial", fallback_to_default=False)
    except ValueError:
        pytest.skip("Arial is not installed on this rendering host")
    figure, axis = plt.subplots()
    axis.plot([0, 1], [0, 1], label=r"Signal $\alpha^2$")
    axis.set_title(r"Ordinary text, $\chi_\nu^2$, and $\mathbf{R}^2$", fontweight="bold")
    axis.set_xlabel(r"Binding energy ($\mathrm{eV}$)")
    axis.annotate(r"$\beta^3$", (0.5, 0.5))
    axis.text(0.1, 0.8, "Italic text", fontstyle="italic")
    axis.legend()

    path = export_figure(figure, tmp_path / "arial.pdf")["pdf"]
    payload = path.read_bytes()
    font_names = {
        match.decode("ascii")
        for match in re.findall(rb"/(?:BaseFont|FontName)\s*/(?:[A-Z]{6}\+)?([^\s/<>()\[\]]+)", payload)
    }

    assert font_names
    assert {
        "ArialMT",
        "Arial-ItalicMT",
        "Arial-BoldMT",
        "STIXGeneral-Regular",
        "STIXGeneral-Italic",
        "STIXGeneral-Bold",
    }.issubset(font_names)
    assert all(name.startswith(("Arial", "STIXGeneral")) for name in font_names)
    assert b"DejaVu" not in payload
    assert b"/FontFile2" in payload
    plt.close(figure)
