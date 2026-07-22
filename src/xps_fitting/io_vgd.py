"""Adapter for the repository's VGD reader workflow."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .io import spectrum_from_dataframe
from .spectrum import Spectrum


def read_vgd(path: str | Path, *, spectrum_index: int = 0, intensity_column: str = "corrected_intensity") -> Spectrum:
    try:
        from vgd_reader import read_vgd as parse_vgd
    except ImportError as exc:
        raise ImportError("VGD input requires the declared vgd-reader dependency; run 'uv sync'") from exc

    parsed = parse_vgd(Path(path))
    selected = next((item for item in parsed.spectra if item.spectrum_index == spectrum_index), None)
    if selected is None:
        raise IndexError(f"spectrum_index {spectrum_index} is unavailable")
    if not hasattr(selected, intensity_column):
        raise ValueError(f"VGD spectrum has no intensity column {intensity_column!r}")

    frame = pd.DataFrame(
        {
            "binding_energy_eV": selected.binding_energy,
            "intensity": getattr(selected, intensity_column),
        }
    )
    return spectrum_from_dataframe(
        frame,
        "binding_energy_eV",
        "intensity",
        region=str(selected.core_level),
        sample_name=str(selected.sample_id),
        source_file=str(path),
        metadata={
            "data_origin": "experimental",
            "vgd_spectrum_index": spectrum_index,
            "title": selected.title,
            "technique": selected.technique,
            "source_energy_eV": selected.source_energy,
            "pass_energy_eV": selected.pass_energy,
            "dwell_time_s": selected.dwell_time,
            "periods": selected.periods,
            "txf_applied": selected.txf_applied,
        },
    )
