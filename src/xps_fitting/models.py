"""Numerical evaluation of configured component models."""

from __future__ import annotations

import numpy as np

from .configuration import PeakConfig
from .lineshapes import gaussian, lorentzian, pseudo_voigt


def evaluate_peak(x: np.ndarray, peak: PeakConfig, values: dict[str, float]) -> np.ndarray:
    prefix = peak.label
    area, centre = values[f"{prefix}.area"], values[f"{prefix}.centre"]
    fwhm, fraction = values[f"{prefix}.fwhm"], values[f"{prefix}.fraction"]
    if peak.line_shape == "gaussian":
        return gaussian(x, area, centre, fwhm)
    if peak.line_shape == "lorentzian":
        return lorentzian(x, area, centre, fwhm)
    if peak.line_shape == "pseudo_voigt":
        return pseudo_voigt(x, area, centre, fwhm, fraction)
    raise ValueError(f"unsupported fitting line shape: {peak.line_shape}")


def resolve_links(peaks: list[PeakConfig], values: dict[str, float]) -> dict[str, float]:
    resolved = dict(values)
    width_groups: dict[str, float] = {}
    fraction_groups: dict[str, float] = {}
    for peak in peaks:
        if peak.width_group:
            key = f"{peak.label}.fwhm"
            resolved[key] = width_groups.setdefault(peak.width_group, resolved[key])
        if peak.fraction_group:
            key = f"{peak.label}.fraction"
            resolved[key] = fraction_groups.setdefault(peak.fraction_group, resolved[key])
        if peak.centre_offset_from:
            reference, offset = peak.centre_offset_from
            resolved[f"{peak.label}.centre"] = resolved[f"{reference}.centre"] + offset
        if peak.area_ratio_to:
            reference, ratio = peak.area_ratio_to
            resolved[f"{peak.label}.area"] = resolved[f"{reference}.area"] * ratio
    return resolved
