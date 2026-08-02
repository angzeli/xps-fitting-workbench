"""Validated representation of aligned XPS binding-energy and intensity arrays."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Spectrum:
    """Hold aligned one-dimensional XPS energy and intensity arrays.

    Binding energy is stored in eV and must be finite and strictly ascending for
    fitting. Optional normalised intensity must have the same shape; its scale and
    the raw intensity units remain those supplied by the data source.
    """

    binding_energy: np.ndarray
    intensity: np.ndarray
    region: str = ""
    sample_name: str = ""
    source_file: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    normalised_intensity: np.ndarray | None = None
    acquisition_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Coerce inputs to finite one-dimensional arrays in ascending energy order."""
        energy = np.asarray(self.binding_energy, dtype=float)
        intensity = np.asarray(self.intensity, dtype=float)
        if energy.ndim != 1 or intensity.ndim != 1 or energy.size != intensity.size:
            raise ValueError("binding_energy and intensity must be equal-length 1D arrays")
        if energy.size < 2 or not np.all(np.isfinite(energy)) or not np.all(np.isfinite(intensity)):
            raise ValueError("a spectrum needs at least two finite points")
        if np.any(np.diff(energy) <= 0):
            raise ValueError("binding_energy must be strictly ascending for fitting")
        object.__setattr__(self, "binding_energy", energy)
        object.__setattr__(self, "intensity", intensity)
        if self.normalised_intensity is not None:
            norm = np.asarray(self.normalised_intensity, dtype=float)
            if norm.shape != energy.shape:
                raise ValueError("normalised_intensity must match binding_energy")
            object.__setattr__(self, "normalised_intensity", norm)

    def crop(self, minimum: float, maximum: float) -> "Spectrum":
        """Return an inclusive binding-energy interval in eV, preserving array alignment."""
        lo, hi = sorted((minimum, maximum))
        mask = (self.binding_energy >= lo) & (self.binding_energy <= hi)
        if mask.sum() < 2:
            raise ValueError("crop interval contains fewer than two points")
        normalised = None if self.normalised_intensity is None else self.normalised_intensity[mask]
        return replace(
            self,
            binding_energy=self.binding_energy[mask],
            intensity=self.intensity[mask],
            normalised_intensity=normalised,
        )

    @property
    def source_path(self) -> Path | None:
        """Return the recorded source as a path, or ``None`` when it is absent."""
        return None if self.source_file is None else Path(self.source_file)
