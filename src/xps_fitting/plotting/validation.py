"""Plot-input and colour-accessibility validation."""

from __future__ import annotations

from matplotlib.colors import to_rgb

from ..integrity import validate_result_integrity
from ..result import FitResult


def validate_result_curves(result: FitResult, *, rtol: float = 1e-9, atol: float = 1e-12) -> None:
    """Validate curve alignment and reconstruction invariants before plotting."""
    validate_result_integrity(result, rtol=rtol, atol=atol)


def contrast_ratio(foreground: str, background: str = "#FFFFFF") -> float:
    """Return the relative-luminance contrast ratio between two Matplotlib colours."""

    def luminance(colour: str) -> float:
        channels = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in to_rgb(colour)]
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    first, second = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (first + 0.05) / (second + 0.05)
