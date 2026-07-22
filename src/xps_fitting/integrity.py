"""Scientific-array identities and reproducible SHA-256 helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .result import FitResult


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 digest of a file without changing it."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    """Hash a JSON-compatible value using a stable canonical representation."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def result_identity_metrics(result: FitResult) -> dict[str, float]:
    """Calculate the two exact FitResult curve-identity residuals."""
    component_sum = sum(result.components.values(), start=np.zeros_like(result.energy))
    return {
        "max_abs_component_envelope_error": float(np.max(np.abs(result.background + component_sum - result.total_fit))),
        "max_abs_residual_reconstruction_error": float(
            np.max(np.abs(result.raw_intensity - result.total_fit - result.residual))
        ),
    }


def validate_result_integrity(result: FitResult, *, rtol: float = 1e-9, atol: float = 1e-12) -> None:
    """Raise when stored arrays violate the stable FitResult numerical contract."""
    arrays = {
        "energy": result.energy,
        "raw_intensity": result.raw_intensity,
        "background": result.background,
        "total_fit": result.total_fit,
        "residual": result.residual,
        **{f"component:{label}": curve for label, curve in result.components.items()},
    }
    expected_shape = np.asarray(result.energy).shape
    for name, values in arrays.items():
        array = np.asarray(values)
        if array.shape != expected_shape:
            raise ValueError(f"{name} shape does not match energy")
        if not np.all(np.isfinite(array)):
            raise ValueError(f"{name} contains non-finite values")
    component_sum = sum(result.components.values(), start=np.zeros_like(result.energy))
    if not np.allclose(result.background + component_sum, result.total_fit, rtol=rtol, atol=atol):
        raise ValueError("background plus components does not reproduce total_fit")
    if not np.allclose(result.raw_intensity - result.total_fit, result.residual, rtol=rtol, atol=atol):
        raise ValueError("raw_intensity minus total_fit does not reproduce residual")


def result_arrays_equal(first: FitResult, second: FitResult, *, energy_offset: float = 0.0) -> bool:
    """Compare two results, allowing only a declared rigid energy-axis shift."""
    if set(first.components) != set(second.components):
        return False
    if not np.allclose(second.energy, first.energy + energy_offset, rtol=0.0, atol=1e-12):
        return False
    for name in ("raw_intensity", "background", "total_fit", "residual"):
        if not np.array_equal(getattr(first, name), getattr(second, name)):
            return False
    return all(np.array_equal(first.components[name], second.components[name]) for name in first.components)
