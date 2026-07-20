"""Optional adapter for the repository's existing VGD reader workflow."""

from __future__ import annotations

from pathlib import Path

from .io import spectrum_from_dataframe
from .spectrum import Spectrum


def read_vgd(path: str | Path, *, spectrum_index: int = 0, intensity_column: str = "corrected_intensity") -> Spectrum:
    try:
        from xps_vgd_utils import read_vgd_to_dataframe
    except ImportError as exc:
        raise ImportError("VGD input requires the optional vgd-reader package and xps_vgd_utils.py") from exc
    frame = read_vgd_to_dataframe(path)
    selected = frame[frame["spectrum_index"] == spectrum_index]
    if selected.empty:
        raise IndexError(f"spectrum_index {spectrum_index} is unavailable")
    row = selected.iloc[0]
    return spectrum_from_dataframe(
        selected, "binding_energy_eV", intensity_column,
        region=str(row.get("core_level", "")), sample_name=str(row.get("sample_id", "")), source_file=str(path),
        metadata={"vgd_spectrum_index": spectrum_index},
    )
