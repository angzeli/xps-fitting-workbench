"""Serializable plotting recipes."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .annotations import validate_peak_annotation_options
from .single import DISPLAY_MODES
from .themes import figure_size_preset as resolve_figure_size_preset
from .themes import load_theme, validate_theme


@dataclass(frozen=True)
class PlotConfig:
    theme: str = "angze_publication"
    figure_size: tuple[float, float] | None = None
    figure_size_preset: str | None = None
    output_formats: tuple[str, ...] = ("png", "pdf")
    output_filename: str = "xps_fit"
    core_level: str | None = None
    core_level_colour: str | None = None
    component_colour_overrides: dict[str, str] = field(default_factory=dict)
    component_display_mode: str = "filled_to_background"
    fit_line_width: float | None = None
    component_line_width: float | None = None
    marker_size: float | None = None
    dpi: int | None = None
    show_peak_positions: bool = False
    peak_position_precision: int = 1
    peak_position_unit: bool = True
    peak_annotation_leaders: bool = True
    peak_label_fontsize: float | None = None
    peak_annotation_leader_width: float | None = None
    peak_annotation_offsets: dict[str, tuple[float, float]] = field(default_factory=dict)
    peak_annotations: dict[str, dict[str, Any]] = field(default_factory=dict)
    annotate_negligible_components: bool = False
    annotate_hidden_components: bool = False
    labels: dict[str, str] = field(default_factory=dict)
    legend_order: tuple[str, ...] = ()
    x_limits: tuple[float, float] | None = None
    tick_spacing: float | None = None
    x_minor_interval: float | None = None
    show_y_ticks: bool = True
    show_top_ticks: bool | None = None
    show_sample_title: bool = True
    core_level_label_position: tuple[float, float] | None = None
    residual_panel: bool = False
    normalisation_disclosure: str | None = None
    intensity_offset_disclosure: str | None = None
    panel_layout: str = "single"
    panel_labels: tuple[str, ...] = ()
    transparent: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        theme = load_theme(self.theme)
        if self.figure_size is not None and self.figure_size_preset is not None:
            raise ValueError("set either figure_size or figure_size_preset, not both")
        if self.figure_size_preset is not None:
            resolve_figure_size_preset(self.figure_size_preset)
        if self.component_display_mode not in DISPLAY_MODES:
            raise ValueError(f"invalid component_display_mode {self.component_display_mode!r}")
        if not self.output_formats:
            raise ValueError("output_formats must contain PNG and/or PDF")
        validate_theme(theme, output_formats=self.output_formats)
        if self.dpi is not None and (isinstance(self.dpi, bool) or not isinstance(self.dpi, int) or self.dpi <= 0):
            raise ValueError("dpi must be a positive integer")
        for value in (
            self.fit_line_width,
            self.component_line_width,
            self.marker_size,
            self.tick_spacing,
            self.x_minor_interval,
            self.peak_label_fontsize,
            self.peak_annotation_leader_width,
        ):
            if value is not None and value <= 0:
                raise ValueError("line widths, marker size, and tick spacing must be positive")
        if (
            isinstance(self.peak_position_precision, bool)
            or not isinstance(self.peak_position_precision, int)
            or self.peak_position_precision < 0
        ):
            raise ValueError("peak_position_precision must be a non-negative integer")
        for label, offset in self.peak_annotation_offsets.items():
            try:
                offset_x, offset_y = offset
            except (TypeError, ValueError) as exc:
                raise ValueError(f"peak annotation offset for {label!r} must contain two finite values") from exc
            if not all(math.isfinite(value) for value in (offset_x, offset_y)):
                raise ValueError(f"peak annotation offset for {label!r} must contain two finite values")
        validate_peak_annotation_options(
            self.peak_annotations,
            default_connector=self.peak_annotation_leaders,
            max_connector_points=theme.peak_annotation_max_connector_points,
        )
        if self.core_level_label_position is not None and (
            len(self.core_level_label_position) != 2
            or not all(math.isfinite(value) and 0 <= value <= 1 for value in self.core_level_label_position)
        ):
            raise ValueError("core_level_label_position must contain two axes-relative values between 0 and 1")
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
    for key in (
        "figure_size",
        "output_formats",
        "legend_order",
        "x_limits",
        "panel_labels",
        "core_level_label_position",
    ):
        if key in data and data[key] is not None:
            data[key] = tuple(data[key])
    if "peak_annotation_offsets" in data:
        data["peak_annotation_offsets"] = {
            label: tuple(offset) for label, offset in data["peak_annotation_offsets"].items()
        }
    if "peak_annotations" in data:
        for options in data["peak_annotations"].values():
            if "offset_points" in options:
                options["offset_points"] = tuple(options["offset_points"])
    return PlotConfig(**data)
