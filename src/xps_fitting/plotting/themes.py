"""Validated, local-only plotting themes."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Iterator

import matplotlib as mpl


@dataclass(frozen=True)
class PlotTheme:
    name: str
    font_family: str = "DejaVu Sans"
    font_size: float = 9
    axis_label_size: float = 10
    tick_label_size: float = 8
    title_size: float = 11
    spine_width: float = 1.2
    tick_width: float = 1.0
    tick_length: float = 4.0
    tick_direction: str = "in"
    marker: str = "o"
    marker_size: float = 3.0
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
    figure_size: tuple[float, float] = (3.45, 2.8)
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

    def rc_params(self) -> dict[str, object]:
        return {
            "font.family": self.font_family,
            "font.size": self.font_size,
            "axes.labelsize": self.axis_label_size,
            "axes.titlesize": self.title_size,
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
            "savefig.dpi": self.dpi,
        }


_THEMES = {
    "angze_publication": PlotTheme("angze_publication"),
    "angze_diagnostic": PlotTheme("angze_diagnostic", figure_size=(5.8, 4.4), show_title=True, top_spine=True, right_spine=True, component_alpha=0.18),
    "monochrome_publication": PlotTheme("monochrome_publication", component_alpha=0.12, raw_edge="#000000"),
    "presentation": PlotTheme("presentation", font_size=15, axis_label_size=17, tick_label_size=13, title_size=18, spine_width=1.8, tick_width=1.5, tick_length=6, marker_size=5, fit_line_width=3, figure_size=(8, 5), show_title=True),
}


def load_theme(theme: str | PlotTheme = "angze_publication", **overrides) -> PlotTheme:
    selected = theme if isinstance(theme, PlotTheme) else _THEMES.get(theme)
    if selected is None:
        raise ValueError(f"unknown theme {theme!r}; choose from {sorted(_THEMES)}")
    return replace(selected, **overrides) if overrides else selected


@contextmanager
def theme_context(theme: str | PlotTheme = "angze_publication", **overrides) -> Iterator[PlotTheme]:
    selected = load_theme(theme, **overrides)
    with mpl.rc_context(selected.rc_params()):
        yield selected
