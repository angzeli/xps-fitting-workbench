"""Stable semantic colours and monochrome fallbacks."""

from __future__ import annotations

import warnings
from hashlib import sha256

from .aliases import canonical_core_level

CORE_LEVEL_COLOURS = {
    "Survey": "#111810",
    "C 1s": "#8C8C8C",
    "N 1s": "#2F80ED",
    "O 1s": "#EB5757",
    "S 2p": "#F2C94C",
    "Cl 2p": "#27AE60",
}
COMPONENT_COLOURS = {
    "aromatic_C-C_C=C": "#5B6F8A",
    "C-N_C-Cl": "#2563EB",
    "imide_N-C=O": "#7C3AED",
    "acid_O-C=O": "#EA580C",
    "pi-pi_star": "#0F766E",
    "Cl_2p3/2": "#166534",
    "Cl_2p1/2": "#4C956C",
    "O_1s_carbonyl": "#D62728",
    "O_1s_carboxyl": "#E66101",
    "O_1s_hydroxyl": "#C2185B",
    "N_1s_imide": "#7C3AED",
    "N_1s_amine": "#6D28D9",
    "carbonyl_O": "#D62728",
    "imide_carbonyl_O": "#D62728",
    "acid_carbonyl_O": "#E66101",
    "acid_hydroxyl_OH": "#C2185B",
    "methyl_C": "#A16207",
    "methoxy_C": "#0891B2",
}
UNKNOWN_COMPONENT_COLOUR = "#6B7280"
MONOCHROME_STYLES = ("-", "--", "-.", ":")


def core_level_colour(core_level: str) -> str:
    return CORE_LEVEL_COLOURS.get(canonical_core_level(core_level), "#4B5563")


def component_colour(label: str, overrides: dict[str, str] | None = None) -> str:
    if overrides and label in overrides:
        return overrides[label]
    if label in COMPONENT_COLOURS:
        return COMPONENT_COLOURS[label]
    warnings.warn(
        f"component {label!r} has no semantic colour; using neutral {UNKNOWN_COMPONENT_COLOUR}",
        UserWarning,
        stacklevel=2,
    )
    return UNKNOWN_COMPONENT_COLOUR


def component_style(label: str) -> str:
    index = int.from_bytes(sha256(label.encode("utf-8")).digest()[4:8], "big") % len(MONOCHROME_STYLES)
    return MONOCHROME_STYLES[index]
