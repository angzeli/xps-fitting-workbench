"""Validate stored plot inputs and colour accessibility."""

from __future__ import annotations

from matplotlib.colors import to_rgb

from ..integrity import validate_result_integrity
from ..result import FitResult


def validate_result_curves(result: FitResult, *, rtol: float = 1e-9, atol: float = 1e-12) -> None:
    """Validate aligned stored curves and their reconstruction identities."""
    validate_result_integrity(result, rtol=rtol, atol=atol)


def _relative_luminance(colour: str) -> float:
    """Return WCAG-style relative luminance for a Matplotlib colour."""
    channels = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in to_rgb(colour)]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(foreground: str, background: str = "#FFFFFF") -> float:
    """Return ``(lighter + 0.05) / (darker + 0.05)`` for two colours."""
    first, second = sorted((_relative_luminance(foreground), _relative_luminance(background)), reverse=True)
    return (first + 0.05) / (second + 0.05)
