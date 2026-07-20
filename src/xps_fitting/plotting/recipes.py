"""Apply a validated recipe to a FitResult."""

from __future__ import annotations

from pathlib import Path

from ..result import FitResult
from .configuration import PlotConfig
from .export import export_figure
from .single import plot_xps_fit
from .themes import load_theme


def plot_from_config(result: FitResult, config: PlotConfig, output_directory: str | Path = "."):
    overrides = {}
    for field_name in ("figure_size", "fit_line_width", "component_line_width", "marker_size"):
        value = getattr(config, field_name)
        if value is not None: overrides[field_name] = value
    theme = load_theme(config.theme, **overrides)
    disclosure = "; ".join(value for value in (config.normalisation_disclosure, config.intensity_offset_disclosure) if value)
    figure, axes = plot_xps_fit(
        result, theme=theme, core_level=config.core_level, component_style=config.component_display_mode,
        show_residual=config.residual_panel, tick_spacing=config.tick_spacing, x_limits=config.x_limits,
        legend_order=config.legend_order, label_map=config.labels, component_colours=config.component_colour_overrides,
        fit_colour=config.core_level_colour, sample_label=disclosure or None,
    )
    paths = export_figure(figure, Path(output_directory) / config.output_filename, formats=config.output_formats, theme=theme, transparent=config.transparent, metadata={str(key): str(value) for key, value in config.metadata.items()})
    return figure, axes, paths
