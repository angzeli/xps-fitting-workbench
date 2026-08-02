"""Verify cleanup remains allowlisted and dry runs preserve every file."""

from xps_fitting.cleanup import clean_generated


def test_cleanup_is_allowlisted_and_dry_run_preserves_everything(tmp_path) -> None:
    disposable = tmp_path / "outputs" / "old.png"
    diagnostic = tmp_path / "figures" / "diagnostic" / "fit.pdf"
    reviewed = tmp_path / "artifacts" / "reviewed" / "sample" / "manifest.json"
    raw = tmp_path / "data" / "raw" / "sample" / "C1s Scan.VGD"
    for path in (disposable, diagnostic, reviewed, raw):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("data")

    planned = clean_generated(tmp_path, dry_run=True)
    assert set(planned) == {disposable, diagnostic}
    assert all(path.exists() for path in (disposable, diagnostic, reviewed, raw))

    removed = clean_generated(tmp_path, dry_run=False)
    assert set(removed) == {disposable, diagnostic}
    assert not disposable.exists() and not diagnostic.exists()
    assert reviewed.exists() and raw.exists()
