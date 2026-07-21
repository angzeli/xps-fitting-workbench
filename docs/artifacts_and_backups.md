# Scientific artifacts and backups

The important directories are:

- `data/raw/`: immutable acquired files;
- `artifacts/candidates/`: persisted unreviewed fits and provenance;
- `artifacts/reviewed/`: review records, uncalibrated versions, calibrated copies,
  sample manifests, and calibration records;
- `configs/`: fit hypotheses and plot recipes;
- `figures/`: disposable renderings.

A fit bundle is a readable directory containing `manifest.json`, `curves.csv`,
and `metadata.json`. The manifest links the source/configuration hashes and
lifecycle state. A reviewed raw Survey uses a `.spectrum` directory with
`manifest.json`, `spectrum.csv`, and `metadata.json`.

Back up `data/raw/`, `artifacts/reviewed/`, and `configs/` together. Restore them
to the same repository-relative paths, then run `xps-fit validate-sample` and
`xps-fit validate-calibration`. A PNG or PDF cannot restore the scientific arrays
and is not a substitute for a bundle.

`xps-fit clean-generated --dry-run` lists disposable files. The cleanup allowlist
contains only `outputs/` and `figures/diagnostic/`; it refuses symlinks and never
touches `data/raw/` or `artifacts/reviewed/`.
