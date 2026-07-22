"""Heterogeneous Survey plus fitted-region publication panel."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import cast

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator

from ..result import FitResult
from ..spectrum import Spectrum
from .annotations import PDI_H_C1S_LABELS
from .configuration import PlotConfig
from .export import export_figure
from .palettes import component_colour
from .survey import draw_survey_axis
from .themes import PlotTheme, apply_vertical_headroom, load_theme, style_axes, style_legend, theme_context

PANEL_REGIONS = ("Survey", "C1s", "N1s", "O1s", "Cl2p")


def _draw_fitted_axis(axis: Axes, result: FitResult, config: PlotConfig, theme: PlotTheme) -> None:
    energy = np.asarray(result.energy)
    raw = np.asarray(result.raw_intensity)
    background = np.asarray(result.background)
    total = np.asarray(result.total_fit)
    axis.plot(
        energy,
        raw,
        linestyle="none",
        marker=theme.marker,
        markersize=theme.marker_size,
        markerfacecolor=theme.raw_face,
        markeredgecolor=theme.raw_edge,
        markeredgewidth=theme.marker_edge_width,
        label="Experimental",
        zorder=7,
    )
    axis.plot(
        energy,
        background,
        theme.background_line_style,
        color="#555555",
        linewidth=theme.background_line_width,
        label="_nolegend_",
    )
    labels = {**PDI_H_C1S_LABELS, **config.labels}
    displayed = [raw, background, total]
    for label, curve in result.components.items():
        colour = component_colour(label, config.component_colour_overrides)
        component = background + np.asarray(curve)
        axis.fill_between(
            energy,
            background,
            component,
            color=colour,
            alpha=theme.component_alpha,
            label=labels.get(label, label),
        )
        axis.plot(energy, component, color=colour, linewidth=theme.component_line_width)
        displayed.append(component)
    axis.plot(
        energy,
        total,
        color=config.core_level_colour or theme.fit_colour,
        linewidth=theme.fit_line_width,
        label="Total fit",
        zorder=6,
    )
    if config.x_limits is not None:
        axis.set_xlim(config.x_limits)
    elif theme.invert_binding_energy and not axis.xaxis_inverted():
        axis.invert_xaxis()
    if config.tick_spacing is not None:
        axis.xaxis.set_major_locator(MultipleLocator(config.tick_spacing))
    if config.x_minor_interval is not None:
        axis.xaxis.set_minor_locator(MultipleLocator(config.x_minor_interval))
    apply_vertical_headroom(
        axis,
        theme,
        minimum=min(float(np.min(curve)) for curve in displayed),
        maximum=max(float(np.max(curve)) for curve in displayed),
        bottom=0.0,
    )
    style_axes(axis, theme, show_top_ticks=False, show_y_ticks=False)
    axis.set_xlabel("Binding energy (eV)")
    legend = axis.legend(loc="best", ncol=2 if len(result.components) > 3 else 1)
    style_legend(legend, theme)


def plot_sample_panel(
    datasets: Mapping[str, FitResult | Spectrum],
    configs: Mapping[str, PlotConfig],
    output_directory: str | Path,
    *,
    output_filename: str = "pdi_h_cooh_xps_panel",
    output_formats: tuple[str, ...] = ("png", "pdf"),
    dpi: int = 600,
    metadata: Mapping[str, str] | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> tuple[Figure, dict[str, Axes], dict[str, Path]]:
    """Render Survey wide above four fitted regions without recalculation."""
    missing = [region for region in PANEL_REGIONS if region not in datasets or region not in configs]
    if missing:
        raise ValueError("sample panel is missing regions or recipes: " + ", ".join(missing))
    if not isinstance(datasets["Survey"], Spectrum) or any(
        not isinstance(datasets[region], FitResult) for region in PANEL_REGIONS[1:]
    ):
        raise TypeError("sample panel requires one Survey Spectrum and four fitted-region results")
    theme = replace(load_theme("angze_publication").for_multipanel(), figure_size=(10.5, 10.0), dpi=dpi)
    with theme_context(theme):
        figure = plt.figure(figsize=theme.figure_size, layout="constrained")
        grid = figure.add_gridspec(3, 2, height_ratios=(0.72, 1.0, 1.0))
        axes = {
            "Survey": figure.add_subplot(grid[0, :]),
            "C1s": figure.add_subplot(grid[1, 0]),
            "N1s": figure.add_subplot(grid[1, 1]),
            "O1s": figure.add_subplot(grid[2, 0]),
            "Cl2p": figure.add_subplot(grid[2, 1]),
        }
        survey = cast(Spectrum, datasets["Survey"])
        draw_survey_axis(axes["Survey"], survey, theme, replace(configs["Survey"], core_level=None))
        for region in PANEL_REGIONS[1:]:
            _draw_fitted_axis(axes[region], cast(FitResult, datasets[region]), configs[region], theme)
        for index, region in enumerate(PANEL_REGIONS):
            axis = axes[region]
            axis.set_title(f"({chr(97 + index)})", loc="left", fontsize=theme.title_size, fontweight="bold")
            label = axis.text(
                0.97,
                0.94,
                configs[region].core_level or region,
                transform=axis.transAxes,
                ha="right",
                va="top",
                fontsize=theme.core_level_size,
                fontweight="semibold",
            )
            label.set_gid("core-level-label")
        axes["N1s"].set_ylabel("")
        axes["Cl2p"].set_ylabel("")
    paths = export_figure(
        figure,
        Path(output_directory) / output_filename,
        formats=output_formats,
        theme=theme,
        metadata=dict(metadata or {}),
        overwrite=overwrite,
        dry_run=dry_run,
    )
    return figure, axes, paths
