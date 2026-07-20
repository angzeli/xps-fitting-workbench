"""Tabular spectrum input."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .spectrum import Spectrum


def spectrum_from_dataframe(
    frame: pd.DataFrame,
    energy_column: str = "binding_energy_eV",
    intensity_column: str = "intensity",
    *, region: str = "", sample_name: str = "", source_file: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Spectrum:
    """Clean a table, average duplicate energies, and return ascending arrays."""
    if energy_column not in frame or intensity_column not in frame:
        raise ValueError(f"required columns: {energy_column!r}, {intensity_column!r}")
    original_order = "ascending" if frame[energy_column].is_monotonic_increasing else (
        "descending" if frame[energy_column].is_monotonic_decreasing else "unordered"
    )
    table = pd.DataFrame({
        "energy": pd.to_numeric(frame[energy_column], errors="coerce"),
        "intensity": pd.to_numeric(frame[intensity_column], errors="coerce"),
    }).dropna()
    table = table[np.isfinite(table["energy"]) & np.isfinite(table["intensity"])]
    table = table.groupby("energy", as_index=False, sort=True)["intensity"].mean()
    info = dict(metadata or {})
    info.update({"original_order": original_order, "input_rows": len(frame), "clean_rows": len(table)})
    return Spectrum(table.energy.to_numpy(), table.intensity.to_numpy(), region, sample_name, source_file, info)


def read_csv(path: str | Path, **kwargs: Any) -> Spectrum:
    path = Path(path)
    return spectrum_from_dataframe(pd.read_csv(path), source_file=str(path), **kwargs)


def read_xlsx(path: str | Path, *, sheet_name: str | int = 0, **kwargs: Any) -> Spectrum:
    path = Path(path)
    return spectrum_from_dataframe(pd.read_excel(path, sheet_name=sheet_name), source_file=str(path), **kwargs)
