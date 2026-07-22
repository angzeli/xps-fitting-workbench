"""Validated, local-only plotting themes."""

from __future__ import annotations

import math
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Any, Iterator

import matplotlib as mpl
import numpy as np
from matplotlib.axes import Axes
from matplotlib.legend import Legend

VISIBLE_SPINE_WIDTH = 1.8
SUPPORTED_OUTPUT_FORMATS = frozenset({"png", "pdf"})
FIGURE_SIZE_PRESETS = {
    "single-column": (3.45, 2.8),
    "one-and-a-half-column": (5.2, 3.4),
    "double-column": (7.1, 3.8),
    "detailed-publication": (8.0, 6.0),
    "presentation": (8.0, 5.0),
}
_FIXED_SPINE_THEMES = frozenset({"angze_publication", "monochrome_publication", "presentation"})


@dataclass(frozen=True)
class PlotTheme:
    name: str
    font_family: str = "DejaVu Sans"
    font_size: float = 14
    axis_label_size: float = 22
    tick_label_size: float = 14
    tick_label_weight: str = "bold"
    title_size: float = 18
    core_level_size: float = 16.5
    title_padding: float = 6
    peak_annotation_size: float = 10
    peak_annotation_offset_points: float = 10
    peak_annotation_stagger_points: float = 13
    peak_annotation_collision_fraction: float = 0.06
    peak_annotation_leader_width: float = 0.7
    peak_annotation_max_connector_points: float = 30
    peak_annotation_max_automatic_displacement_points: float = 35
    negligible_component_fraction: float = 0.01
    multipanel_axis_label_size: float = 10
    multipanel_tick_label_size: float = 9
    multipanel_title_size: float = 9
    multipanel_core_level_size: float = 8.5
    multipanel_legend_font_size: float = 9
    multipanel_peak_annotation_size: float = 8
    spine_width: float = VISIBLE_SPINE_WIDTH
    tick_width: float = VISIBLE_SPINE_WIDTH
    tick_length: float = 4.0
    minor_tick_width: float = 1.2
    minor_tick_length: float = 2.5
    tick_direction: str = "in"
    marker: str = "o"
    marker_size: float = 4.0
    marker_edge_width: float = 0.9
    raw_face: str = "white"
    raw_edge: str = "#222222"
    fit_colour: str = "#333333"
    fit_line_width: float = 2.0
    background_line_width: float = 1.3
    background_line_style: str = "--"
    component_line_width: float = 1.5
    component_alpha: float = 0.28
    legend_frame: bool = True
    legend_font_size: float = 11
    legend_font_weight: str = "bold"
    legend_face_colour: str = "white"
    legend_edge_colour: str = "#222222"
    legend_frame_alpha: float = 0.95
    legend_frame_linewidth: float = 1.0
    legend_fancybox: bool = False
    legend_spacing: float = 0.35
    axis_padding: float = 4.0
    figure_size: tuple[float, float] = FIGURE_SIZE_PRESETS["detailed-publication"]
    vertical_headroom: float = 0.1
    fitted_region_lower_padding: float = 0.06
    fitted_region_upper_padding: float = 0.12
    dpi: int = 300
    invert_binding_energy: bool = True
    residual_height_ratio: float = 0.28
    residual_zero_line: bool = True
    panel_label_template: str = "({label})"
    show_title: bool = False
    top_spine: bool = True
    right_spine: bool = True
    raster_transparent: bool = False
    vector_transparent: bool = True

    def __post_init__(self) -> None:
        if self.tick_direction not in {"in", "out", "inout"}:
            raise ValueError("tick_direction must be in, out, or inout")
        if (
            self.dpi <= 0
            or min(self.figure_size) <= 0
            or not 0 <= self.component_alpha <= 1
            or not 0 <= self.legend_frame_alpha <= 1
            or not 0 <= self.negligible_component_fraction <= 1
            or self.peak_annotation_collision_fraction < 0
            or self.vertical_headroom < 0
            or self.fitted_region_lower_padding < 0
            or self.fitted_region_upper_padding < 0
        ):
            raise ValueError("theme dimensions, DPI, and alpha must be valid")
        if (
            min(
                self.spine_width,
                self.tick_width,
                self.minor_tick_width,
                self.minor_tick_length,
                self.marker_edge_width,
                self.legend_frame_linewidth,
                self.peak_annotation_size,
                self.peak_annotation_leader_width,
                self.peak_annotation_max_connector_points,
                self.peak_annotation_max_automatic_displacement_points,
                self.peak_annotation_stagger_points,
            )
            <= 0
        ):
            raise ValueError("theme widths and annotation sizes must be positive")

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
            "xtick.minor.width": self.minor_tick_width,
            "ytick.minor.width": self.minor_tick_width,
            "xtick.minor.size": self.minor_tick_length,
            "ytick.minor.size": self.minor_tick_length,
            "axes.grid": False,
            "legend.frameon": self.legend_frame,
            "legend.fontsize": self.legend_font_size,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.dpi": self.dpi,
        }

    def for_multipanel(self) -> PlotTheme:
        """Return the theme's compact typography variant for aligned panels."""
        return replace(
            self,
            axis_label_size=self.multipanel_axis_label_size,
            tick_label_size=self.multipanel_tick_label_size,
            title_size=self.multipanel_title_size,
            core_level_size=self.multipanel_core_level_size,
            legend_font_size=self.multipanel_legend_font_size,
            peak_annotation_size=self.multipanel_peak_annotation_size,
        )


