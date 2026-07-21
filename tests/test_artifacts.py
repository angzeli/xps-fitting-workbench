import copy
import json

import numpy as np
import pytest

from xps_fitting.artifacts import save_candidate_bundle, validate_fit_bundle
from xps_fitting.export import load_fit_bundle, save_fit_bundle
from xps_fitting.result import FitResult


def experimental_result() -> FitResult:
    energy = np.linspace(280.0, 292.0, 121)
    background = np.linspace(20.0, 35.0, energy.size)
    component = 100.0 * np.exp(-(((energy - 284.3762) / 0.8) ** 2))
    total = background + component
    residual = 0.2 * np.sin(energy)
    return FitResult(
        energy,
        total + residual,
        background,
        {"aromatic_C-C_C=C": component},
        total,
        residual,
        {
            "aromatic_C-C_C=C.centre": 284.3762,
            "aromatic_C-C_C=C.area": 100.0,
            "aromatic_C-C_C=C.fwhm": 1.2,
        },
        configuration={
            "name": "C1s_candidate",
            "region": "C 1s",
            "peaks": [{"label": "aromatic_C-C_C=C", "centre": 284.3762}],
        },
        metadata={"data_origin": "experimental"},
    )


def test_candidate_bundle_has_hashes_round_trips_and_does_not_mutate(tmp_path) -> None:
    source = tmp_path / "C1s Scan.VGD"
    source.write_bytes(b"immutable experimental source")
    result = experimental_result()
    before = copy.deepcopy(result.to_dict())
    bundle = tmp_path / "artifacts" / "candidate.bundle"

    save_candidate_bundle(
        result,
        bundle,
        sample="PDI-H-COOH",
        region="C1s",
        source_path=source,
        repository_root=tmp_path,
        created_at="2026-07-21T00:00:00+00:00",
    )

    assert result.to_dict() == before
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert set(manifest["integrity"]) == {"curves.csv", "metadata.json"}
    assert manifest["artifact"]["state"] == "candidate"
    assert manifest["artifact"]["source"]["path"] == "C1s Scan.VGD"
    assert len(manifest["artifact"]["source"]["sha256"]) == 64
    reloaded = load_fit_bundle(bundle)
    np.testing.assert_array_equal(reloaded.raw_intensity, result.raw_intensity)
    assert reloaded.metadata["review_status"] == "candidate"
    assert reloaded.metadata["historical_result_recovered"] is False

    report = validate_fit_bundle(bundle, repository_root=tmp_path)
    assert not report.errors
    assert not report.publication_eligible
    assert "scientifically reviewed" in " ".join(report.publication_reasons)
    assert report.component_envelope_error < 1e-12
    assert report.residual_reconstruction_error < 1e-12


def test_bundle_member_tampering_is_detected(tmp_path) -> None:
    source = tmp_path / "source.VGD"
    source.write_bytes(b"source")
    bundle = tmp_path / "candidate.bundle"
    save_candidate_bundle(
        experimental_result(),
        bundle,
        sample="PDI-H-COOH",
        region="C1s",
        source_path=source,
        repository_root=tmp_path,
    )
    with (bundle / "curves.csv").open("a", encoding="utf-8") as stream:
        stream.write("\n")
    with pytest.raises(ValueError, match="member hash mismatch"):
        load_fit_bundle(bundle)


def test_legacy_and_synthetic_results_are_never_publication_eligible(tmp_path) -> None:
    result = experimental_result()
    legacy = tmp_path / "legacy.bundle"
    save_fit_bundle(result, legacy)
    legacy_report = validate_fit_bundle(legacy)
    assert not legacy_report.publication_eligible
    assert "legacy bundle" in " ".join(legacy_report.publication_reasons)

    result.metadata["data_origin"] = "deterministic synthetic test fixture"
    source = tmp_path / "synthetic.VGD"
    source.write_bytes(b"synthetic")
    with pytest.raises(ValueError, match="require explicit data_origin='experimental'"):
        save_candidate_bundle(
            result,
            tmp_path / "synthetic.bundle",
            sample="PDI-H-COOH",
            region="C1s",
            source_path=source,
        )
