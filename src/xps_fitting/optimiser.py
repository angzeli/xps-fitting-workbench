"""Deterministic staged constrained fitting."""

from __future__ import annotations

import platform
from types import SimpleNamespace
from typing import Any, Callable

import numpy as np
import scipy
from scipy.optimize import least_squares

from ._version import __version__
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
    if stage in {"centres", "widths", "fractions"}:
        allowed.add("centre")
    if stage in {"widths", "fractions"}:
        allowed.add("fwhm")
    if stage == "fractions" and release_fraction:
        allowed.add("fraction")
    names, widths, fractions = [], set(), set()
    for peak in peaks:
        for name in ("area", "centre", "fwhm", "fraction"):
            if name not in allowed or name in peak.fixed:
                continue
            if name == "area" and peak.area_ratio_to:
                continue
            if name == "centre" and peak.centre_offset_from:
                continue
            if name == "fwhm" and peak.width_group:
                if peak.width_group in widths:
                    continue
                widths.add(peak.width_group)
            if name == "fraction" and peak.fraction_group:
                if peak.fraction_group in fractions:
                    continue
                fractions.add(peak.fraction_group)
            names.append(f"{peak.label}.{name}")
    return names


def _solve_stage(
    residual: Callable[[np.ndarray], np.ndarray],
    names: list[str],
    trial: dict[str, float],
    bounds: dict[str, tuple[float, float]],
    robust_loss: str,
    backend: str,
) -> Any:
    lower = np.array([bounds[name][0] for name in names])
    upper = np.array([bounds[name][1] for name in names])
    if backend == "scipy":
        result = least_squares(residual, [trial[name] for name in names], bounds=(lower, upper), loss=robust_loss)
        result.parameter_names = names
        result.covar = None
        return result

    import lmfit

    parameters = lmfit.Parameters()
    for index, name in enumerate(names):
        parameters.add(f"v{index}", value=trial[name], min=bounds[name][0], max=bounds[name][1])

    def lmfit_residual(params: Any) -> np.ndarray:
        return residual(np.array([params[f"v{index}"].value for index in range(len(names))]))

    fitted_result = lmfit.minimize(lmfit_residual, parameters, method="least_squares", loss=robust_loss)
    vector = np.array([fitted_result.params[f"v{index}"].value for index in range(len(names))])
    return SimpleNamespace(
        x=vector,
        fun=np.asarray(fitted_result.residual),
        jac=None,
        success=bool(fitted_result.success),
        message=str(fitted_result.message),
        nfev=int(fitted_result.nfev),
        covar=fitted_result.covar,
        parameter_names=names,
    )


