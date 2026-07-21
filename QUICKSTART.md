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

## 4. Fit candidate models

```bash
uv run xps-fit fit-region --sample PDI-H-COOH --region C1s
```

Each candidate is saved under `artifacts/candidates/` **before** diagnostic
figures are created under `figures/diagnostic/`. Fitting does not approve a
model and does not calibrate the data.

## 5. Review and approve one candidate

```bash
uv run xps-fit review-region --sample PDI-H-COOH --region C1s
```

Read the listed centres, widths, areas, area fractions, residual statistics,
warnings, convergence information, and correlations. Open the diagnostic PNG or
PDF. Choose Cancel if the background, residual, assignments, or constraints are
not scientifically acceptable. Approval creates a new version under
`artifacts/reviewed/PDI-H-COOH/uncalibrated/`; it never changes the candidate.

Survey has no peak model, so review it as a raw spectrum rather than inventing a
fake fit:

```bash
uv run xps-fit review-spectrum --sample PDI-H-COOH --region Survey
```

## 6. Calibrate the whole sample

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
  --reference-component-label "Aromatic C=C/C-C" \
  --target-energy 284.8
```

The command prints the exact centre, common shift, affected regions, missing
regions, and the arrays that will not change. The default answer is No. If you
continue, the identical shift moves C 1s, N 1s, O 1s, Cl 2p, Survey, and any
other reviewed region for this sample. Intensities, background, components,
residuals, widths, and areas do not change. Each compound needs its own record.

## 7. Generate a final figure

```bash
uv run xps-fit plot-region \
  --sample PDI-H-COOH \
  --region C1s \
  --recipe configs/plots/c1s_publication.json
```

Final PNG, PDF, and provenance JSON files go to
`figures/final/PDI-H-COOH/`. Plotting reads only a reviewed calibrated bundle;
it does not refit or reconstruct missing arrays.

## 8. Validate and back up

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
