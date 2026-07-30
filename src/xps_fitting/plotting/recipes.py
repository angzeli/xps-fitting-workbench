"""Apply a validated recipe to a FitResult."""

from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from ..naming import validate_output_stem
from ..result import FitResult
from .configuration import PlotConfig
from .export import export_figure
from .multipanel import plot_xps_series
from .single import plot_xps_fit
from .themes import PlotTheme, figure_size_preset, load_theme


def _theme_from_config(config: PlotConfig) -> PlotTheme:
    overrides: dict[str, object] = {}
    if config.figure_size_preset is not None:
        overrides["figure_size"] = figure_size_preset(config.figure_size_preset)
    for field_name in ("figure_size", "fit_line_width", "component_line_width", "marker_size", "dpi"):
        value = getattr(config, field_name)
        if value is not None:
            overrides[field_name] = value
    if config.peak_label_fontsize is not None:
        overrides["peak_annotation_size"] = config.peak_label_fontsize
    if config.peak_annotation_leader_width is not None:
        overrides["peak_annotation_leader_width"] = config.peak_annotation_leader_width
    return load_theme(config.theme, **overrides)


def plot_from_config(
    result: FitResult,
    config: PlotConfig,
    output_directory: str | Path = ".",
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> tuple[Figure, Axes | np.ndarray, dict[str, Path]]:
    """Render and export one result according to a validated plot recipe."""
    theme = _theme_from_config(config)
    disclosure = "; ".join(
        value for value in (config.normalisation_disclosure, config.intensity_offset_disclosure) if value
    )
    figure, axes = plot_xps_fit(
        result,
        theme=theme,
        core_level=config.core_level,
        component_display_mode=config.component_display_mode,
        show_residual=config.residual_panel,
        tick_spacing=config.tick_spacing,
        x_minor_interval=config.x_minor_interval,
        show_y_ticks=config.show_y_ticks,
        show_top_ticks=config.show_top_ticks,
        x_limits=config.x_limits,
        legend_order=config.legend_order,
        label_map=config.labels,
        component_colours=config.component_colour_overrides,
        fit_colour=config.core_level_colour,
        sample_label=disclosure or None,
        show_sample_title=config.show_sample_title,
        core_level_label_position=config.core_level_label_position,
        show_peak_positions=config.show_peak_positions,
        peak_position_precision=config.peak_position_precision,
        peak_position_unit=config.peak_position_unit,
        peak_annotation_leaders=config.peak_annotation_leaders,
        peak_annotation_offsets=config.peak_annotation_offsets,
        peak_annotations=config.peak_annotations,
        annotate_negligible_components=config.annotate_negligible_components,
        annotate_hidden_components=config.annotate_hidden_components,
    )
    output_filename = validate_output_stem(config.output_filename)
    paths = export_figure(
        figure,
        Path(output_directory) / output_filename,
        formats=config.output_formats,
        theme=theme,
        transparent=config.transparent,
        metadata={str(key): str(value) for key, value in config.metadata.items()},
        overwrite=overwrite,
        dry_run=dry_run,
    )
    return figure, axes, paths


def plot_series_from_config(
    results: Sequence[FitResult],
    config: PlotConfig,
    output_directory: str | Path = ".",
    *,
    sample_labels: Sequence[str] | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> tuple[Figure, np.ndarray, dict[str, Path]]:
    """Render and export two or more results according to a multipanel recipe."""
    if len(results) < 2:
        raise ValueError("multipanel plotting requires at least two fit results")
    if config.panel_layout == "single":
        raise ValueError("a multi-input plot recipe must set panel_layout to horizontal, vertical, or grid")
    theme = _theme_from_config(config)
    nrows = ncols = None
    if config.panel_layout == "grid":
        ncols = math.ceil(math.sqrt(len(results)))
        nrows = math.ceil(len(results) / ncols)
    figure, axes = plot_xps_series(
        results,
        theme=theme,
        layout=config.panel_layout,
        nrows=nrows,
        ncols=ncols,
        sample_labels=sample_labels,
        panel_labels=config.panel_labels or None,
        core_levels=config.core_level,
        show_components=config.component_display_mode != "hidden",
        x_limits=config.x_limits,
        tick_spacing=config.tick_spacing,
        normalised=bool(config.normalisation_disclosure),
        label_map=config.labels,
        show_peak_positions=config.show_peak_positions,
        peak_position_precision=config.peak_position_precision,
        peak_position_unit=config.peak_position_unit,
        peak_annotation_leaders=config.peak_annotation_leaders,
        peak_annotation_offsets=config.peak_annotation_offsets,
        peak_annotations=config.peak_annotations,
        annotate_negligible_components=config.annotate_negligible_components,
        annotate_hidden_components=config.annotate_hidden_components,
    )
    output_filename = validate_output_stem(config.output_filename)
    paths = export_figure(
        figure,
        Path(output_directory) / output_filename,
        formats=config.output_formats,
        theme=theme,
        transparent=config.transparent,
        metadata={str(key): str(value) for key, value in config.metadata.items()},
        overwrite=overwrite,
        dry_run=dry_run,
    )
    return figure, axes, paths
