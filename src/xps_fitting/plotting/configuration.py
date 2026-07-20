"""Serializable plotting recipes."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .single import DISPLAY_MODES
from .themes import load_theme, validate_theme


@dataclass(frozen=True)
class PlotConfig:
    theme: str = "angze_publication"
    figure_size: tuple[float, float] | None = None
    output_formats: tuple[str, ...] = ("png", "pdf")
    output_filename: str = "xps_fit"
    core_level: str | None = None
    core_level_colour: str | None = None
    component_colour_overrides: dict[str, str] = field(default_factory=dict)
    component_display_mode: str = "filled_to_background"
    fit_line_width: float | None = None
    component_line_width: float | None = None
    marker_size: float | None = None
    labels: dict[str, str] = field(default_factory=dict)
    legend_order: tuple[str, ...] = ()
    x_limits: tuple[float, float] | None = None
    tick_spacing: float | None = None
    residual_panel: bool = False
    normalisation_disclosure: str | None = None
    intensity_offset_disclosure: str | None = None
    panel_layout: str = "single"
    panel_labels: tuple[str, ...] = ()
    transparent: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        theme = load_theme(self.theme)
        if self.component_display_mode not in DISPLAY_MODES:
            raise ValueError(f"invalid component_display_mode {self.component_display_mode!r}")
        if not self.output_formats:
            raise ValueError("output_formats must contain PNG and/or PDF")
        validate_theme(theme, output_formats=self.output_formats)
        for value in (self.fit_line_width, self.component_line_width, self.marker_size, self.tick_spacing):
            if value is not None and value <= 0:
                raise ValueError("line widths, marker size, and tick spacing must be positive")
        if self.panel_layout not in {"single", "horizontal", "vertical", "grid"}:
            raise ValueError("invalid panel_layout")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
        return path


def load_plot_config(path: str | Path) -> PlotConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("figure_size", "output_formats", "legend_order", "x_limits", "panel_labels"):
        if key in data and data[key] is not None:
            data[key] = tuple(data[key])
    return PlotConfig(**data)
