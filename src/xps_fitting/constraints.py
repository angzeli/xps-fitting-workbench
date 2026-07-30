"""Helpers for common chemistry/physics parameter relationships."""

from __future__ import annotations

from .configuration import PeakConfig


def cl2p_doublet(
    label: str,
    centre_32: float,
    area_32: float,
    *,
    separation: float = 1.6,
    fwhm: float = 1.2,
    fraction: float = 0.5,
) -> list[PeakConfig]:
    """Create a 2p3/2:2p1/2 doublet with shared shape/width and a 2:1 area ratio."""
    group = f"{label}_doublet"
    main = PeakConfig(
        f"{label}_2p3/2",
        centre_32,
        (centre_32 - 0.5, centre_32 + 0.5),
        area_32,
        fwhm=fwhm,
        width_group=group,
        fraction=fraction,
        fraction_group=group,
    )
    partner = PeakConfig(
        f"{label}_2p1/2",
        centre_32 + separation,
        (centre_32 + separation - 0.5, centre_32 + separation + 0.5),
        area_32 / 2,
        fwhm=fwhm,
        width_group=group,
        fraction=fraction,
        fraction_group=group,
        centre_offset_from=(main.label, separation),
        area_ratio_to=(main.label, 0.5),
    )
    return [main, partner]


def validate_links(peaks: list[PeakConfig]) -> None:
    """Require unique peak labels and references to peaks in the same model."""
    labels = {peak.label for peak in peaks}
    if len(labels) != len(peaks):
        raise ValueError("peak labels must be unique")
    for peak in peaks:
        for link in (peak.centre_offset_from, peak.area_ratio_to):
            if link and link[0] not in labels:
                raise ValueError(f"{peak.label} references unknown peak {link[0]}")
