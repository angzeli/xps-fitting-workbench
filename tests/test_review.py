"""Exercise cancellation, rejection, and immutable candidate review promotion."""

import json
from pathlib import Path

import numpy as np
import pytest

from xps_fitting.artifacts import load_publication_bundle, save_candidate_bundle, validate_fit_bundle
from xps_fitting.export import load_fit_bundle
from xps_fitting.integrity import result_arrays_equal, sha256_file
from xps_fitting.result import FitResult
from xps_fitting.review import candidate_review_summary, load_review_record, reject_all_candidates, review_candidate


def candidate_result() -> FitResult:
    """Return a fitted experimental-style candidate suitable for review tests."""
    energy = np.linspace(280.0, 292.0, 121)
    background = np.linspace(15.0, 25.0, energy.size)
    component = 100.0 * np.exp(-(((energy - 284.3762) / 0.8) ** 2))
    total = background + component
    residual = 0.1 * np.cos(energy)
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
            "name": "C1s_5",
            "region": "C 1s",
            "peaks": [
                {
                    "label": "aromatic_C-C_C=C",
                    "centre_bounds": [284.3762, 285.0],
                    "fwhm_bounds": [0.5, 2.0],
                    "area_bounds": [0.0, 200.0],
                }
            ],
        },
        metadata={"data_origin": "experimental"},
    )


def make_candidate(tmp_path):
    source = tmp_path / "data" / "raw" / "PDI-H-COOH" / "C1s Scan.VGD"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"raw experimental bytes")
    bundle = tmp_path / "artifacts" / "candidates" / "PDI-H-COOH" / "C1s" / "c1s-5.bundle"
    save_candidate_bundle(
        candidate_result(),
        bundle,
        sample="PDI-H-COOH",
        region="C1s",
        source_path=source,
        repository_root=tmp_path,
        created_at="2026-07-21T01:00:00+00:00",
    )
    return bundle


def approve(candidate, tmp_path, **overrides):
    arguments = {
        "decision": "accepted",
        "reviewer": "Angze Li",
        "notes": ("Residuals inspected", "Assignments reviewed"),
        "residual_inspection_status": "approved",
        "background_approval_status": "approved",
        "component_assignment_approval_status": "approved",
        "constraints_reviewed": True,
        "warnings_acknowledged": True,
        "repository_root": tmp_path,
        "review_date": "2026-07-21T02:00:00+00:00",
    }
    arguments.update(overrides)
    return review_candidate(candidate, tmp_path / "artifacts" / "reviewed", **arguments)


def test_review_cancellation_writes_nothing(tmp_path) -> None:
    candidate = make_candidate(tmp_path)
    result = review_candidate(
        candidate,
        tmp_path / "artifacts" / "reviewed",
        decision="cancelled",
        repository_root=tmp_path,
    )
    assert result is None
    assert not (tmp_path / "artifacts" / "reviewed").exists()


def test_review_creates_immutable_version_and_record_without_changing_candidate(tmp_path) -> None:
    candidate = make_candidate(tmp_path)
    candidate_hashes = {path.name: sha256_file(path) for path in candidate.iterdir() if path.is_file()}
    original = load_fit_bundle(candidate)

    promotion = approve(candidate, tmp_path)
    assert promotion is not None
    assert promotion.version == 1
    assert promotion.reviewed_bundle.name == "C1s.review-v1.bundle"
    assert promotion.review_record.name == "C1s.review-v1.json"
    assert candidate_hashes == {path.name: sha256_file(path) for path in candidate.iterdir() if path.is_file()}
    reviewed = load_fit_bundle(promotion.reviewed_bundle)
    assert result_arrays_equal(original, reviewed)
    assert reviewed.metadata["review_status"] == "reviewed"
    assert reviewed.metadata["calibration_status"] == "uncalibrated"
    record = load_review_record(promotion.review_record)
    assert record.reviewer == "Angze Li" and record.decision == "accepted"

    report = validate_fit_bundle(promotion.reviewed_bundle, repository_root=tmp_path)
    assert report.publication_eligible and not report.errors
    with pytest.raises(ValueError, match="requires a calibrated reviewed artifact"):
        load_publication_bundle(promotion.reviewed_bundle, repository_root=tmp_path)


