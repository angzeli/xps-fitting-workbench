"""Chemistry-constrained XPS fitting tools."""

from ._version import __version__
from .calibration import BindingEnergyCalibration, calibrate_sample_binding_energy
from .calibration_workflow import (
    CalibrationOutcome,
    CalibrationPlan,
    CalibrationRecord,
    calibrate_reviewed_sample,
    prepare_sample_calibration,
)
from .export import load_fit_bundle, save_fit_bundle
from .publication import load_publication_region, plot_publication_region
from .result import FitResult
from .sample_manifest import SampleManifest, create_sample_manifest, load_sample_manifest
from .spectrum import Spectrum
from .spectrum_artifacts import load_spectrum_bundle, review_spectrum, save_spectrum_bundle

__all__ = [
    "BindingEnergyCalibration",
    "CalibrationOutcome",
    "CalibrationPlan",
    "CalibrationRecord",
    "FitResult",
    "SampleManifest",
    "Spectrum",
    "__version__",
    "calibrate_sample_binding_energy",
    "calibrate_reviewed_sample",
    "create_sample_manifest",
    "load_fit_bundle",
    "load_publication_region",
    "load_sample_manifest",
    "load_spectrum_bundle",
    "prepare_sample_calibration",
    "plot_publication_region",
    "review_spectrum",
    "save_fit_bundle",
    "save_spectrum_bundle",
]
