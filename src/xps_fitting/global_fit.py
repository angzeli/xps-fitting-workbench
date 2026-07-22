"""Limited two-pass groundwork for shape-linked related spectra."""

from __future__ import annotations

from copy import deepcopy
from statistics import mean

from .configuration import FitConfig
from .optimiser import fit_spectrum
from .result import FitResult
from .spectrum import Spectrum


def fit_shared_shapes(
    spectra: list[Spectrum], config: FitConfig, *, shared: tuple[str, ...] = ("fwhm", "fraction")
) -> list[FitResult]:
    """Two-pass fits with consensus FWHM/fraction values fixed in pass two.

    This is deterministic groundwork, not a simultaneous joint covariance model.
    Areas and centres remain spectrum-specific; existing centre-offset links remain exact.
    """
    if not spectra:
        raise ValueError("at least one spectrum is required")
    unsupported = set(shared) - {"fwhm", "fraction"}
    if unsupported:
        raise ValueError(f"unsupported shared parameter classes: {sorted(unsupported)}")
    first = [fit_spectrum(spectrum, deepcopy(config)) for spectrum in spectra]
    linked = deepcopy(config)
    for peak in linked.peaks:
        fixed = set(peak.fixed)
        for kind in shared:
            key = f"{peak.label}.{kind}"
            setattr(peak, kind, mean(result.fitted_parameters[key] for result in first))
            fixed.add(kind)
        peak.fixed = tuple(sorted(fixed))
    results = [fit_spectrum(spectrum, deepcopy(linked)) for spectrum in spectra]
    for result in results:
        result.metadata["global_fit_method"] = "two-pass consensus shared shapes"
        result.warnings.append("Global fit is a two-pass consensus approximation; joint covariance is not available.")
    return results
