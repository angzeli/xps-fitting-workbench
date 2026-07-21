import copy
import json

import numpy as np
import pytest

from xps_fitting.artifacts import save_candidate_bundle, validate_fit_bundle
from xps_fitting.calibration_workflow import calibrate_reviewed_sample, prepare_sample_calibration
from xps_fitting.export import load_fit_bundle
from xps_fitting.integrity import result_arrays_equal, sha256_file
from xps_fitting.result import FitResult
from xps_fitting.review import review_candidate
from xps_fitting.sample_manifest import activate_reviewed_bundle, create_sample_manifest, load_sample_manifest
from xps_fitting.spectrum import Spectrum
from xps_fitting.spectrum_artifacts import load_spectrum_bundle, review_spectrum, validate_spectrum_bundle


def _result(region: str, component: str, centre: float) -> FitResult:
    energy = np.linspace(centre - 3.0, centre + 3.0, 61)
    background = np.linspace(10.0, 15.0, energy.size)
    peak = 80.0 * np.exp(-(((energy - centre) / 0.7) ** 2))
    total = background + peak
    residual = 0.1 * np.sin(energy)
    return FitResult(
        energy,
        total + residual,
        background,
        {component: peak},
        total,
        residual,
        {f"{component}.centre": centre, f"{component}.fwhm": 1.2, f"{component}.area": 100.0},
        configuration={
            "name": f"{region}_model",
            "region": region,
            "peaks": [{"label": component, "centre": centre, "centre_bounds": [centre - 0.5, centre + 0.5]}],
        },
        metadata={"data_origin": "experimental"},
    )


