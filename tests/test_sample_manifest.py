import numpy as np
import pytest

from xps_fitting.artifacts import save_candidate_bundle
from xps_fitting.result import FitResult
from xps_fitting.review import review_candidate
from xps_fitting.sample_manifest import (
    activate_reviewed_bundle,
    create_sample_manifest,
    load_sample_manifest,
)


def _candidate_result() -> FitResult:
    energy = np.linspace(280.0, 292.0, 121)
    background = np.linspace(15.0, 25.0, energy.size)
    component = 100.0 * np.exp(-(((energy - 284.3762) / 0.8) ** 2))
    total = background + component
    residual = 0.1 * np.cos(energy)
    return FitResult(
        energy,
        total + residual,
        background,
        {"aromatic_cc": component},
        total,
        residual,
        {"aromatic_cc.centre": 284.3762},
        configuration={"name": "C1s_5", "region": "C 1s", "peaks": []},
        metadata={"data_origin": "experimental"},
    )


def _reviewed_bundle(tmp_path):
    source = tmp_path / "raw" / "PDI-H-COOH" / "C1s Scan.VGD"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"c1s raw")
    candidate = tmp_path / "artifacts" / "candidates" / "C1s.bundle"
    save_candidate_bundle(
        _candidate_result(),
        candidate,
        sample="PDI-H-COOH",
        region="C1s",
        source_path=source,
        repository_root=tmp_path,
    )
    promotion = review_candidate(
        candidate,
        tmp_path / "artifacts" / "reviewed",
        decision="accepted",
        reviewer="Reviewer",
        residual_inspection_status="approved",
        background_approval_status="approved",
        component_assignment_approval_status="approved",
        constraints_reviewed=True,
        warnings_acknowledged=True,
        repository_root=tmp_path,
    )
    assert promotion is not None
    return promotion.reviewed_bundle


def test_sample_manifest_hashes_raw_regions_and_reports_missing_regions(tmp_path) -> None:
    raw = tmp_path / "raw" / "PDI-H-COOH"
    raw.mkdir(parents=True)
    for name in ("C1s Scan.VGD", "N1s Scan.VGD", "XPS Survey.VGD"):
        (raw / name).write_bytes(name.encode())
    path = tmp_path / "artifacts" / "reviewed" / "PDI-H-COOH" / "sample_manifest.json"

    manifest = create_sample_manifest(
        "PDI-H-COOH",
        raw,
        path,
        repository_root=tmp_path,
        created_at="2026-07-21T00:00:00+00:00",
    )

    assert set(manifest.raw_regions) == {"C1s", "N1s", "Survey"}
    assert manifest.raw_regions["C1s"] == "raw/PDI-H-COOH/C1s Scan.VGD"
    assert manifest.missing_raw_regions == ("O1s", "Cl2p")
    assert all(len(digest) == 64 for digest in manifest.raw_sha256.values())
    assert manifest.reviewed_uncalibrated == {} and manifest.calibration is None
    assert load_sample_manifest(path).to_dict() == manifest.to_dict()
    with pytest.raises(FileExistsError, match="already exists"):
        create_sample_manifest("PDI-H-COOH", raw, path, repository_root=tmp_path)


def test_reviewed_activation_is_explicit_and_never_overwrites_silently(tmp_path) -> None:
    reviewed = _reviewed_bundle(tmp_path)
    raw = tmp_path / "raw" / "PDI-H-COOH"
    manifest_path = tmp_path / "artifacts" / "reviewed" / "PDI-H-COOH" / "sample_manifest.json"
    create_sample_manifest("PDI-H-COOH", raw, manifest_path, repository_root=tmp_path)

    manifest = activate_reviewed_bundle(manifest_path, reviewed, repository_root=tmp_path)
    assert manifest.reviewed_uncalibrated["C1s"].endswith("C1s.review-v1.bundle")
    assert manifest.active_review_versions == {"C1s": 1}
    with pytest.raises(FileExistsError, match="replace_active=True"):
        activate_reviewed_bundle(manifest_path, reviewed, repository_root=tmp_path)
