"""Visual comparison of alternative fitted hypotheses."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
from matplotlib.figure import Figure

from ..result import FitResult
from .multipanel import plot_xps_series
from .themes import PlotTheme


def plot_fit_comparison(
    results: Mapping[str, FitResult] | Sequence[FitResult],
    *,
    names: Sequence[str] | None = None,
    theme: str | PlotTheme = "angze_publication",
    show_residual: bool = True,
    show_peak_positions: bool = False,
) -> tuple[Figure, np.ndarray]:
    """Compare statistics and component stability without claiming chemical truth."""
    if isinstance(results, Mapping):
        model_names, values = list(results), list(results.values())
    else:
        values = list(results)
        model_names = list(
            names or [result.configuration.get("name", f"Model {index + 1}") for index, result in enumerate(values)]
        )
    figure, axes = plot_xps_series(
        values,
        theme=theme,
        layout="horizontal",
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
    figure._xps_component_stability = stability  # machine-readable companion to the visual
    figure.text(0.5, 0.005, "Statistical preference does not prove chemical correctness.", ha="center", fontsize=8)
    return figure, axes
