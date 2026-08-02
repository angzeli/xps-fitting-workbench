"""Ordered candidate fitting and statistical projection without model selection."""

from __future__ import annotations

from .configuration import FitConfig
from .optimiser import fit_spectrum
from .result import FitResult
from .spectrum import Spectrum


def compare_models(spectrum: Spectrum, configurations: list[FitConfig]) -> dict[str, FitResult]:
    """Fit each uniquely named hypothesis and preserve caller-supplied order."""
    if len({config.name for config in configurations}) != len(configurations):
        raise ValueError("candidate model names must be unique")
    return {config.name: fit_spectrum(spectrum, config) for config in configurations}


def comparison_table(results: dict[str, FitResult]) -> list[dict[str, object]]:
    """Project results into ordered statistics without declaring a preferred model."""
    table = []
    for name, result in results.items():
        table.append(
            {
                "model": name,
                **{
                    key: result.fit_statistics[key]
                    for key in (
                        "aic",
                        "aicc",
                        "bic",
                        "rss",
                        "rms_residual",
                        "residual_mean",
                        "max_abs_residual",
                        "durbin_watson",
                        "residual_runs",
                    )
                },
                "warning_count": len(result.warnings),
                "warnings": list(result.warnings),
                "multistart_rss": result.convergence.get("multistart_rss", []),
            }
        )
    return table
