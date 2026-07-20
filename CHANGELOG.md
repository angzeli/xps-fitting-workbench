# Changelog

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

## Unreleased — Phase 1

- Added validated CSV, XLSX, DataFrame, and optional VGD spectrum input.
- Added area-normalised line shapes, backgrounds, chemistry constraints, staged
  deterministic fitting, diagnostics, model comparison, and diagnostic plotting.
- Added PDI-H-COOH C 1s and Cl 2p examples, export bundles, a stable `FitResult`
  contract, and limited two-pass shared-shape fitting groundwork.

## Unreleased — Phase 2

- Added scoped publication, diagnostic, monochrome, and presentation themes.
- Added stable core-level and component palettes with alias handling and contrast checks.
- Added single-spectrum, residual, multipanel, series, and candidate-model figures.
- Added figure export plus validated JSON plotting recipes; Phase 3 standardises saved figures on PNG and PDF.
- Added plotting-only CSV/XLSX/full-JSON reconstruction and the `xps-fit plot` CLI.
- Added end-to-end numerical-integrity coverage and plotting documentation.
