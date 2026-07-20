"""Stable semantic colours and monochrome fallbacks."""

from __future__ import annotations

from hashlib import sha256

from .aliases import canonical_core_level

CORE_LEVEL_COLOURS = {"Survey": "#111810", "C 1s": "#8C8C8C", "N 1s": "#2F80ED", "O 1s": "#EB5757", "S 2p": "#F2C94C", "Cl 2p": "#27AE60"}
COMPONENT_COLOURS = {
    "aromatic_C-C_C=C": "#64748B",
    "C-N_C-Cl": "#2563EB",
    "imide_N-C=O": "#7C3AED",
    "acid_O-C=O": "#EA580C",
    "pi-pi_star": "#0F766E",
}
FALLBACK_COMPONENT_COLOURS = ("#0F766E", "#B45309", "#4338CA", "#BE123C", "#4D7C0F", "#A21CAF", "#0369A1")
MONOCHROME_STYLES = ("-", "--", "-.", ":")


def core_level_colour(core_level: str) -> str:
    return CORE_LEVEL_COLOURS.get(canonical_core_level(core_level), "#4B5563")


def component_colour(label: str, overrides: dict[str, str] | None = None) -> str:
    if overrides and label in overrides:
        return overrides[label]
    if label in COMPONENT_COLOURS:
        return COMPONENT_COLOURS[label]
    index = int.from_bytes(sha256(label.encode("utf-8")).digest()[:4], "big") % len(FALLBACK_COMPONENT_COLOURS)
    return FALLBACK_COMPONENT_COLOURS[index]


def component_style(label: str) -> str:
    index = int.from_bytes(sha256(label.encode("utf-8")).digest()[4:8], "big") % len(MONOCHROME_STYLES)
    return MONOCHROME_STYLES[index]
