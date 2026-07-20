"""Publication plotting API for immutable Phase 1 numerical results."""

from .aliases import canonical_core_level
from .diagnostic import plot_fit
from .palettes import CORE_LEVEL_COLOURS, component_colour, core_level_colour
from .themes import PlotTheme, load_theme, theme_context
from .validation import validate_result_curves

__all__ = ["CORE_LEVEL_COLOURS", "PlotTheme", "canonical_core_level", "component_colour", "core_level_colour", "load_theme", "plot_fit", "theme_context", "validate_result_curves"]
