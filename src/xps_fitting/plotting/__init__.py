"""Publication plotting API for immutable Phase 1 numerical results."""

from .aliases import canonical_core_level
from .diagnostic import plot_fit
from .export import export_figure
from .comparison import plot_fit_comparison
from .multipanel import plot_core_level_panel, plot_xps_series
from .palettes import CORE_LEVEL_COLOURS, component_colour, core_level_colour
from .themes import PlotTheme, load_theme, theme_context
from .validation import validate_result_curves
from .single import DISPLAY_MODES, plot_xps_fit

__all__ = ["CORE_LEVEL_COLOURS", "DISPLAY_MODES", "PlotTheme", "canonical_core_level", "component_colour", "core_level_colour", "export_figure", "load_theme", "plot_core_level_panel", "plot_fit", "plot_fit_comparison", "plot_xps_fit", "plot_xps_series", "theme_context", "validate_result_curves"]
