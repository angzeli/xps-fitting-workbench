"""Verify complete exports, readable bundles, collisions, and curve round-trips."""

import json

import numpy as np
import pandas as pd
import pytest

from xps_fitting.configuration import FitConfig, PeakConfig
from xps_fitting.export import export_result, load_fit_bundle, save_fit_bundle
from xps_fitting.lineshapes import gaussian
from xps_fitting.optimiser import fit_spectrum
from xps_fitting.spectrum import Spectrum


def test_export_bundle_and_curve_consistency(tmp_path) -> None:
    x = np.linspace(0, 10, 101)
    y = 2 + gaussian(x, 100, 5, 1)
    result = fit_spectrum(
        Spectrum(
            x,
            y,
            region="C 1s",
            sample_name="PDI-H-COOH",
            source_file="raw/C1s Scan.VGD",
            metadata={"id": "synthetic"},
        ),
        FitConfig(
            "export", "test", [PeakConfig("p", 5, (4, 6), 90, fwhm=1, fwhm_bounds=(0.8, 1.2), line_shape="gaussian")]
        ),
    )
    paths = export_result(result, tmp_path)
    assert all(path.stat().st_size > 0 for path in paths.values())
    csv = pd.read_csv(paths["csv"])
    xlsx = pd.read_excel(paths["xlsx"], sheet_name="curves")
    assert list(csv.columns) == list(xlsx.columns)
    assert json.loads(paths["json"].read_text())["metadata"]["id"] == "synthetic"
    assert result.metadata["source_file"] == "raw/C1s Scan.VGD"
    assert result.metadata["sample_name"] == "PDI-H-COOH"
    assert result.metadata["region"] == "C 1s"
    assert result.software_versions["xps_fitting"] == "0.3.0"
    with pytest.raises(FileExistsError, match="pass overwrite=True"):
        export_result(result, tmp_path)

    bundle_paths = save_fit_bundle(result, tmp_path / "fit-bundle")
    assert set(bundle_paths) == {"manifest", "curves", "metadata"}
    assert all(path.stat().st_size > 0 for path in bundle_paths.values())
    reloaded = load_fit_bundle(tmp_path / "fit-bundle")
    np.testing.assert_allclose(reloaded.energy, result.energy, rtol=0, atol=1e-12)
    np.testing.assert_allclose(reloaded.total_fit, result.total_fit, rtol=1e-12, atol=1e-12)
    assert reloaded.fitted_parameters == result.fitted_parameters
    assert reloaded.metadata == result.metadata
    assert reloaded.warnings == result.warnings
    with pytest.raises(FileExistsError):
        save_fit_bundle(result, tmp_path / "fit-bundle")

    planned = save_fit_bundle(result, tmp_path / "planned-bundle", dry_run=True)
    assert not any(path.exists() for path in planned.values())
