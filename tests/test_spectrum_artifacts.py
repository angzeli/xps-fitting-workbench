from dataclasses import replace
from pathlib import Path
from shutil import copyfile

import numpy as np
import pytest

from xps_fitting.cli import main
from xps_fitting.io_vgd import read_vgd
from xps_fitting.sample_manifest import activate_reviewed_bundle, create_sample_manifest, load_sample_manifest
from xps_fitting.spectrum import Spectrum
from xps_fitting.spectrum_artifacts import (
    _canonical_region_name,
    load_spectrum_bundle,
    review_spectrum,
    validate_spectrum_bundle,
)


@pytest.mark.parametrize(
    ("alias", "canonical"),
    [
        ("Survey Scan", "Survey"),
        ("survey", "Survey"),
        ("XPS Survey", "Survey"),
        ("XPSSurvey", "Survey"),
        ("Wide Scan", "Survey"),
        ("C 1s", "C1s"),
        ("N 1s", "N1s"),
        ("O 1s", "O1s"),
        ("Cl 2p", "Cl2p"),
    ],
)
def test_spectrum_region_aliases_are_canonicalised(alias, canonical) -> None:
    assert _canonical_region_name(alias) == canonical


def test_different_spectrum_regions_remain_distinct() -> None:
    assert _canonical_region_name("O1s") != _canonical_region_name("Survey")


def test_reviewed_survey_is_a_spectrum_artifact_not_a_fake_fitresult(tmp_path) -> None:
    source = tmp_path / "raw" / "PDI-H-COOH" / "XPS Survey.VGD"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"survey raw")
    spectrum = Spectrum(
        np.linspace(0.0, 1200.0, 121),
        np.linspace(100.0, 200.0, 121),
        region="Survey",
        sample_name="PDI-H-COOH",
        source_file=str(source),
        metadata={"data_origin": "experimental"},
    )

    promotion = review_spectrum(
        spectrum,
        tmp_path / "artifacts" / "reviewed",
        source_path=source,
        reviewer="Reviewer",
        notes=("Acquisition and energy range inspected",),
        repository_root=tmp_path,
    )

    assert promotion.reviewed_spectrum.name == "Survey.review-v1.spectrum"
    reloaded = load_spectrum_bundle(promotion.reviewed_spectrum)
    np.testing.assert_array_equal(reloaded.binding_energy, spectrum.binding_energy)
    np.testing.assert_array_equal(reloaded.intensity, spectrum.intensity)
    report = validate_spectrum_bundle(promotion.reviewed_spectrum, repository_root=tmp_path)
    assert report.publication_eligible and not report.errors

    manifest_path = tmp_path / "artifacts" / "reviewed" / "PDI-H-COOH" / "sample_manifest.json"
    create_sample_manifest("PDI-H-COOH", source.parent, manifest_path, repository_root=tmp_path)
    manifest = activate_reviewed_bundle(
        manifest_path,
        promotion.reviewed_spectrum,
        repository_root=tmp_path,
    )
    assert manifest.reviewed_uncalibrated["Survey"].endswith("Survey.review-v1.spectrum")


def test_existing_survey_cli_review_preserves_arrays_without_fitting(tmp_path, monkeypatch) -> None:
    def fail_if_fitted(*args, **kwargs):
        raise AssertionError("spectrum review must not invoke fitting")

    monkeypatch.setattr("xps_fitting.optimiser.fit_spectrum", fail_if_fitted)
    repository = Path(__file__).resolve().parents[1]
    source = repository / "data" / "raw" / "PDI-H-COOH" / "XPS Survey.VGD"
    spectrum = read_vgd(source)
    original_energy = spectrum.binding_energy.copy()
    original_intensity = spectrum.intensity.copy()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\nversion='0'\n")
    copied_source = tmp_path / "data" / "raw" / "PDI-H-COOH" / "XPS Survey.VGD"
    copied_source.parent.mkdir(parents=True)
    copyfile(source, copied_source)

    status = main(
        [
            "--repository",
            str(tmp_path),
            "review-spectrum",
            "--sample",
            "PDI-H-COOH",
            "--region",
            "Survey",
            "--approve",
            "--reviewer",
            "Reviewer",
        ]
    )

    assert status == 0
    bundle = tmp_path / "artifacts" / "reviewed" / "PDI-H-COOH" / "uncalibrated" / "Survey.review-v1.spectrum"
    reloaded = load_spectrum_bundle(bundle)
    assert reloaded.region == "XPS Survey"
    assert reloaded.sample_name == "PDI-H-COOH"
    assert reloaded.metadata["source_sample_name"] == "3.10-3"
    np.testing.assert_array_equal(reloaded.binding_energy, original_energy)
    np.testing.assert_array_equal(reloaded.intensity, original_intensity)
    report = validate_spectrum_bundle(bundle, repository_root=tmp_path)
    assert not report.errors
    manifest = load_sample_manifest(tmp_path / "artifacts" / "reviewed" / "PDI-H-COOH" / "sample_manifest.json")
    assert manifest.reviewed_uncalibrated["Survey"].endswith("Survey.review-v1.spectrum")

    monkeypatch.setattr(
        "xps_fitting.spectrum_artifacts.load_spectrum_bundle",
        lambda _: replace(reloaded, sample_name="PDI-Me-COOH"),
    )
    mismatched = validate_spectrum_bundle(bundle, repository_root=tmp_path)
    assert "spectrum sample or region differs from the artifact descriptor" in mismatched.errors