def fit_spectrum(spectrum: Spectrum, config: FitConfig, *, backend: str = "lmfit") -> FitResult:
    """Fit a configured hypothesis using deterministic staged optimisation.

    Each initialisation releases areas, centres, widths, and optionally line-shape
    fractions in that order. Linked parameters are resolved at every evaluation;
    Shirley backgrounds alternate with the current component envelope. The returned
    result is the initialisation with the lowest unpenalised residual sum of squares.
    """
    if backend not in {"lmfit", "scipy"}:
        raise ValueError("backend must be 'lmfit' or 'scipy'")
    validate_links(config.peaks)
    x, y = spectrum.binding_energy, spectrum.intensity
    base_background = linear(x, y[0], y[-1]) if config.background == "linear" else shirley(y)
    values, bounds = _parameter_table(config.peaks)
    rng = np.random.default_rng(config.random_seed)
    best = None
    solutions: list[float] = []
    final_names: list[str] = []
    stages = ["areas", "centres", "widths"] + (["fractions"] if config.release_fraction else [])
    # Run the same ordered release schedule from each deterministic initialisation.
    for start in range(max(1, config.multistart)):
        trial = dict(values)
        if start:
            for peak in config.peaks:
                for name in ("area", "centre", "fwhm"):
                    key = f"{peak.label}.{name}"
                    lo, hi = bounds[key]
                    span = (hi - lo) if np.isfinite(hi) else max(abs(trial[key]), 1.0)
                    trial[key] = float(np.clip(trial[key] + rng.normal(0, 0.08 * span), lo, hi))
        result = None
        background = base_background.copy()
        background_iterations = 0
        for stage in stages:
            names = _independent_names(config.peaks, stage, config.release_fraction)

            def residual(vector: np.ndarray) -> np.ndarray:
                current = dict(trial)
                current.update(zip(names, vector))
                current = resolve_links(config.peaks, current)
                model = sum((evaluate_peak(x, peak, current) for peak in config.peaks), start=np.zeros_like(x))
                data_residual = y - background - model
                if config.width_penalty > 0 and len(config.peaks) > 1:
                    widths = np.array([current[f"{peak.label}.fwhm"] for peak in config.peaks])
                    penalty = np.sqrt(config.width_penalty) * (widths[1:] - widths[:-1])
                    return np.concatenate((data_residual, penalty))
                return data_residual

            iterations = config.max_background_iterations if config.background == "shirley" else 1
            for _ in range(iterations):
                result = _solve_stage(residual, names, trial, bounds, config.robust_loss, backend)
                trial.update(zip(names, result.x))
                trial = resolve_links(config.peaks, trial)
                if config.background != "shirley":
                    break
                components = sum((evaluate_peak(x, peak, trial) for peak in config.peaks), start=np.zeros_like(x))
                updated_background = shirley(y - components)
                background_iterations += 1
                converged = np.max(np.abs(updated_background - background)) <= 1e-7 * max(1.0, np.ptp(y))
                background = updated_background
                if converged:
                    break
            if config.background == "shirley":
                result = _solve_stage(residual, names, trial, bounds, config.robust_loss, backend)
                trial.update(zip(names, result.x))
                trial = resolve_links(config.peaks, trial)
        assert result is not None
        current = resolve_links(config.peaks, trial)
        # Rank starts by the physical residual, excluding any width-penalty terms.
        physical_residual = (
            y - background - sum((evaluate_peak(x, peak, current) for peak in config.peaks), start=np.zeros_like(x))
        )
        score = float(physical_residual @ physical_residual)
        solutions.append(score)
        if best is None or score < best[0]:
            best = (score, result, trial, background, names, background_iterations)
    assert best is not None
    _, raw_result, fitted, background, final_names, background_iterations = best
    # Reconstruct aligned curves and diagnostics from the best linked parameter set.
    components = {peak.label: evaluate_peak(x, peak, fitted) for peak in config.peaks}
    total = background + sum(components.values(), start=np.zeros_like(x))
    residual = y - total
    stats = statistics(residual, len(final_names))
    uncertainties: dict[str, float | None] = {name: None for name in fitted}
    correlations: dict[str, dict[str, float]] = {}
    warnings: list[str] = []
    # Prefer backend covariance, with a Jacobian estimate when the backend omits it.
    covariance = raw_result.covar
    if (
        covariance is None
        and raw_result.jac is not None
        and raw_result.jac.size
        and raw_result.jac.shape[0] > raw_result.jac.shape[1]
    ):
        try:
            covariance = np.linalg.inv(raw_result.jac.T @ raw_result.jac) * stats["reduced_chi_square"]
        except np.linalg.LinAlgError:
            covariance = None
    if covariance is not None:
        try:
            stderr = np.sqrt(np.maximum(np.diag(covariance), 0))
            with np.errstate(divide="ignore", invalid="ignore"):
                corr = covariance / np.outer(stderr, stderr)
            corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)
            uncertainties.update(dict(zip(raw_result.parameter_names, map(float, stderr))))
            correlations = {
                a: {b: float(corr[i, j]) for j, b in enumerate(raw_result.parameter_names)}
                for i, a in enumerate(raw_result.parameter_names)
            }
            if np.any(np.abs(corr - np.eye(len(corr))) > 0.95):
                warnings.append("Parameter correlation exceeds 0.95.")
        except np.linalg.LinAlgError:
            warnings.append("Covariance matrix is singular; uncertainties are unavailable.")
    fitted_area_total = sum(fitted[f"{peak.label}.area"] for peak in config.peaks)
    for peak in config.peaks:
        for name in ("area", "centre", "fwhm", "fraction"):
            key = f"{peak.label}.{name}"
            lo, hi = bounds[key]
            value = fitted[key]
            scale = max(1.0, abs(value), abs(hi - lo) if np.isfinite(hi) else 1.0)
            if abs(value - lo) <= 1e-5 * scale or (np.isfinite(hi) and abs(hi - value) <= 1e-5 * scale):
                warnings.append(f"{key} is at or near a bound.")
        if fitted_area_total > 0 and fitted[f"{peak.label}.area"] < 0.005 * fitted_area_total:
            warnings.append(f"{peak.label} is a negligible component.")
    for index, first in enumerate(config.peaks):
        for second in config.peaks[index + 1 :]:
            separation = abs(fitted[f"{first.label}.centre"] - fitted[f"{second.label}.centre"])
            mean_width = (fitted[f"{first.label}.fwhm"] + fitted[f"{second.label}.fwhm"]) / 2
            if separation < 0.5 * mean_width:
                warnings.append(f"{first.label} and {second.label} are unresolved by the 0.5 FWHM criterion.")
    fitted_widths = [fitted[f"{peak.label}.fwhm"] for peak in config.peaks]
    if len(fitted_widths) > 1 and max(fitted_widths) > 1.5 * min(fitted_widths):
        warnings.append("Structural component FWHMs diverge by more than 50%.")
    stoichiometric_area_ratio: dict[str, dict[str, float]] = {}
    nominal_ratio = config.metadata.get("nominal_structural_ratio")
    if isinstance(nominal_ratio, dict) and nominal_ratio:
        reference = next((peak.label for peak in config.peaks if peak.label in nominal_ratio), None)
        if reference and fitted[f"{reference}.area"] > 0 and float(nominal_ratio[reference]) > 0:
            fitted_reference = fitted[f"{reference}.area"]
            nominal_reference = float(nominal_ratio[reference])
            materially_different = False
            for peak in config.peaks:
                if peak.label not in nominal_ratio:
                    continue
                fitted_relative = fitted[f"{peak.label}.area"] / fitted_reference
                nominal_relative = float(nominal_ratio[peak.label]) / nominal_reference
                ratio_to_nominal = fitted_relative / nominal_relative
                stoichiometric_area_ratio[peak.label] = {
                    "fitted_relative": float(fitted_relative),
                    "nominal_relative": float(nominal_relative),
                    "ratio_to_nominal": float(ratio_to_nominal),
                }
                materially_different |= ratio_to_nominal < 0.5 or ratio_to_nominal > 2.0
            if materially_different:
                warnings.append(
                    "Fitted structural area ratios differ by more than a factor of two from nominal counts."
                )
    if not raw_result.success:
        warnings.append(f"Convergence warning: {raw_result.message}")
    if np.any(background < 0):
        warnings.append("Background contains negative values.")
    if len(solutions) > 1 and (max(solutions) - min(solutions)) / max(min(solutions), 1e-30) > 0.05:
        warnings.append("Multiple initialisations produced materially different solutions.")
    versions = {
        "xps_fitting": __version__,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
    }
    if backend == "lmfit":
        import lmfit

        versions["lmfit"] = lmfit.__version__
    result_metadata = dict(spectrum.metadata)
    for metadata_key, metadata_value in (
        ("source_file", spectrum.source_file),
        ("sample_name", spectrum.sample_name),
        ("region", spectrum.region),
    ):
        if metadata_value:
            result_metadata.setdefault(metadata_key, metadata_value)
    return FitResult(
        x,
        y,
        background,
        components,
        total,
        residual,
        fitted,
        uncertainties,
        correlations,
        stats,
        warnings,
        config.to_dict(),
        result_metadata,
        {
            "success": bool(raw_result.success),
            "message": raw_result.message,
            "evaluations": raw_result.nfev,
            "backend": backend,
            "multistart_rss": solutions,
            "background_iterations": background_iterations,
            "stoichiometric_area_ratio": stoichiometric_area_ratio,
        },
        versions,
    )
