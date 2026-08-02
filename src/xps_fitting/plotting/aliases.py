"""Canonical display naming for supported XPS core levels."""

from __future__ import annotations

_CANONICAL = {
    "survey": "Survey",
    "xpssurvey": "Survey",
    "c1s": "C 1s",
    "n1s": "N 1s",
    "o1s": "O 1s",
    "s2p": "S 2p",
    "cl2p": "Cl 2p",
}


def canonical_core_level(value: str) -> str:
    """Return the spaced display spelling for a recognised core-level alias.

    Unknown labels are stripped but otherwise retained, avoiding unsupported
    scientific interpretation.
    """
    key = value.lower().replace(" ", "").replace("_", "").removesuffix("scan")
    return _CANONICAL.get(key, value.strip())