def test_review_versions_never_overwrite_and_record_tampering_is_detected(tmp_path) -> None:
    candidate = make_candidate(tmp_path)
    first = approve(candidate, tmp_path)
    second = approve(candidate, tmp_path, review_date="2026-07-21T03:00:00+00:00")
    assert first is not None and second is not None and second.version == 2
    with pytest.raises(FileExistsError, match="create a new version"):
        approve(candidate, tmp_path, version=1)

    record_data = json.loads(first.review_record.read_text())
    record_data["notes"] = ["tampered"]
    first.review_record.write_text(json.dumps(record_data))
    report = validate_fit_bundle(first.reviewed_bundle, repository_root=tmp_path)
    assert not report.publication_eligible
    assert "review record SHA-256" in " ".join(report.errors)


def test_review_rejects_a_raw_equals_total_candidate(tmp_path) -> None:
    result = candidate_result()
    result.raw_intensity = result.total_fit.copy()
    result.residual = np.zeros_like(result.energy)
    source = tmp_path / "source.VGD"
    source.write_bytes(b"experimental")
    candidate = tmp_path / "candidate.bundle"
    save_candidate_bundle(
        result,
        candidate,
        sample="PDI-H-COOH",
        region="C1s",
        source_path=source,
        repository_root=tmp_path,
    )
    with pytest.raises(ValueError, match="raw_intensity is identical to total_fit"):
        approve(candidate, tmp_path)


def test_candidate_summary_reports_bound_hits_and_rejection_is_versioned(tmp_path) -> None:
    candidate = make_candidate(tmp_path)
    summary = candidate_review_summary(candidate)
    assert summary["bound_hits"] == [{"parameter": "aromatic_C-C_C=C.centre", "bound": "lower", "value": 284.3762}]

    first = reject_all_candidates(
        (candidate,),
        tmp_path / "artifacts" / "reviewed",
        reviewer="Angze Li",
        notes=("Residual structure requires a revised model.",),
        repository_root=tmp_path,
        review_date="2026-07-21T02:00:00+00:00",
    )
    second = reject_all_candidates(
        (candidate,),
        tmp_path / "artifacts" / "reviewed",
        reviewer="Angze Li",
        repository_root=tmp_path,
        review_date="2026-07-21T03:00:00+00:00",
    )
    assert first.version == 1 and second.version == 2
    assert first.record.decision == "rejected_all"
    assert first.rejection_record.is_file()
    assert not (tmp_path / "artifacts" / "reviewed" / "PDI-H-COOH" / "uncalibrated").exists()


@pytest.mark.parametrize(
    ("bounds", "expected_bounds", "expected_hit"),
    [
        ([0.0, None], [0.0, "unbounded"], None),
        ([None, 10.0], ["unbounded", 10.0], "upper"),
        ([None, None], ["unbounded", "unbounded"], None),
        ([0.0, 10.0], [0.0, 10.0], "upper"),
    ],
)
def test_candidate_summary_handles_optional_bounds(monkeypatch, bounds, expected_bounds, expected_hit) -> None:
    result = candidate_result()
    result.fitted_parameters["aromatic_C-C_C=C.area"] = 10.0
    result.configuration["peaks"][0]["area_bounds"] = bounds
    monkeypatch.setattr("xps_fitting.review.load_fit_bundle", lambda _: result)

    summary = candidate_review_summary("candidate.bundle")

    assert summary["components"][0]["bounds"]["area"] == expected_bounds
    area_hits = [item for item in summary["bound_hits"] if item["parameter"].endswith(".area")]
    assert [item["bound"] for item in area_hits] == ([] if expected_hit is None else [expected_hit])


def test_persisted_cl2p_candidate_summary_handles_unbounded_area_without_fitting(monkeypatch) -> None:
    def fail_if_fitted(*args, **kwargs):
        raise AssertionError("review must not invoke fitting")

    monkeypatch.setattr("xps_fitting.optimiser.fit_spectrum", fail_if_fitted)
    bundle = (
        Path(__file__).resolve().parents[1]
        / "artifacts"
        / "candidates"
        / "PDI-H-COOH"
        / "Cl2p"
        / "cl2p-constrained.bundle"
    )

    summary = candidate_review_summary(bundle)

    assert summary["model"] == "Cl2p_constrained"
    assert summary["components"][0]["bounds"]["area"] == [0.0, "unbounded"]
