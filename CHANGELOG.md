# Changelog

## Unreleased

## [0.3.0] - 2026-07-21

- Added durable experimental candidate bundles with source/configuration hashes,
  strict validation, and mandatory persistence before diagnostic plotting.
- Added explicit immutable review versions and review records; structurally invalid,
  synthetic, fixture-like, and raw-equals-fit bundles cannot be promoted.
- Added sample manifests and persisted sample-wide calibration from the exact stored
  C 1s centre, including reviewed raw Survey spectra and intensity-invariance checks.
- Added plotting-only final PNG/PDF export from calibrated reviewed artifacts plus a
  provenance JSON sidecar.
- Added inspect, fit, review, calibrate, plot, validate, cleanup, and guided-wizard
  CLI commands with conservative confirmation defaults.
- Reorganised tracked acquisitions under `data/raw/`, fit hypotheses under
  `configs/fits/`, and generated three raw-only sample manifests without changing
  any VGD file bytes.
- Added the beginner quick start, launcher, scientific workflow, review, calibration,
  artifact/backup, schema, and troubleshooting documentation.

- Refined detailed single-spectrum publication figures to 8 × 6 in with a complete
  1.8 pt box, bold ticks, restrained markers/fills, a thinner total fit, additional
  headroom, and compact framed legends without a background entry.
- Standardised sentence-case chemical labels, including Aromatic C=C/C–C, and
  layout-aware upper-left sample and upper-right core-level titles.
- Added optional fitted binding-energy annotations with assignment colours,
  one-decimal `eV` formatting, leaders, collision staggering, negligible/hidden
  component controls, manual offsets, multipanel support, and recipe serialization.
- Polished the publication, diagnostic, model-comparison, monochrome, PDI-series,
  core-level-panel, and Cl 2p examples while retaining PNG/PDF-only export.
- Added recipe-controlled y/top tick visibility, one-minor-tick spacing, optional
  sample titles, axes-relative core labels, and 600 dpi output for the final C 1s plot.
- Refined binding-energy annotation clearance against visible curves, other labels,
  legends, and figure bounds while preserving fitted centres and component arrays.
- Added a plotting-only PDI-H-COOH C 1s example that requires a reviewed Phase 1
  export and writes only the named PNG and vector PDF.
- Removed the synthetic publication smoke-test bundle and added strict experimental
  provenance, stored raw/background, numerical-audit, and plot-immutability checks.
- Preserved source-file, sample, and region metadata in new `FitResult` exports and
  marked VGD acquisitions explicitly as experimental provenance.
- Added non-mutating sample-wide binding-energy calibration for fitted results and
  raw spectra, with one shared C 1s-derived offset, provenance, and double-shift guards.

## [0.2.0] - 2026-07-21

- Completed all eight deterministic, headless examples and added an isolated
  all-examples runner.
- Standardised figure output on PNG/PDF, centralised the 1.8 pt publication spine
  contract, expanded semantic colours, and added publication size presets.
- Added readable fit-bundle save/load APIs with numerically consistent reload.
- Extended `xps-fit plot` to ordered multi-input bundle/curve sources with panel
  labels, safe names, dry runs, collision checks, and concise ordinary errors.
- Made the package version authoritative and recorded 0.2.0 in fitted-result
  provenance.
- Added Ruff, selected mypy checks, local pre-commit hooks, and Python 3.10–3.13 CI
  with tests, examples, build, and clean-wheel import.
- Exercised all tracked VGD spectra, real PDI-H-COOH C 1s candidate fits and Cl 2p
  constraints, and raw PDI series/N 1s/O 1s plots with explicit scientific caveats.

## Earlier Phase 1 foundation

- Added validated CSV, XLSX, DataFrame, and optional VGD spectrum input.
- Added area-normalised line shapes, backgrounds, chemistry constraints, staged
  deterministic fitting, diagnostics, model comparison, and diagnostic plotting.
- Added PDI-H-COOH C 1s and Cl 2p examples, export bundles, a stable `FitResult`
  contract, and limited two-pass shared-shape fitting groundwork.

## Earlier Phase 2 plotting foundation

- Added scoped publication, diagnostic, monochrome, and presentation themes.
- Added stable core-level and component palettes with alias handling and contrast checks.
- Added single-spectrum, residual, multipanel, series, and candidate-model figures.
- Added figure export plus validated JSON plotting recipes; version 0.2.0
  standardises saved figures on PNG and PDF.
- Added plotting-only CSV/XLSX/full-JSON reconstruction and the `xps-fit plot` CLI.
- Added end-to-end numerical-integrity coverage and plotting documentation.
