# Executable examples

All examples are deterministic and headless. Unless noted otherwise they use
synthetic spectra and write beneath the ignored `outputs/examples/` directory.
Override the destination with `--output-dir PATH`.

| Example | Workflows | Expected outputs |
|---|---|---|
| `load_spectrum.py` | DataFrame, CSV, XLSX, tracked experimental VGD | CSV and XLSX input tables |
| `fit_pdi_h_cooh_c1s.py` | Four- and five-component synthetic C 1s fits | Two diagnostic PNGs |
| `compare_pdi_h_cooh_models.py` | Annotated four-versus-five model comparison | PNG and PDF |
| `fit_cl2p_doublet.py` | Annotated constrained 2:1 synthetic Cl 2p doublet | PNG and PDF |
| `plot_single_fit.py` | Annotated 8 × 6 publication, residual diagnostic, monochrome SI | PNG and PDF |
| `plot_pdi_c1s_series.py` | Annotated three-sample synthetic multipanel | PNG and PDF |
| `plot_core_level_panel.py` | Annotated synthetic C 1s/N 1s/O 1s panel | PNG and PDF |
| `end_to_end_publication.py` | Fit, Phase 1 export, XLSX reload, curve-table plotting, CLI | Numerical bundle files, PNG and PDF |
| `plot_pdi_h_cooh_c1s_publication.py` | Active calibrated reviewed C 1s artifact and exact recipe | PNG, PDF, provenance JSON |

Run one example:

```bash
PYTHONPATH=src MPLBACKEND=Agg python examples/plot_single_fit.py
```

Run every synthetic example independently:

```bash
python scripts/run_all_examples.py
```

The runner skips the experimental publication example unless
`--pdi-h-c1s-sample-manifest PATH` is supplied. It never substitutes synthetic
data or invokes fitting for that figure. The experimental example itself fails
clearly when its reviewed calibrated source is missing or ineligible.

The runner and individual examples refuse to replace existing files by default.
Pass `--overwrite` only when intentionally regenerating an example's dedicated
ignored output directory.

The experimental publication example deliberately has no fitting fallback. Pass a
sample manifest with `--sample-manifest PATH`. It resolves only the active calibrated
reviewed bundle and fails clearly on missing review/calibration records, synthetic or
legacy provenance, identical raw/fitted curves, a trivial background, incomplete
arrays, or hash inconsistencies. It prints the bundle, calibration record, exact
offset, recipe, and output paths.

The declared `vgd-reader` dependency exercises the VGD path. Existing tracked
experimental files are read in place and never copied. Figures are saved only as
PNG or PDF.

The release's real-data check is intentionally separate from the deterministic
example suite. Run
`PYTHONPATH=src MPLBACKEND=Agg python scripts/validate_experimental_workflow.py` to
create ignored PNG/PDF publication, diagnostic, comparison, and raw-series figures
for the tracked PDI spectra. The experimental title is `PDI-H-COOH`; `Synthetic`
is retained only by deterministic validation examples. See
`docs/experimental_validation.md`; successful optimisation is not presented as
chemical validation.
