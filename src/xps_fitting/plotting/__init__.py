"""Plot immutable Phase 1 results without recomputing scientific curves.

This package exposes Phase 2 rendering, recipe, theme, and export utilities. It
accepts stored Phase 1 arrays as authoritative and never refits or reconstructs
missing raw intensity or background data.
"""

from .aliases import canonical_core_level
from .comparison import plot_fit_comparison
from .configuration import PlotConfig, load_plot_config
from .diagnostic import plot_fit
from .export import export_figure
from .io import fit_result_from_dict, load_curve_result
from .multipanel import plot_core_level_panel, plot_xps_series
from .palettes import CORE_LEVEL_COLOURS, component_colour, core_level_colour
from .recipes import plot_from_config, plot_series_from_config
from .single import DISPLAY_MODES, plot_xps_fit
from .themes import (
    FIGURE_SIZE_PRESETS,
    VISIBLE_SPINE_WIDTH,
    PlotTheme,
    figure_size_preset,
    fitted_region_y_limits,
    load_theme,
    style_axes,
    theme_context,
    validate_theme,
)
from .validation import validate_result_curves

__all__ = [
    "CORE_LEVEL_COLOURS",
    "DISPLAY_MODES",
    "FIGURE_SIZE_PRESETS",
    "VISIBLE_SPINE_WIDTH",
    "PlotConfig",
    "PlotTheme",
    "canonical_core_level",
    "component_colour",
    "core_level_colour",
    "export_figure",
    "fitted_region_y_limits",
    "figure_size_preset",
    "fit_result_from_dict",
    "load_curve_result",
    "load_plot_config",
    "load_theme",
    "plot_core_level_panel",
    "plot_fit",
    "plot_fit_comparison",
    "plot_from_config",
    "plot_series_from_config",
    "plot_xps_fit",
    "plot_xps_series",
    "style_axes",
    "theme_context",
    "validate_result_curves",
    "validate_theme",
]
