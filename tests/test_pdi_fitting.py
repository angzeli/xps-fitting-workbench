"""Verify synthetic PDI recovery and persistence-before-plotting workflow order."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import matplotlib.pyplot as plt
import numpy as np
import pytest

from xps_fitting.configuration import load_config
from xps_fitting.lineshapes import pseudo_voigt
from xps_fitting.optimiser import fit_spectrum
from xps_fitting.project_workflow import fit_region_candidates
from xps_fitting.result import FitResult
from xps_fitting.spectrum import Spectrum

ROOT = Path(__file__).resolve().parents[1]
FIT_CONFIGS = ROOT / "configs" / "fits"


def _linear_background(x: np.ndarray, low: float, high: float) -> np.ndarray:
    """Return an endpoint-defined background on the test energy grid."""
    return low + (high - low) * (x - x[0]) / (x[-1] - x[0])


def test_n1s_one_component_synthetic_recovery() -> None:
    x = np.linspace(392.0, 410.0, 181)
    y = _linear_background(x, 24500.0, 24300.0) + pseudo_voigt(x, 25000.0, 399.92, 1.3, 0.5)
    config = replace(load_config(FIT_CONFIGS / "pdi_h_cooh_n1s_1.json"), multistart=3)

    result = fit_spectrum(Spectrum(x, y, region="N 1s"), config)

    assert result.fitted_parameters["imide_N-C=O.centre"] == pytest.approx(399.92, abs=0.02)
    assert result.fitted_parameters["imide_N-C=O.fwhm"] == pytest.approx(1.3, rel=0.03)
    assert result.fitted_parameters["imide_N-C=O.area"] == pytest.approx(25000.0, rel=0.03)


@pytest.mark.parametrize(
    ("filename", "components"),
    [
        (
            "pdi_h_cooh_o1s_2.json",
            [("carbonyl_O", 140000.0, 531.0), ("acid_hydroxyl_OH", 45000.0, 532.7)],
        ),
        (
            "pdi_h_cooh_o1s_3.json",
            [
                ("imide_carbonyl_O", 100000.0, 530.9),
                ("acid_carbonyl_O", 50000.0, 531.7),
                ("acid_hydroxyl_OH", 50000.0, 532.9),
            ],
        ),
    ],
)
def test_o1s_synthetic_recovery(filename, components) -> None:
    x = np.linspace(525.0, 545.0, 201)
    y = _linear_background(x, 22500.0, 29000.0)
    for _, area, centre in components:
        y = y + pseudo_voigt(x, area, centre, 1.4, 0.5)
    config = replace(load_config(FIT_CONFIGS / filename), multistart=3)

    result = fit_spectrum(Spectrum(x, y, region="O 1s"), config)

    for label, area, centre in components:
        assert result.fitted_parameters[f"{label}.centre"] == pytest.approx(centre, abs=0.08)
        assert result.fitted_parameters[f"{label}.area"] == pytest.approx(area, rel=0.12)
        assert result.fitted_parameters[f"{label}.fwhm"] == pytest.approx(1.4, rel=0.05)
    assert result.convergence["stoichiometric_area_ratio"]


def test_candidate_persistence_precedes_diagnostic_plotting(tmp_path, monkeypatch) -> None:
    source = tmp_path / "N1s Scan.VGD"
    source.write_bytes(b"experimental")
    x = np.linspace(398.0, 402.0, 41)
    background = np.linspace(10.0, 11.0, x.size)
    component = pseudo_voigt(x, 100.0, 400.0, 1.2, 0.5)
    result = FitResult(
        x,
        background + component,
        background,
        {"imide_N-C=O": component},
        background + component,
        np.zeros_like(x),
        {
            "imide_N-C=O.area": 100.0,
            "imide_N-C=O.centre": 400.0,
            "imide_N-C=O.fwhm": 1.2,
            "imide_N-C=O.fraction": 0.5,
        },
        configuration={"name": "N1s_1_linear", "region": "N 1s", "background": "linear", "peaks": []},
        metadata={"data_origin": "experimental"},
    )
    state = {"persisted": False}
    bundle = tmp_path / "candidate.bundle"

    monkeypatch.setattr("xps_fitting.project_workflow.discover_raw_regions", lambda _: {"N1s": source})
    monkeypatch.setattr("xps_fitting.project_workflow.read_vgd", lambda _: Spectrum(x, result.raw_intensity))
    monkeypatch.setattr("xps_fitting.project_workflow.compare_models", lambda *_: {"N1s_1_linear": result})

    def persist(*args, **kwargs):
        state["persisted"] = True
        return {"N1s_1_linear": bundle}

    def plot(*args, **kwargs):
        assert state["persisted"] is True
        return plt.subplots()

    monkeypatch.setattr("xps_fitting.project_workflow.persist_candidate_results", persist)
    monkeypatch.setattr(
        "xps_fitting.project_workflow.validate_fit_bundle",
        lambda *_args, **_kwargs: SimpleNamespace(errors=(), to_dict=lambda: {}),
    )
    monkeypatch.setattr("xps_fitting.review.candidate_review_summary", lambda _: {})
    monkeypatch.setattr("xps_fitting.project_workflow.plot_xps_fit", plot)
    monkeypatch.setattr(
        "xps_fitting.project_workflow.export_figure",
        lambda *args, **kwargs: {"png": tmp_path / "diagnostic.png", "pdf": tmp_path / "diagnostic.pdf"},
    )

    output = fit_region_candidates(
        tmp_path,
        "PDI-H-COOH",
        "N1s",
        configuration_paths=(FIT_CONFIGS / "pdi_h_cooh_n1s_1.json",),
    )

    assert output["candidate_bundles"]["N1s_1_linear"] == str(bundle)
