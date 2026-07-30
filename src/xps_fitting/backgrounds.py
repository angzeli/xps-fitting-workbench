"""XPS background estimators."""

from __future__ import annotations

import numpy as np


def linear(x: np.ndarray, y_start: float, y_end: float) -> np.ndarray:
    """Interpolate a straight background between the supplied endpoint levels."""
    x = np.asarray(x, dtype=float)
    if x[-1] == x[0]:
        raise ValueError("energy range must be nonzero")
    return y_start + (y_end - y_start) * (x - x[0]) / (x[-1] - x[0])


def shirley(intensity: np.ndarray, *, max_iter: int = 200, tolerance: float = 1e-7) -> np.ndarray:
    """Iterative discrete Shirley background for data in either acquisition order."""
    y = np.asarray(intensity, dtype=float)
    if y.ndim != 1 or y.size < 2 or not np.all(np.isfinite(y)):
        raise ValueError("intensity must be a finite 1D array")
    background = np.linspace(y[0], y[-1], y.size)
    for _ in range(max_iter):
        positive = np.maximum(y - background, 0)
        cumulative = np.cumsum(positive[::-1])[::-1]
        if cumulative[0] <= np.finfo(float).eps:
            return np.linspace(y[0], y[-1], y.size)
        updated = y[-1] + (y[0] - y[-1]) * cumulative / cumulative[0]
        if np.max(np.abs(updated - background)) <= tolerance * max(1.0, np.ptp(y)):
            return updated
        background = updated
    return background
