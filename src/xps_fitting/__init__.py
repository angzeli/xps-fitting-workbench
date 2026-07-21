"""Chemistry-constrained XPS fitting tools."""

from ._version import __version__
from .calibration import BindingEnergyCalibration, calibrate_sample_binding_energy
from .export import load_fit_bundle, save_fit_bundle
from .result import FitResult
from .sample_manifest import SampleManifest, create_sample_manifest, load_sample_manifest
from .spectrum import Spectrum

__all__ = [
    "BindingEnergyCalibration",
    "FitResult",
    "SampleManifest",
    "Spectrum",
    "__version__",
    "calibrate_sample_binding_energy",
    "create_sample_manifest",
    "load_fit_bundle",
    "load_sample_manifest",
    "save_fit_bundle",
]
