"""Publication rendering for a reviewed raw Survey spectrum."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator

from ..spectrum import Spectrum
from .configuration import PlotConfig
from .export import export_figure
from .themes import PlotTheme, apply_vertical_headroom, figure_size_preset, load_theme, style_axes, theme_context


def _theme_from_config(config: PlotConfig) -> PlotTheme:
    overrides = {}
    if config.figure_size_preset is not None:
        overrides["figure_size"] = figure_size_preset(config.figure_size_preset)
    for field_name in ("figure_size", "fit_line_width", "marker_size", "dpi"):
        value = getattr(config, field_name)
        if value is not None:
            overrides[field_name] = value
    return load_theme(config.theme, **overrides)


def draw_survey_axis(axis: Axes, spectrum: Spectrum, theme: PlotTheme, config: PlotConfig) -> None:
    """Draw one immutable Survey trace on an existing axes."""
    energy = np.asarray(spectrum.binding_energy)
    intensity = np.asarray(spectrum.intensity)
    axis.plot(energy, intensity, color=config.core_level_colour or theme.fit_colour, linewidth=theme.fit_line_width)
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
        minimum=float(np.min(intensity)),
        maximum=float(np.max(intensity)),
        bottom=0.0,
    )
    style_axes(axis, theme, show_top_ticks=config.show_top_ticks, show_y_ticks=config.show_y_ticks)
    axis.set_xlabel("Binding energy (eV)")
    axis.set_ylabel("Intensity (a.u.)")
    if config.core_level:
        position = config.core_level_label_position or (0.97, 0.96)
        label = axis.text(
            *position,
            config.core_level,
            transform=axis.transAxes,
            ha="right",
            va="top",
            fontsize=theme.core_level_size,
            fontweight="bold",
        )
        label.set_gid("core-level-label")


def plot_survey_from_config(
    spectrum: Spectrum,
    config: PlotConfig,
    output_directory: str | Path,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> tuple[Figure, Axes, dict[str, Path]]:
    """Render and export one reviewed Survey without fitting or interpolation."""
    theme = _theme_from_config(config)
    with theme_context(theme):
        figure, axis = plt.subplots(figsize=theme.figure_size, layout="constrained")
        draw_survey_axis(axis, spectrum, theme, config)
    paths = export_figure(
        figure,
        Path(output_directory) / config.output_filename,
        formats=config.output_formats,
        theme=theme,
        transparent=config.transparent,
        metadata={str(key): str(value) for key, value in config.metadata.items()},
        overwrite=overwrite,
        dry_run=dry_run,
    )
    return figure, axis, paths
