# XPS workflow quick start

This guide assumes you have never used Python, Git, or a command-line program.
The workflow never changes the original VGD files.

## 1. Install the tools on macOS

Open **Terminal**: press Command-Space, type `Terminal`, then press Return.
Install `uv` once by following <https://docs.astral.sh/uv/getting-started/installation/>.
In Terminal, move into this repository (keep the quotation marks because the
folder name contains a space):

```bash
cd "/Users/liangze/Desktop/squiddy tools/xps-fitting-workbench"
uv sync --python 3.13
uv run xps-fit doctor
```

You may instead double-click `Start_XPS_Workflow.command`. It checks `uv`, moves
to the correct folder, installs the environment, and starts the guided wizard.

## 2. Put raw files in the right folder

Use one folder per sample under `data/raw/`:

```text
data/raw/PDI-H-COOH/
  C1s Scan.VGD
  N1s Scan.VGD
  O1s Scan.VGD
  Cl2p Scan.VGD
  XPS Survey.VGD
```

Do not edit, rename during analysis, calibrate, or overwrite these files. The
software hashes each file so a later change is detectable.

## 3. Inspect the sample

```bash
uv run xps-fit inspect-sample --sample PDI-H-COOH
```

The report lists regions, point counts, energy ranges, acquisition metadata,
SHA-256 hashes, missing regions, and existing candidate/reviewed/calibrated files.

## 4. Fit the N 1s candidates

```bash
uv run xps-fit fit-region \
  --sample PDI-H-COOH \
  --region N1s
```

Each candidate is saved under `artifacts/candidates/` **before** diagnostic
figures are created under `figures/diagnostic/`. Fitting does not approve a
model and does not calibrate the data. For this sample, the N 1s candidates use
one expected imide-N environment and compare linear and Shirley backgrounds.

If you intentionally need to replace existing unreviewed candidates and figures,
use `--overwrite-candidates --overwrite-figures`. Do not type `overwrite=True`;
that is Python syntax, not a command-line option.

## 5. Fit the O 1s candidates

```bash
uv run xps-fit fit-region \
  --sample PDI-H-COOH \
  --region O1s
```

The two- and three-component O 1s candidates test different assumptions about
whether the carbonyl environments are resolved. Their structural area ratios are
sensitivity checks, not automatic chemical truth. No adsorbate peak is added by
default.

## 6. Review N 1s and O 1s

```bash
uv run xps-fit review-region \
  --sample PDI-H-COOH \
  --region N1s

uv run xps-fit review-region \
  --sample PDI-H-COOH \
  --region O1s
```

Read the listed centres, widths, areas, area fractions, residual statistics,
AICc/BIC, bound hits, warnings, convergence information, correlations, and
diagnostic paths. Open the diagnostic PNG or PDF. The menu lets you approve one
candidate, reject all candidates, or cancel without changes. Approval creates a
new version under `artifacts/reviewed/PDI-H-COOH/uncalibrated/`; it never changes
the candidate. A lower AICc or BIC does not by itself prove a chemical assignment.

## 7. Review Cl 2p and Survey

```bash
uv run xps-fit review-region \
  --sample PDI-H-COOH \
  --region Cl2p
```

For Cl 2p, check the constrained 2p3/2–2p1/2 doublet, separation, approximately
2:1 area ratio, shared FWHM, and shared line shape.

Survey has no peak model, so review it as a raw spectrum rather than inventing a
fake fit:

```bash
uv run xps-fit review-spectrum --sample PDI-H-COOH --region Survey
```

## 8. Check whether calibration is ready

```bash
uv run xps-fit validate-sample \
  --sample PDI-H-COOH
```

The report lists C1s, N1s, O1s, Cl2p, and Survey as `reviewed` or `missing` and
prints the exact review command for anything missing. Calibration readiness must
say `ready`. Do not use incomplete calibration for the final sample.

## 9. Calibrate the complete sample

Calibration uses the exact stored C 1s fitted centre, not a rounded plot label:

```text
energy shift = 284.8 eV - exact fitted reference centre
```

Run the command with the component key printed during review:

```bash
uv run xps-fit calibrate-sample \
  --sample PDI-H-COOH \
  --reference-region C1s \
  --reference-component aromatic_C-C_C=C \
  --target-energy 284.8
```

The command prints the exact centre, common shift, affected regions, missing
regions, and the arrays that will not change. The default answer is No. If you
continue, the identical shift moves C 1s, N 1s, O 1s, Cl 2p, Survey, and any
other reviewed region for this sample in the same direction by the same amount.
Intensities, background, components, residuals, widths, and areas do not change.
The reviewed uncalibrated artifacts remain intact. Each compound needs its own
calibration record.

## 10. Generate all final figures

```bash
uv run xps-fit plot-sample \
  --sample PDI-H-COOH \
  --recipe configs/plots/pdi_publication.json
```

This creates individual Survey, C 1s, N 1s, O 1s, and Cl 2p figures plus the
five-panel manuscript figure. Final PNG, PDF, and provenance JSON files go to
`figures/final/PDI-H-COOH/`. Plotting reads only a reviewed calibrated bundle;
it does not refit or reconstruct missing arrays. It refuses candidate,
uncalibrated, synthetic, incomplete, or mixed-calibration inputs.

To regenerate only N 1s, use:

```bash
uv run xps-fit plot-region \
  --sample PDI-H-COOH \
  --region N1s \
  --recipe configs/plots/n1s_publication.json
```

Equivalent recipes are available for C 1s, O 1s, Cl 2p, and Survey.

## 11. Validate and back up

```bash
uv run xps-fit validate-sample --sample PDI-H-COOH
uv run xps-fit validate-calibration --sample PDI-H-COOH
```

Back up all of `data/raw/` and `artifacts/reviewed/`. Also keep `configs/`.
Figures can be regenerated. Candidate artifacts are useful audit evidence but
can be regenerated. `outputs/` and `figures/diagnostic/` are disposable after
reviewed artifacts are safely backed up.

Preview cleanup without deleting anything:

```bash
uv run xps-fit clean-generated --dry-run
```

See [troubleshooting](docs/troubleshooting.md) for common errors.

If `xps-fit doctor` reports an unhealthy editable installation, run:

```bash
uv sync --python 3.13 --reinstall-package xps-fitting-workbench
uv run xps-fit doctor
```
