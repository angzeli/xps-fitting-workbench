"""Validated, local-only plotting themes."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
import math
from typing import Iterator

import matplotlib as mpl
from matplotlib.axes import Axes


VISIBLE_SPINE_WIDTH = 1.8
SUPPORTED_OUTPUT_FORMATS = frozenset({"png", "pdf"})
FIGURE_SIZE_PRESETS = {
    "single-column": (3.45, 2.8),
    "one-and-a-half-column": (5.2, 3.4),
    "double-column": (7.1, 3.8),
    "presentation": (8.0, 5.0),
}
_FIXED_SPINE_THEMES = frozenset({"angze_publication", "monochrome_publication", "presentation"})


@dataclass(frozen=True)
class PlotTheme:
    name: str
    font_family: str = "DejaVu Sans"
    font_size: float = 9
    axis_label_size: float = 10
    tick_label_size: float = 8
    title_size: float = 11
    spine_width: float = VISIBLE_SPINE_WIDTH
    tick_width: float = VISIBLE_SPINE_WIDTH
    tick_length: float = 4.0
    tick_direction: str = "in"
    marker: str = "o"
    marker_size: float = 3.0
    marker_edge_width: float = 0.8
    raw_face: str = "white"
    raw_edge: str = "#222222"
    fit_line_width: float = 2.0
    background_line_width: float = 1.1
    background_line_style: str = "--"
    component_line_width: float = 1.2
    component_alpha: float = 0.32
    legend_frame: bool = False
    legend_spacing: float = 0.35
    axis_padding: float = 4.0
    figure_size: tuple[float, float] = FIGURE_SIZE_PRESETS["single-column"]
    dpi: int = 300
    invert_binding_energy: bool = True
    residual_height_ratio: float = 0.28
    residual_zero_line: bool = True
    panel_label_template: str = "({label})"
    show_title: bool = False
    top_spine: bool = False
    right_spine: bool = False
    raster_transparent: bool = False
    vector_transparent: bool = True

    def __post_init__(self) -> None:
        if self.tick_direction not in {"in", "out", "inout"}:
            raise ValueError("tick_direction must be in, out, or inout")
        if self.dpi <= 0 or min(self.figure_size) <= 0 or not 0 <= self.component_alpha <= 1:
            raise ValueError("theme dimensions, DPI, and alpha must be valid")
        if min(self.spine_width, self.tick_width, self.marker_edge_width) <= 0:
            raise ValueError("spine, tick, and marker-edge widths must be positive")

    def rc_params(self) -> dict[str, object]:
        return {
            "font.family": self.font_family,
            "font.size": self.font_size,
            "axes.labelsize": self.axis_label_size,
            "axes.titlesize": self.title_size,
            "axes.labelweight": "bold",
            "axes.linewidth": self.spine_width,
            "xtick.labelsize": self.tick_label_size,
            "ytick.labelsize": self.tick_label_size,
            "xtick.direction": self.tick_direction,
            "ytick.direction": self.tick_direction,
            "xtick.major.width": self.tick_width,
            "ytick.major.width": self.tick_width,
            "xtick.major.size": self.tick_length,
            "ytick.major.size": self.tick_length,
            "axes.grid": False,
            "legend.frameon": self.legend_frame,
            "legend.fontsize": self.tick_label_size,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.dpi": self.dpi,
        }


_THEMES = {
    "angze_publication": PlotTheme("angze_publication"),
    "angze_diagnostic": PlotTheme("angze_diagnostic", figure_size=(5.8, 4.4), show_title=True, top_spine=True, right_spine=True, component_alpha=0.18),
    "monochrome_publication": PlotTheme("monochrome_publication", component_alpha=0.12, raw_edge="#000000"),
    "presentation": PlotTheme("presentation", font_size=15, axis_label_size=17, tick_label_size=13, title_size=18, tick_length=6, marker_size=5, fit_line_width=3, figure_size=FIGURE_SIZE_PRESETS["presentation"], show_title=True),
}


def figure_size_preset(name: str) -> tuple[float, float]:
    key = name.strip().lower().replace("_", "-")
    try:
        return FIGURE_SIZE_PRESETS[key]
    except KeyError as exc:
        raise ValueError(f"unknown figure-size preset {name!r}; choose from {sorted(FIGURE_SIZE_PRESETS)}") from exc


def validate_theme(
    theme: PlotTheme,
    *,
    output_formats: tuple[str, ...] | None = None,
    assignment_colours: dict[str, str] | None = None,
    required_assignments: tuple[str, ...] | None = None,
) -> PlotTheme:
    if theme.name in _FIXED_SPINE_THEMES and not math.isclose(theme.spine_width, VISIBLE_SPINE_WIDTH, abs_tol=1e-12):
        raise ValueError(f"{theme.name} requires a {VISIBLE_SPINE_WIDTH:.1f} pt spine width")
    if not 0 <= theme.component_alpha <= 1:
        raise ValueError("component_alpha must be between 0 and 1")
    if not (theme.fit_line_width >= theme.component_line_width >= theme.background_line_width > 0):
        raise ValueError("line-width hierarchy must be fit >= component >= background > 0")
    if output_formats is not None:
        unsupported = sorted({item.lower() for item in output_formats} - SUPPORTED_OUTPUT_FORMATS)
        if unsupported:
            raise ValueError(f"unsupported output format(s): {', '.join(unsupported)}; use PNG or PDF")
    if required_assignments is not None:
        colours = assignment_colours or {}
        missing = sorted(set(required_assignments) - set(colours))
        if missing:
            raise ValueError(f"missing assignment colour(s): {', '.join(missing)}")
    return theme


def load_theme(theme: str | PlotTheme = "angze_publication", **overrides) -> PlotTheme:
    selected = theme if isinstance(theme, PlotTheme) else _THEMES.get(theme)
    if selected is None:
        raise ValueError(f"unknown theme {theme!r}; choose from {sorted(_THEMES)}")
    if "name" in overrides:
        raise ValueError("theme name cannot be overridden")
    try:
        selected = replace(selected, **overrides) if overrides else selected
    except TypeError as exc:
        raise ValueError(f"unrecognised theme override: {exc}") from exc
    return validate_theme(selected)


def style_axes(axis: Axes, theme: PlotTheme, *, top: bool | None = None, right: bool | None = None) -> None:
    """Apply the theme to every visible spine and tick without changing global state."""
    top_visible = theme.top_spine if top is None else top
    right_visible = theme.right_spine if right is None else right
    axis.spines["top"].set_visible(top_visible)
    axis.spines["right"].set_visible(right_visible)
    for spine in axis.spines.values():
        spine.set_linewidth(theme.spine_width)
    axis.tick_params(
        direction=theme.tick_direction,
        length=theme.tick_length,
        width=theme.tick_width,
        top=top_visible,
        right=right_visible,
    )
    axis.grid(False)


@contextmanager
def theme_context(theme: str | PlotTheme = "angze_publication", **overrides) -> Iterator[PlotTheme]:
    selected = load_theme(theme, **overrides)
    with mpl.rc_context(selected.rc_params()):
        yield selected
