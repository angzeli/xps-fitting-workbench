"""Plot-input and colour-accessibility validation."""

from __future__ import annotations

from matplotlib.colors import to_rgb
import numpy as np

from ..result import FitResult


def validate_result_curves(result: FitResult, *, rtol: float = 1e-9, atol: float = 1e-12) -> None:
    arrays = [result.raw_intensity, result.background, result.total_fit, result.residual, *result.components.values()]
    if any(np.asarray(array).shape != result.energy.shape for array in arrays):
        raise ValueError("all FitResult curves must share the energy shape")
    reconstructed = result.background + sum((np.asarray(curve) for curve in result.components.values()), start=np.zeros_like(result.energy))
    if not np.allclose(reconstructed, result.total_fit, rtol=rtol, atol=atol):
        raise ValueError("components plus background do not match total_fit")
    if not np.allclose(result.raw_intensity - result.total_fit, result.residual, rtol=rtol, atol=atol):
        raise ValueError("raw_intensity minus total_fit does not match residual")


def contrast_ratio(foreground: str, background: str = "#FFFFFF") -> float:
    def luminance(colour: str) -> float:
        channels = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in to_rgb(colour)]
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
    first, second = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (first + 0.05) / (second + 0.05)
