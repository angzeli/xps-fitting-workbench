"""Visually compare ordered alternative fitted hypotheses."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import numpy as np
from matplotlib.figure import Figure

from ..result import FitResult
from .multipanel import plot_xps_series
from .themes import PlotTheme, _apply_figure_font_family, load_theme


def plot_fit_comparison(
    results: Mapping[str, FitResult] | Sequence[FitResult],
    *,
    names: Sequence[str] | None = None,
    theme: str | PlotTheme = "angze_publication",
    show_residual: bool = True,
    show_peak_positions: bool = False,
) -> tuple[Figure, np.ndarray]:
    """Compare statistics and component stability without claiming chemical truth.

    Mapping or sequence order determines panel order. AICc/BIC and warnings are
    copied from stored results, while shared component centres and FWHM values are
    attached as private figure metadata for downstream inspection.
    """
    if isinstance(results, Mapping):
        model_names, values = list(results), list(results.values())
    else:
        values = list(results)
        model_names = list(
            names or [result.configuration.get("name", f"Model {index + 1}") for index, result in enumerate(values)]
        )
    grid = len(values) >= 3
    figure, axes = plot_xps_series(
        values,
        theme=theme,
        layout="grid" if grid else "horizontal",
        nrows=math.ceil(len(values) / 2) if grid else None,
        ncols=2 if grid else None,
        sample_labels=model_names,
        panel_labels=[chr(97 + index) for index in range(len(values))],
        shared_legend=True,
        show_residual=show_residual,
        show_peak_positions=show_peak_positions,
    )
    for result, axis in zip(values, axes.ravel()):
        stats = result.fit_statistics
        warning = f"{len(result.warnings)} warning{'s' if len(result.warnings) != 1 else ''}"
        axis.text(
            0.97,
            0.78,
            f"AICc {stats.get('aicc', np.nan):.3g}\nBIC {stats.get('bic', np.nan):.3g}\n{warning}",
            transform=axis.transAxes,
            ha="right",
            va="top",
            fontsize=8,
        )
    common = set.intersection(*(set(result.components) for result in values)) if values else set()
    stability = {}
    for label in sorted(common):
        centres = [result.fitted_parameters.get(f"{label}.centre") for result in values]
        widths = [result.fitted_parameters.get(f"{label}.fwhm") for result in values]
        stability[label] = {"centres": centres, "fwhms": widths}
    # Intentional private metadata is the machine-readable companion to the visual.
    figure._xps_component_stability = stability
    if figure.legends:
        figure.legends[0].set_title(
            "Statistical preference does not prove chemical correctness.",
            prop={"size": 8, "weight": "normal"},
        )
    _apply_figure_font_family(figure, load_theme(theme).font_family)
    return figure, axes
