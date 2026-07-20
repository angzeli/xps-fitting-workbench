"""Deterministic staged constrained fitting."""

from __future__ import annotations

import platform
from dataclasses import replace

import numpy as np
import scipy
from scipy.optimize import least_squares

from .backgrounds import linear, shirley
from .configuration import FitConfig, PeakConfig
from .constraints import validate_links
from .diagnostics import statistics
from .models import evaluate_peak, resolve_links
from .result import FitResult
from .spectrum import Spectrum


def _parameter_table(peaks: list[PeakConfig]) -> tuple[dict[str, float], dict[str, tuple[float, float]]]:
    values, bounds = {}, {}
    for peak in peaks:
        for name in ("area", "centre", "fwhm", "fraction"):
            values[f"{peak.label}.{name}"] = float(getattr(peak, name))
            bounds[f"{peak.label}.{name}"] = tuple(getattr(peak, f"{name}_bounds"))
    return values, bounds


def _independent_names(peaks: list[PeakConfig], stage: str, release_fraction: bool) -> list[str]:
    allowed = {"area"}
    if stage in {"centres", "widths", "fractions"}: allowed.add("centre")
    if stage in {"widths", "fractions"}: allowed.add("fwhm")
    if stage == "fractions" and release_fraction: allowed.add("fraction")
    names, widths, fractions = [], set(), set()
    for peak in peaks:
        for name in ("area", "centre", "fwhm", "fraction"):
            if name not in allowed or name in peak.fixed: continue
            if name == "area" and peak.area_ratio_to: continue
            if name == "centre" and peak.centre_offset_from: continue
            if name == "fwhm" and peak.width_group:
                if peak.width_group in widths: continue
                widths.add(peak.width_group)
            if name == "fraction" and peak.fraction_group:
                if peak.fraction_group in fractions: continue
                fractions.add(peak.fraction_group)
            names.append(f"{peak.label}.{name}")
    return names


def fit_spectrum(spectrum: Spectrum, config: FitConfig, *, backend: str = "scipy") -> FitResult:
    """Fit a configured chemical hypothesis using deterministic staged optimisation."""
    if backend != "scipy":
        raise ValueError("this installation currently provides the exercised scipy backend")
    validate_links(config.peaks)
    x, y = spectrum.binding_energy, spectrum.intensity
    base_background = linear(x, y[0], y[-1]) if config.background == "linear" else shirley(y)
    values, bounds = _parameter_table(config.peaks)
    rng = np.random.default_rng(config.random_seed)
    best = None
    solutions: list[float] = []
    final_names: list[str] = []
    stages = ["areas", "centres", "widths"] + (["fractions"] if config.release_fraction else [])
    for start in range(max(1, config.multistart)):
        trial = dict(values)
        if start:
            for peak in config.peaks:
                for name in ("area", "centre", "fwhm"):
                    key = f"{peak.label}.{name}"; lo, hi = bounds[key]
                    span = (hi - lo) if np.isfinite(hi) else max(abs(trial[key]), 1.0)
                    trial[key] = float(np.clip(trial[key] + rng.normal(0, 0.08 * span), lo, hi))
        result = None
        background = base_background.copy()
        for stage in stages:
            names = _independent_names(config.peaks, stage, config.release_fraction)
            lower = np.array([bounds[name][0] for name in names]); upper = np.array([bounds[name][1] for name in names])
            def residual(vector: np.ndarray) -> np.ndarray:
                current = dict(trial); current.update(zip(names, vector)); current = resolve_links(config.peaks, current)
                model = sum((evaluate_peak(x, peak, current) for peak in config.peaks), start=np.zeros_like(x))
                return y - background - model
            result = least_squares(residual, [trial[name] for name in names], bounds=(lower, upper), loss=config.robust_loss)
            trial.update(zip(names, result.x)); trial = resolve_links(config.peaks, trial)
            if config.background == "shirley":
                components = sum((evaluate_peak(x, peak, trial) for peak in config.peaks), start=np.zeros_like(x))
                background = shirley(y - components) + components * 0
        assert result is not None
        score = float(result.fun @ result.fun); solutions.append(score)
        if best is None or score < best[0]: best = (score, result, trial, background, names)
    assert best is not None
    _, raw_result, fitted, background, final_names = best
    components = {peak.label: evaluate_peak(x, peak, fitted) for peak in config.peaks}
    total = background + sum(components.values(), start=np.zeros_like(x)); residual = y - total
    stats = statistics(residual, len(final_names))
    uncertainties: dict[str, float | None] = {name: None for name in fitted}; correlations: dict[str, dict[str, float]] = {}
    warnings: list[str] = []
    if raw_result.jac.size and raw_result.jac.shape[0] > raw_result.jac.shape[1]:
        try:
            covariance = np.linalg.inv(raw_result.jac.T @ raw_result.jac) * stats["reduced_chi_square"]
            stderr = np.sqrt(np.diag(covariance)); corr = covariance / np.outer(stderr, stderr)
            uncertainties.update(dict(zip(final_names, map(float, stderr))))
            correlations = {a: {b: float(corr[i, j]) for j, b in enumerate(final_names)} for i, a in enumerate(final_names)}
            if np.any(np.abs(corr - np.eye(len(corr))) > 0.95): warnings.append("Parameter correlation exceeds 0.95.")
        except np.linalg.LinAlgError: warnings.append("Covariance matrix is singular; uncertainties are unavailable.")
    for peak in config.peaks:
        for name in ("area", "centre", "fwhm", "fraction"):
            key = f"{peak.label}.{name}"; lo, hi = bounds[key]; value = fitted[key]
            scale = max(1.0, abs(value), abs(hi - lo) if np.isfinite(hi) else 1.0)
            if abs(value - lo) <= 1e-5 * scale or (np.isfinite(hi) and abs(hi - value) <= 1e-5 * scale): warnings.append(f"{key} is at or near a bound.")
        if fitted[f"{peak.label}.area"] < 0.005 * sum(p.area for p in config.peaks): warnings.append(f"{peak.label} is a negligible component.")
    for index, first in enumerate(config.peaks):
        for second in config.peaks[index + 1:]:
            separation = abs(fitted[f"{first.label}.centre"] - fitted[f"{second.label}.centre"])
            mean_width = (fitted[f"{first.label}.fwhm"] + fitted[f"{second.label}.fwhm"]) / 2
            if separation < 0.5 * mean_width: warnings.append(f"{first.label} and {second.label} are unresolved by the 0.5 FWHM criterion.")
    if not raw_result.success: warnings.append(f"Convergence warning: {raw_result.message}")
    if np.any(background < 0): warnings.append("Background contains negative values.")
    if len(solutions) > 1 and (max(solutions) - min(solutions)) / max(min(solutions), 1e-30) > 0.05: warnings.append("Multiple initialisations produced materially different solutions.")
    return FitResult(x, y, background, components, total, residual, fitted, uncertainties, correlations, stats, warnings, config.to_dict(), dict(spectrum.metadata), {"success": bool(raw_result.success), "message": raw_result.message, "evaluations": raw_result.nfev, "backend": backend, "multistart_rss": solutions}, {"xps_fitting": "0.1.0", "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__})
