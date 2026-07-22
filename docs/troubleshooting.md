# Troubleshooting

## Raw VGD file or region is missing

Place the file under `data/raw/SAMPLE/` using names such as `C1s Scan.VGD` or
`XPS Survey.VGD`, then run `xps-fit inspect-sample`. Calibration stops when a
required reviewed region is missing. For the final sample, review all five
regions; do not use incomplete calibration.

## Synthetic provenance, raw equals total fit, or missing background

The bundle is not publication eligible. Do not edit its manifest to bypass the
gate. Refit the experimental VGD and persist the real candidate arrays. A
synthetic fixture, reconstructed raw trace, constant/zero background, or missing
component curve cannot be approved.

## Bundle is incomplete or a hash differs

Restore the whole bundle from backup. Do not reconstruct `curves.csv` from a
figure. A source-hash mismatch means the recorded raw file is not byte-identical
to the file used during fitting.

## Calibration already exists

The workflow never overwrites calibration. If the reference decision changes,
create new reviewed versions and preserve the old sample directory before starting
a separately versioned calibration workflow.

## Reference component not found

Use the exact component key printed by `review-region`, not its display label.
The full parameter name ends in `.centre` inside the bundle.

## Permission or environment errors

Run `uv run xps-fit doctor`. If `uv run` reports `No module named 'xps_fitting'`,
repair the editable installation with:

```bash
uv sync --python 3.13 --reinstall-package xps-fitting-workbench
uv run xps-fit doctor
```

The normal workflow is editable; `--no-editable` is not required. On macOS, make
the launcher executable with `chmod +x Start_XPS_Workflow.command`. Ensure the
repository and artifact directories are writable and that raw files are readable.

## Candidate or figure output already exists

Existing scientific candidates are protected from silent replacement. If you
really intend to recreate an unreviewed fit, use:

```bash
uv run xps-fit fit-region --sample SAMPLE --region REGION \
  --overwrite-candidates --overwrite-figures
```

Do not append `overwrite=True`; that is Python syntax, not a CLI argument.

## Old output clutter

Run `xps-fit clean-generated --dry-run` first. If the list contains only disposable
outputs, rerun without `--dry-run`. Reviewed artifacts and raw data are protected.
