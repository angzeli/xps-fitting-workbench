import numpy as np

from xps_fitting.artifacts import save_candidate_bundle
from xps_fitting.cli import main
from xps_fitting.result import FitResult


def _repository(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\nversion='0'\n")
    return tmp_path


def _candidate(root):
    energy = np.linspace(280.0, 290.0, 51)
    background = np.linspace(10.0, 20.0, energy.size)
    component = 50.0 * np.exp(-((energy - 284.4) ** 2))
    total = background + component
    residual = 0.1 * np.sin(energy)
    result = FitResult(
        energy,
        total + residual,
        background,
        {"aromatic_cc": component},
        total,
        residual,
        {"aromatic_cc.centre": 284.4},
        configuration={"name": "candidate", "region": "C 1s", "peaks": []},
        metadata={"data_origin": "experimental"},
    )
    source = root / "data" / "raw" / "PDI-H-COOH" / "C1s Scan.VGD"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"raw")
    bundle = root / "artifacts" / "candidates" / "PDI-H-COOH" / "C1s" / "candidate.bundle"
    save_candidate_bundle(
        result,
        bundle,
        sample="PDI-H-COOH",
        region="C1s",
        source_path=source,
        repository_root=root,
    )
    return bundle


def test_validate_bundle_reports_candidate_as_not_publication_eligible(tmp_path, capsys) -> None:
    root = _repository(tmp_path)
    bundle = _candidate(root)
    status = main(["--repository", str(root), "validate-bundle", str(bundle)])
    assert status == 1
    assert "Publication eligible: no" in capsys.readouterr().out


def test_review_region_cancellation_creates_no_reviewed_artifact(tmp_path, monkeypatch, capsys) -> None:
    root = _repository(tmp_path)
    _candidate(root)
    monkeypatch.setattr("builtins.input", lambda _: "2")
    status = main(
        [
            "--repository",
            str(root),
            "review-region",
            "--sample",
            "PDI-H-COOH",
            "--region",
            "C1s",
        ]
    )
    assert status == 0
    assert "Review cancelled" in capsys.readouterr().out
    assert not (root / "artifacts" / "reviewed").exists()


def test_clean_generated_dry_run_lists_but_preserves_files(tmp_path, capsys) -> None:
    root = _repository(tmp_path)
    generated = root / "outputs" / "old.png"
    generated.parent.mkdir()
    generated.write_text("figure")
    status = main(["--repository", str(root), "clean-generated", "--dry-run"])
    assert status == 0 and generated.exists()
    assert f"Would remove: {generated}" in capsys.readouterr().out
