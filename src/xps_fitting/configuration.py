"""Validated fitting configuration dataclasses."""

from __future__ import annotations

import json
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
            if bounds[0] > value or value > bounds[1]:
                raise ValueError(f"{self.label} {name} is outside its bounds")
        if self.area < 0 or self.fwhm <= 0:
            raise ValueError("area must be non-negative and FWHM positive")


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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_config(path: str | Path) -> FitConfig:
    """Load a JSON candidate-model configuration."""
    with Path(path).open(encoding="utf-8") as stream:
        data = json.load(stream)
    data["peaks"] = [PeakConfig(**peak) for peak in data["peaks"]]
    return FitConfig(**data)
