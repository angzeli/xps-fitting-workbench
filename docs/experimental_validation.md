# Experimental workflow validation

This release-readiness check exercised the experimental files already tracked in
the repository on 2026-07-21 with `xps-fitting-workbench` 0.2.0. It is a software
workflow check, not a peer-reviewed XPS interpretation. Generated figures remain
under the ignored `outputs/experimental_validation/` directory.

Run the reproducible check from the repository root after installing the optional
`vgd-reader` package:

```bash
PYTHONPATH=src MPLBACKEND=Agg python scripts/validate_experimental_workflow.py
```

Pass `--overwrite` only to intentionally replace an earlier local validation set.

## Tracked-data inventory

All paths below are repository-relative. The VGD adapter parsed every tracked VGD
file. Narrow scans expose all 11 metadata fields collected by the adapter. Survey
scans expose 8/11; pass energy, dwell time, and periods are absent. The embedded
sample identifier is `3.10-3` in all three directories, so the directory label is
needed to distinguish samples and should be checked against the laboratory record.

| Sample | Core level | Format and bytes | Points | Parse | Fit configuration | Demonstration suitability |
|---|---|---:|---:|---|---|---|
| PDI-H-COOH | C 1s | VGD, 11,776 | 231 | Yes; metadata 11/11 | Four- and five-component JSON | Candidate-model diagnostic, with manual review |
| PDI-H-COOH | Cl 2p | VGD, 12,288 | 261 | Yes; metadata 11/11 | Constrained doublet in validation script | Constrained-fit diagnostic, with manual review |
| PDI-H-COOH | N 1s | VGD, 11,264 | 181 | Yes; metadata 11/11 | None | Ingestion and raw plotting only |
| PDI-H-COOH | O 1s | VGD, 11,776 | 201 | Yes; metadata 11/11 | None | Ingestion and raw plotting only |
| PDI-H-COOH | Survey | VGD, 20,992 | 1,361 | Yes; metadata 8/11 | None | Parser check only |
| PDI-Me-COOH | C 1s | VGD, 11,776 | 231 | Yes; metadata 11/11 | None specific to sample | Ingestion and raw comparison plot |
| PDI-Me-COOH | Cl 2p | VGD, 12,288 | 261 | Yes; metadata 11/11 | None | Parser check only |
| PDI-Me-COOH | N 1s | VGD, 11,264 | 181 | Yes; metadata 11/11 | None | Parser check only |
| PDI-Me-COOH | O 1s | VGD, 11,776 | 201 | Yes; metadata 11/11 | None | Parser check only |
| PDI-Me-COOH | Survey | VGD, 20,992 | 1,361 | Yes; metadata 8/11 | None | Parser check only |
| PDI-OMe-COOH | C 1s | VGD, 11,776 | 231 | Yes; metadata 11/11 | None specific to sample | Ingestion and raw comparison plot |
| PDI-OMe-COOH | Cl 2p | VGD, 12,288 | 261 | Yes; metadata 11/11 | None | Parser check only |
| PDI-OMe-COOH | N 1s | VGD, 11,264 | 181 | Yes; metadata 11/11 | None | Parser check only |
| PDI-OMe-COOH | O 1s | VGD, 11,776 | 201 | Yes; metadata 11/11 | None | Parser check only |
| PDI-OMe-COOH | Survey | VGD, 20,992 | 1,361 | Yes; metadata 8/11 | None | Parser check only |

Each sample directory also contains five XML companion files (6,667–8,026 bytes).
They are not direct spectrum inputs in the package and were inventoried but not
interpreted. The three legacy workbooks are PDI-H-COOH `2.xls` (214,016 bytes),
PDI-Me-COOH `1.xls` (215,552 bytes), and PDI-OMe-COOH `3.xls` (214,016 bytes).
Pandas reported that the optional `xlrd` engine was unavailable. The supported
tabular workflow is CSV or XLSX through the declared dependencies; these old XLS
files therefore remain an explicitly unsupported ingestion case.

## Numerical observations

The PDI-H-COOH C 1s scan was fitted with
`configs/pdi_h_cooh_c1s_4.json` and `configs/pdi_h_cooh_c1s_5.json`.
Both seeded two-start fits converged to essentially identical RSS values between
starts. The five-component candidate lowered RSS by about 12.9% and had lower
AICc/BIC, but the residual remained strongly structured.

| Candidate | RSS | AICc | BIC | Durbin–Watson | Runs | Warnings |
|---|---:|---:|---:|---:|---:|---:|
| Four components | 1.6899e9 | 3676.51 | 3716.39 | 0.103 | 25 | 4 |
| Five components | 1.4717e9 | 3649.09 | 3695.34 | 0.112 | 53 | 4 |

Both candidates reported correlation above 0.95, the C–N/C–Cl centre at a bound,
and the carboxylic centre and/or width at bounds. The low Durbin–Watson values and
visible residual shape show that neither candidate is an adequate chemically
validated description merely because the optimiser converged. The added satellite
is a hypothesis, not an assignment proven by the information criteria.

The PDI-H-COOH Cl 2p check used a 1.6 eV separation, exact 2:1 area ratio, shared
FWHM/fraction, and a linear background. It converged reproducibly at 199.992 and
201.592 eV, FWHM 0.966 eV, with RSS 1.0557e8 and Durbin–Watson 0.092. No automated
warning fired, but the visibly structured residual and low Durbin–Watson statistic
still require manual review of background, line shape, calibration, and possible
additional chemistry.

PDI-Me-COOH and PDI-OMe-COOH C 1s spectra were parsed and plotted beside
PDI-H-COOH without normalisation or fitted assignments. The PDI-H-COOH N 1s and
O 1s spectra were likewise parsed and plotted as raw points. This confirms the
reader and publication theme on real arrays while avoiding unsupported peak claims.

## Real versus synthetic behaviour

Synthetic examples recover the deliberately generated components and generally
have cleaner residuals. The experimental scans have much larger count scales,
baseline structure, correlated residuals, bound-sensitive components, and metadata
identity ambiguity. Deterministic multistart stability therefore demonstrates only
numerical repeatability for a configured model—not model adequacy or chemical truth.

## Manual review and next scientific work

Before reporting assignments, an analyst should verify energy calibration and
sample identity, select physically defensible crop/background conventions, inspect
residuals and parameter correlations, justify every component against chemical
evidence, and assess uncertainty/replicates. Recommended next development is a
reviewed configuration set for all three PDI samples, weighted residual statistics,
simultaneous global fitting with explicit charging shifts, and validated Tougaard
or asymmetric line shapes. Optional legacy XLS support and stronger residual-
autocorrelation warnings are useful engineering follow-ups.
