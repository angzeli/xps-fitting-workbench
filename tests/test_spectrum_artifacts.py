import numpy as np

from xps_fitting.sample_manifest import activate_reviewed_bundle, create_sample_manifest
from xps_fitting.spectrum import Spectrum
from xps_fitting.spectrum_artifacts import load_spectrum_bundle, review_spectrum, validate_spectrum_bundle


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
