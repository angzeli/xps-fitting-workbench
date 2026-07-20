"""Reconstruct plotting-only results from Phase 1 exports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..result import FitResult


def fit_result_from_dict(data: dict[str, Any]) -> FitResult:
    array_keys = ("energy", "raw_intensity", "background", "total_fit", "residual")
    arrays = {key: np.asarray(data[key], dtype=float) for key in array_keys}
    components = {label: np.asarray(curve, dtype=float) for label, curve in data.get("components", {}).items()}
    return FitResult(**arrays, components=components, fitted_parameters=data.get("fitted_parameters", {}), parameter_uncertainties=data.get("parameter_uncertainties", {}), correlation_matrix=data.get("correlation_matrix", {}), fit_statistics=data.get("fit_statistics", {}), warnings=data.get("warnings", []), configuration=data.get("configuration", {}), metadata=data.get("metadata", {}), convergence=data.get("convergence", {}), software_versions=data.get("software_versions", {}))


def load_curve_result(path: str | Path, metadata: str | Path | dict[str, Any] | None = None) -> FitResult:
    """Load a full-result JSON or CSV/XLSX curves plus Phase 1 JSON metadata."""
    path = Path(path)
    if path.suffix.lower() == ".json":
        return fit_result_from_dict(json.loads(path.read_text(encoding="utf-8")))
    if path.suffix.lower() == ".csv":
        table = pd.read_csv(path)
    elif path.suffix.lower() in {".xlsx", ".xls"}:
        table = pd.read_excel(path, sheet_name="curves")
    else:
        raise ValueError("plot source must be a full JSON result or CSV/XLSX curve table")
    details = json.loads(Path(metadata).read_text(encoding="utf-8")) if isinstance(metadata, (str, Path)) else dict(metadata or {})
    components = {column.removeprefix("component:"): table[column].to_numpy(float) for column in table if column.startswith("component:")}
    return FitResult(
        table["binding_energy_eV"].to_numpy(float), table["raw_intensity"].to_numpy(float), table["background"].to_numpy(float), components,
        table["total_fit"].to_numpy(float), table["residual"].to_numpy(float), details.get("fitted_parameters", {}), details.get("parameter_uncertainties", {}),
        details.get("correlation_matrix", {}), details.get("fit_statistics", {}), details.get("warnings", []), details.get("configuration", {}), details.get("metadata", {}), details.get("convergence", {}), details.get("software_versions", {}),
    )
