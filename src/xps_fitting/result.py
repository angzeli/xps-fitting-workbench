"""Stable numerical result contract for fitting and Phase 2 plotting."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


@dataclass
class FitResult:
    energy: np.ndarray
    raw_intensity: np.ndarray
    background: np.ndarray
    components: dict[str, np.ndarray]
    total_fit: np.ndarray
    residual: np.ndarray
    fitted_parameters: dict[str, float]
    parameter_uncertainties: dict[str, float | None] = field(default_factory=dict)
    correlation_matrix: dict[str, dict[str, float]] = field(default_factory=dict)
    fit_statistics: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    configuration: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    convergence: dict[str, Any] = field(default_factory=dict)
    software_versions: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))
