"""Validated fitting configuration dataclasses."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PeakConfig:
    label: str
    centre: float
    centre_bounds: tuple[float, float]
    area: float
    area_bounds: tuple[float, float] = (0.0, float("inf"))
    fwhm: float = 1.4
    fwhm_bounds: tuple[float, float] = (0.2, 3.0)
    line_shape: str = "pseudo_voigt"
    fraction: float = 0.5
    fraction_bounds: tuple[float, float] = (0.0, 1.0)
    fixed: tuple[str, ...] = ()
    width_group: str | None = None
    fraction_group: str | None = None
    centre_offset_from: tuple[str, float] | None = None
    area_ratio_to: tuple[str, float] | None = None

    def __post_init__(self) -> None:
        for name, value, bounds in (
            ("centre", self.centre, self.centre_bounds),
            ("area", self.area, self.area_bounds),
            ("fwhm", self.fwhm, self.fwhm_bounds),
            ("fraction", self.fraction, self.fraction_bounds),
        ):
            if len(bounds) != 2 or bounds[0] > bounds[1]:
                raise ValueError(f"{self.label} {name} bounds are invalid")
            if not math.isfinite(value):
                raise ValueError(f"{self.label} {name} must be finite")
            if bounds[0] > value or value > bounds[1]:
                raise ValueError(f"{self.label} {name} is outside its bounds")
        if self.area < 0 or self.fwhm <= 0:
            raise ValueError("area must be non-negative and FWHM positive")
        if self.area_bounds[0] < 0 or self.fwhm_bounds[0] <= 0:
            raise ValueError("area bounds must be non-negative and FWHM bounds positive")
        if self.fraction_bounds[0] < 0 or self.fraction_bounds[1] > 1:
            raise ValueError("fraction bounds must lie within [0, 1]")
        if self.line_shape not in {"gaussian", "lorentzian", "pseudo_voigt"}:
            raise ValueError(f"unsupported fitting line shape: {self.line_shape}")


@dataclass
class FitConfig:
    name: str
    region: str
    peaks: list[PeakConfig]
    background: str = "linear"
    robust_loss: str = "linear"
    multistart: int = 1
    random_seed: int = 0
    release_fraction: bool = False
    max_background_iterations: int = 3
    width_penalty: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.region.strip() or not self.peaks:
            raise ValueError("fit name, region, and at least one peak are required")
        if self.background not in {"linear", "shirley"}:
            raise ValueError("background must be 'linear' or 'shirley'")
        if self.robust_loss not in {"linear", "soft_l1", "huber", "cauchy", "arctan"}:
            raise ValueError("unsupported least-squares robust loss")
        if isinstance(self.multistart, bool) or not isinstance(self.multistart, int) or self.multistart < 1:
            raise ValueError("multistart must be a positive integer")
        if (
            isinstance(self.max_background_iterations, bool)
            or not isinstance(self.max_background_iterations, int)
            or self.max_background_iterations < 1
        ):
            raise ValueError("max_background_iterations must be a positive integer")
        if not math.isfinite(self.width_penalty) or self.width_penalty < 0:
            raise ValueError("width_penalty must be finite and non-negative")
        labels = [peak.label for peak in self.peaks]
        if len(labels) != len(set(labels)):
            raise ValueError("peak labels must be unique")
        for attribute in ("width_group", "fraction_group"):
            groups: dict[str, list[PeakConfig]] = {}
            for peak in self.peaks:
                group = getattr(peak, attribute)
                if group:
                    groups.setdefault(group, []).append(peak)
            parameter = "fwhm" if attribute == "width_group" else "fraction"
            for group, peaks in groups.items():
                values = {getattr(peak, parameter) for peak in peaks}
                bounds = {tuple(getattr(peak, f"{parameter}_bounds")) for peak in peaks}
                if len(values) != 1 or len(bounds) != 1:
                    raise ValueError(f"shared {parameter} group {group!r} requires identical initials and bounds")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_config(path: str | Path) -> FitConfig:
    """Load a JSON candidate-model configuration."""
    with Path(path).open(encoding="utf-8") as stream:
        data = json.load(stream)
    data["peaks"] = [PeakConfig(**peak) for peak in data["peaks"]]
    config = FitConfig(**data)
    from .constraints import validate_links

    validate_links(config.peaks)
    return config