def _review_region(tmp_path, region: str, component: str, centre: float):
    source = tmp_path / "raw" / "PDI-H-COOH" / f"{region} Scan.VGD"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(f"raw {region}".encode())
    candidate = tmp_path / "artifacts" / "candidates" / region / "model.bundle"
    save_candidate_bundle(
        _result(region, component, centre),
        candidate,
        sample="PDI-H-COOH",
        region=region,
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


def _sample(tmp_path):
    c1s = _review_region(tmp_path, "C1s", "aromatic_cc", 284.3762)
    n1s = _review_region(tmp_path, "N1s", "nitrogen", 400.125)
    survey_source = tmp_path / "raw" / "PDI-H-COOH" / "XPS Survey.VGD"
    survey_source.write_bytes(b"raw Survey")
    survey = Spectrum(
        np.linspace(0.0, 1200.0, 121),
        np.linspace(50.0, 100.0, 121),
        region="Survey",
        sample_name="PDI-H-COOH",
        source_file=str(survey_source),
        metadata={"data_origin": "experimental"},
    )
    survey_promotion = review_spectrum(
        survey,
        tmp_path / "artifacts" / "reviewed",
        source_path=survey_source,
        reviewer="Reviewer",
        repository_root=tmp_path,
    )
    manifest_path = tmp_path / "artifacts" / "reviewed" / "PDI-H-COOH" / "sample_manifest.json"
    create_sample_manifest("PDI-H-COOH", tmp_path / "raw" / "PDI-H-COOH", manifest_path, repository_root=tmp_path)
    activate_reviewed_bundle(manifest_path, c1s, repository_root=tmp_path)
    activate_reviewed_bundle(manifest_path, n1s, repository_root=tmp_path)
    activate_reviewed_bundle(manifest_path, survey_promotion.reviewed_spectrum, repository_root=tmp_path)
    return manifest_path, {"C1s": c1s, "N1s": n1s, "Survey": survey_promotion.reviewed_spectrum}


def test_persisted_calibration_uses_exact_centre_and_preserves_every_intensity_array(tmp_path) -> None:
    manifest_path, source_bundles = _sample(tmp_path)
    source_hashes = {
        region: {member.name: sha256_file(member) for member in bundle.iterdir() if member.is_file()}
        for region, bundle in source_bundles.items()
    }
    originals = {
        region: copy.deepcopy(load_spectrum_bundle(bundle) if region == "Survey" else load_fit_bundle(bundle))
        for region, bundle in source_bundles.items()
    }
    plan = prepare_sample_calibration(
        manifest_path,
        reference_region="C1s",
        reference_component="aromatic_cc",
        reference_component_label="Aromatic C=C/C-C",
        required_regions=("C1s", "N1s", "Survey"),
        repository_root=tmp_path,
    )
    assert plan.reference_center_before_eV == 284.3762
    assert plan.energy_offset_eV == pytest.approx(0.4238)
    assert "Exact fitted reference centre: 284.376200 eV" in plan.format_text()

    with pytest.raises(PermissionError, match="confirmation"):
        calibrate_reviewed_sample(
            manifest_path,
            reference_region="C1s",
            reference_component="aromatic_cc",
            reference_component_label="Aromatic C=C/C-C",
            reviewer="Reviewer",
            scientific_rationale="Intrinsic aromatic carbon reference reviewed for this sample.",
            required_regions=("C1s", "N1s", "Survey"),
            repository_root=tmp_path,
        )
    assert not (manifest_path.parent / "calibration.json").exists()

    outcome = calibrate_reviewed_sample(
        manifest_path,
        reference_region="C1s",
        reference_component="aromatic_cc",
        reference_component_label="Aromatic C=C/C-C",
        reviewer="Reviewer",
        scientific_rationale="Intrinsic aromatic carbon reference reviewed for this sample.",
        required_regions=("C1s", "N1s", "Survey"),
        confirmed=True,
        repository_root=tmp_path,
        calibration_date="2026-07-21T05:00:00+00:00",
    )

    assert outcome.record.energy_offset_eV == pytest.approx(0.4238)
    assert outcome.record.applied_regions == ("C1s", "N1s", "Survey")
    for region, bundle in outcome.calibrated_bundles.items():
        if region == "Survey":
            calibrated_survey = load_spectrum_bundle(bundle)
            np.testing.assert_allclose(
                calibrated_survey.binding_energy,
                originals[region].binding_energy + 0.4238,
                rtol=0,
                atol=1e-12,
            )
            np.testing.assert_array_equal(calibrated_survey.intensity, originals[region].intensity)
            report = validate_spectrum_bundle(bundle, require_calibrated=True, repository_root=tmp_path)
            assert report.publication_eligible and not report.errors
            continue
        calibrated = load_fit_bundle(bundle)
        assert result_arrays_equal(originals[region], calibrated, energy_offset=0.4238)
        for name, value in originals[region].fitted_parameters.items():
            expected = value + 0.4238 if name.endswith(".centre") else value
            assert calibrated.fitted_parameters[name] == pytest.approx(expected)
        report = validate_fit_bundle(bundle, require_calibrated=True, repository_root=tmp_path)
        assert report.publication_eligible and not report.errors
    assert source_hashes == {
        region: {member.name: sha256_file(member) for member in bundle.iterdir() if member.is_file()}
        for region, bundle in source_bundles.items()
    }
    stored_manifest = load_sample_manifest(manifest_path)
    assert stored_manifest.calibration_status == "calibrated"
    assert stored_manifest.energy_offset_eV == pytest.approx(0.4238)
    assert set(stored_manifest.calibrated) == {"C1s", "N1s", "Survey"}
    record = json.loads(outcome.calibration_record.read_text())
    assert record["reference_center_before_eV"] == 284.3762


def test_incomplete_sample_requires_an_explicit_override_and_calibration_is_immutable(tmp_path) -> None:
    manifest_path, _ = _sample(tmp_path)
    with pytest.raises(ValueError, match="missing reviewed regions"):
        prepare_sample_calibration(
            manifest_path,
            reference_region="C1s",
            reference_component="aromatic_cc",
            reference_component_label="Aromatic C=C/C-C",
            repository_root=tmp_path,
        )
    outcome = calibrate_reviewed_sample(
        manifest_path,
        reference_region="C1s",
        reference_component="aromatic_cc",
        reference_component_label="Aromatic C=C/C-C",
        reviewer="Reviewer",
        scientific_rationale="Only the explicitly available regions are in scope.",
        allow_incomplete=True,
        confirmed=True,
        repository_root=tmp_path,
    )
    assert set(outcome.record.missing_regions) == {"O1s", "Cl2p"}
    with pytest.raises(FileExistsError, match="already exists"):
        calibrate_reviewed_sample(
            manifest_path,
            reference_region="C1s",
            reference_component="aromatic_cc",
            reference_component_label="Aromatic C=C/C-C",
            reviewer="Reviewer",
            scientific_rationale="Repeat attempt.",
            allow_incomplete=True,
            confirmed=True,
            repository_root=tmp_path,
        )