_THEMES = {
    "angze_publication": PlotTheme("angze_publication"),
    "angze_diagnostic": PlotTheme(
        "angze_diagnostic",
        font_size=10,
        axis_label_size=13,
        tick_label_size=10,
        title_size=14,
        core_level_size=12,
        legend_font_size=9,
        figure_size=(5.8, 4.4),
        show_title=True,
        component_alpha=0.18,
    ),
    "monochrome_publication": PlotTheme("monochrome_publication", component_alpha=0.12, raw_edge="#000000"),
    "presentation": PlotTheme(
        "presentation",
        font_size=15,
        axis_label_size=17,
        tick_label_size=13,
        title_size=18,
        tick_length=6,
        marker_size=5,
        fit_line_width=3,
        figure_size=FIGURE_SIZE_PRESETS["presentation"],
        show_title=True,
    ),
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


def load_theme(theme: str | PlotTheme = "angze_publication", **overrides: Any) -> PlotTheme:
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


def style_axes(
    axis: Axes,
    theme: PlotTheme,
    *,
    top: bool | None = None,
    right: bool | None = None,
    show_top_ticks: bool | None = None,
    show_y_ticks: bool = True,
) -> None:
    """Apply the theme to every visible spine and tick without changing global state."""
    top_visible = theme.top_spine if top is None else top
    right_visible = theme.right_spine if right is None else right
    axis.spines["top"].set_visible(top_visible)
    axis.spines["right"].set_visible(right_visible)
    for spine in axis.spines.values():
        spine.set_linewidth(theme.spine_width)
    top_ticks = top_visible if show_top_ticks is None else show_top_ticks
    axis.tick_params(
        axis="x",
        which="major",
        direction=theme.tick_direction,
        length=theme.tick_length,
        width=theme.tick_width,
        bottom=True,
        top=top_ticks,
        labelbottom=True,
        labeltop=False,
    )
    axis.tick_params(
        axis="x",
        which="minor",
        direction=theme.tick_direction,
        length=theme.minor_tick_length,
        width=theme.minor_tick_width,
        bottom=True,
        top=top_ticks,
        labelbottom=False,
        labeltop=False,
    )
    axis.tick_params(
        axis="y",
        which="both",
        direction=theme.tick_direction,
        length=theme.tick_length,
        width=theme.tick_width,
        left=show_y_ticks,
        right=right_visible and show_y_ticks,
        labelleft=show_y_ticks,
        labelright=False,
    )
    for tick in (*axis.xaxis.get_major_ticks(), *axis.yaxis.get_major_ticks()):
        tick.label1.set_fontweight(theme.tick_label_weight)
        tick.label2.set_fontweight(theme.tick_label_weight)
    axis.grid(False)


def style_legend(legend: Legend, theme: PlotTheme) -> Legend:
    """Apply the compact, deterministic publication legend hierarchy."""
    frame = legend.get_frame()
    frame.set_facecolor(theme.legend_face_colour)
    frame.set_edgecolor(theme.legend_edge_colour)
    frame.set_alpha(theme.legend_frame_alpha)
    frame.set_linewidth(theme.legend_frame_linewidth)
    for text in legend.get_texts():
        text.set_fontweight(theme.legend_font_weight)
        text.set_fontsize(theme.legend_font_size)
    return legend


def apply_vertical_headroom(
    axis: Axes,
    theme: PlotTheme,
    *,
    minimum: float,
    maximum: float,
    bottom: float | None = None,
) -> None:
    """Set a stable y range with theme-controlled space above displayed curves."""
    lower = minimum if bottom is None else bottom
    span = max(maximum - lower, abs(maximum), 1.0)
    axis.set_ylim(bottom=lower, top=maximum + theme.vertical_headroom * span)


def fitted_region_y_limits(
    raw_intensity: np.ndarray,
    background: np.ndarray,
    total_fit: np.ndarray,
    theme: PlotTheme,
) -> tuple[float, float]:
    """Return baseline-relative limits from the displayed fitted envelope."""
    curves = tuple(np.asarray(curve, dtype=float) for curve in (raw_intensity, background, total_fit))
    finite = tuple(curve[np.isfinite(curve)] for curve in curves)
    if any(curve.size == 0 for curve in finite):
        raise ValueError("fitted-region y limits require finite displayed curves")
    display_minimum = min(float(np.min(curve)) for curve in finite)
    display_maximum = max(float(np.max(curve)) for curve in finite)
    signal_span = display_maximum - display_minimum
    if signal_span <= 0:
        signal_span = max(abs(display_maximum), 1.0)
    return (
        display_minimum - theme.fitted_region_lower_padding * signal_span,
        display_maximum + theme.fitted_region_upper_padding * signal_span,
    )


@contextmanager
def theme_context(theme: str | PlotTheme = "angze_publication", **overrides: Any) -> Iterator[PlotTheme]:
    selected = load_theme(theme, **overrides)
    with mpl.rc_context(selected.rc_params()):
        yield selected
