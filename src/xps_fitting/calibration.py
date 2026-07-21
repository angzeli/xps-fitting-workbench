"""Non-mutating sample-wide binding-energy calibration."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from .result import FitResult
from .spectrum import Spectrum

CALIBRATION_METADATA_KEY = "binding_energy_calibration"


@dataclass(frozen=True)
class BindingEnergyCalibration:
    """A rigid binding-energy reference shared by every core level of a sample."""

    reference_core_level: str
    reference_component: str
    observed_eV: float
    target_eV: float
    offset_eV: float

    def to_dict(self) -> dict[str, str | float]:
        return {
            "reference_core_level": self.reference_core_level,
            "reference_component": self.reference_component,
            "observed_eV": self.observed_eV,
            "target_eV": self.target_eV,
            "offset_eV": self.offset_eV,
            "method": "rigid sample-wide binding-energy shift",
        }


def _sample_name(dataset: FitResult | Spectrum) -> str:
    if isinstance(dataset, Spectrum):
        return dataset.sample_name or str(dataset.metadata.get("sample_name", ""))
    return str(dataset.metadata.get("sample_name", ""))


def _validate_datasets(fit_results: Mapping[str, FitResult], spectra: Mapping[str, Spectrum]) -> None:
    datasets: list[tuple[str, FitResult | Spectrum]] = [*fit_results.items(), *spectra.items()]
    names = {_sample_name(dataset) for _, dataset in datasets} - {""}
    if len(names) > 1:
        raise ValueError(f"sample-wide calibration received mixed samples: {', '.join(sorted(names))}")
    already_calibrated = [
        core_level
        for core_level, dataset in datasets
        if CALIBRATION_METADATA_KEY in dataset.metadata
    ]
    if already_calibrated:
        raise ValueError(
            "binding-energy calibration is already present for: " + ", ".join(already_calibrated)
        )


def _shift_bounds(bounds: Any, offset_eV: float) -> Any:
    if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
        raise ValueError("peak centre_bounds must contain exactly two values")
    shifted = [float(bound) + offset_eV for bound in bounds]
    return tuple(shifted) if isinstance(bounds, tuple) else shifted


def _shift_configuration(configuration: dict[str, Any], offset_eV: float) -> dict[str, Any]:
    shifted = deepcopy(configuration)
    peaks = shifted.get("peaks", [])
    if not isinstance(peaks, list):
        raise ValueError("FitResult configuration peaks must be a list")
    for peak in peaks:
        if not isinstance(peak, dict):
            raise ValueError("FitResult configuration peaks must be mappings")
        if "centre" in peak:
            peak["centre"] = float(peak["centre"]) + offset_eV
        if "centre_bounds" in peak:
            peak["centre_bounds"] = _shift_bounds(peak["centre_bounds"], offset_eV)
    return shifted


def _calibration_metadata(metadata: dict[str, Any], calibration: BindingEnergyCalibration) -> dict[str, Any]:
    shifted = deepcopy(metadata)
    shifted[CALIBRATION_METADATA_KEY] = calibration.to_dict()
    return shifted


def _shift_fit_result(result: FitResult, calibration: BindingEnergyCalibration) -> FitResult:
    shifted = deepcopy(result)
    shifted.energy = np.asarray(result.energy, dtype=float).copy() + calibration.offset_eV
    shifted.fitted_parameters = {
        name: float(value) + calibration.offset_eV if name.endswith(".centre") else value
        for name, value in result.fitted_parameters.items()
    }
    shifted.configuration = _shift_configuration(result.configuration, calibration.offset_eV)
    shifted.metadata = _calibration_metadata(result.metadata, calibration)
    return shifted


def _shift_spectrum(spectrum: Spectrum, calibration: BindingEnergyCalibration) -> Spectrum:
    return replace(
        deepcopy(spectrum),
        binding_energy=np.asarray(spectrum.binding_energy, dtype=float).copy() + calibration.offset_eV,
        metadata=_calibration_metadata(spectrum.metadata, calibration),
    )


def calibrate_sample_binding_energy(
    fit_results: Mapping[str, FitResult],
    *,
    spectra: Mapping[str, Spectrum] | None = None,
    reference_core_level: str = "C 1s",
    reference_component: str = "aromatic_C-C_C=C",
    target_eV: float = 284.8,
) -> tuple[dict[str, FitResult], dict[str, Spectrum], BindingEnergyCalibration]:
    """Reference all supplied core levels to one fitted component without refitting.

    The offset is ``target_eV - fitted reference centre``. It is applied to every
    energy axis, absolute fitted centre, and configuration centre/bound. Intensity,
    background, component, total-fit, residual, area, width, and relative-offset
    values are copied unchanged.
    """
    if not fit_results:
        raise ValueError("at least one FitResult is required for binding-energy calibration")
    if reference_core_level not in fit_results:
        raise KeyError(f"reference core level is unavailable: {reference_core_level}")
    if not np.isfinite(target_eV):
        raise ValueError("target_eV must be finite")

    raw_spectra = dict(spectra or {})
    _validate_datasets(fit_results, raw_spectra)
    reference = fit_results[reference_core_level]
    centre_key = f"{reference_component}.centre"
    if centre_key not in reference.fitted_parameters:
        raise KeyError(f"fitted reference centre is unavailable: {centre_key}")
    observed_eV = float(reference.fitted_parameters[centre_key])
    if not np.isfinite(observed_eV):
        raise ValueError(f"fitted reference centre must be finite: {centre_key}")

    calibration = BindingEnergyCalibration(
        reference_core_level=reference_core_level,
        reference_component=reference_component,
        observed_eV=observed_eV,
        target_eV=float(target_eV),
        offset_eV=float(target_eV - observed_eV),
    )
    calibrated_results = {
        core_level: _shift_fit_result(result, calibration) for core_level, result in fit_results.items()
    }
    calibrated_spectra = {
        core_level: _shift_spectrum(spectrum, calibration) for core_level, spectrum in raw_spectra.items()
    }
    return calibrated_results, calibrated_spectra, calibration
