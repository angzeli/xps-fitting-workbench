"""Reconstruct plotting-only results from Phase 1 exports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..result import FitResult

_REQUIRED_ARRAY_KEYS = ("energy", "raw_intensity", "background", "total_fit", "residual")
_REQUIRED_CURVE_COLUMNS = (
    "binding_energy_eV",
    "raw_intensity",
    "background",
    "total_fit",
    "residual",
)


def _require_fields(available: set[str], required: tuple[str, ...], source: str) -> None:
    missing = [name for name in required if name not in available]
    if missing:
        raise ValueError(
            f"{source} is missing required stored fields: {', '.join(missing)}; "
            "raw_intensity and background must be supplied and are never reconstructed"
        )


def fit_result_from_dict(data: dict[str, Any]) -> FitResult:
    _require_fields(set(data), _REQUIRED_ARRAY_KEYS, "full FitResult JSON")
    arrays = {key: np.asarray(data[key], dtype=float) for key in _REQUIRED_ARRAY_KEYS}
    components = {label: np.asarray(curve, dtype=float) for label, curve in data.get("components", {}).items()}
    return FitResult(
        **arrays,
        components=components,
        fitted_parameters=data.get("fitted_parameters", {}),
        parameter_uncertainties=data.get("parameter_uncertainties", {}),
        correlation_matrix=data.get("correlation_matrix", {}),
        fit_statistics=data.get("fit_statistics", {}),
        warnings=data.get("warnings", []),
        configuration=data.get("configuration", {}),
        metadata=data.get("metadata", {}),
        convergence=data.get("convergence", {}),
        software_versions=data.get("software_versions", {}),
    )


def load_curve_result(path: str | Path, metadata: str | Path | dict[str, Any] | None = None) -> FitResult:
    """Load a full-result JSON or CSV/XLSX curves plus Phase 1 JSON metadata."""
    path = Path(path)
    if path.is_dir():
        if metadata is not None:
            raise ValueError("fit bundles contain their own metadata; do not pass a separate metadata source")
        from ..export import load_fit_bundle

        return load_fit_bundle(path)
    if path.suffix.lower() == ".json":
        return fit_result_from_dict(json.loads(path.read_text(encoding="utf-8")))
    if path.suffix.lower() == ".csv":
        table = pd.read_csv(path)
    elif path.suffix.lower() in {".xlsx", ".xls"}:
        table = pd.read_excel(path, sheet_name="curves")
    else:
        raise ValueError("plot source must be a full JSON result or CSV/XLSX curve table")
    _require_fields(set(table.columns), _REQUIRED_CURVE_COLUMNS, "curve table")
    details = (
        json.loads(Path(metadata).read_text(encoding="utf-8"))
        if isinstance(metadata, (str, Path))
        else dict(metadata or {})
    )
    components = {
        column.removeprefix("component:"): table[column].to_numpy(float)
        for column in table
        if column.startswith("component:")
    }
    return FitResult(
        table["binding_energy_eV"].to_numpy(float),
        table["raw_intensity"].to_numpy(float),
        table["background"].to_numpy(float),
        components,
        table["total_fit"].to_numpy(float),
        table["residual"].to_numpy(float),
        details.get("fitted_parameters", {}),
        details.get("parameter_uncertainties", {}),
        details.get("correlation_matrix", {}),
        details.get("fit_statistics", {}),
        details.get("warnings", []),
        details.get("configuration", {}),
        details.get("metadata", {}),
        details.get("convergence", {}),
        details.get("software_versions", {}),
    )
