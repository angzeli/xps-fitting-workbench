# Executable examples

All examples are deterministic and headless. Unless noted otherwise they use
synthetic spectra and write beneath the ignored `outputs/examples/` directory.
Override the destination with `--output-dir PATH`.

| Example | Workflows | Expected outputs |
|---|---|---|
| `load_spectrum.py` | DataFrame, CSV, XLSX, optional tracked experimental VGD | CSV and XLSX input tables |
| `fit_pdi_h_cooh_c1s.py` | Four- and five-component synthetic C 1s fits | Two diagnostic PNGs |
| `compare_pdi_h_cooh_models.py` | Annotated four-versus-five model comparison | PNG and PDF |
| `fit_cl2p_doublet.py` | Annotated constrained 2:1 synthetic Cl 2p doublet | PNG and PDF |
| `plot_single_fit.py` | Annotated 8 × 6 publication, residual diagnostic, monochrome SI | PNG and PDF |
| `plot_pdi_c1s_series.py` | Annotated three-sample synthetic multipanel | PNG and PDF |
| `plot_core_level_panel.py` | Annotated synthetic C 1s/N 1s/O 1s panel | PNG and PDF |
| `end_to_end_publication.py` | Fit, Phase 1 export, XLSX reload, curve-table plotting, CLI | Numerical bundle files, PNG and PDF |
| `plot_pdi_h_cooh_c1s_publication.py` | Reviewed experimental FitResult reload and exact C 1s recipe | PNG and PDF |

Run one example:

```bash
PYTHONPATH=src MPLBACKEND=Agg python examples/plot_single_fit.py
```

Run every retained example independently:

```bash
python scripts/run_all_examples.py
```

The runner and individual examples refuse to replace existing files by default.
Pass `--overwrite` only when intentionally regenerating an example's dedicated
ignored output directory.

The experimental publication example deliberately has no fitting fallback. Pass a
reviewed Phase 1 bundle with `--fit-result PATH`; CSV/XLSX inputs also require their
metadata JSON via `--metadata PATH`. It fails clearly if the numerical export is
missing or does not contain the recipe's five components and fitted centres.

The VGD path is exercised only when `vgd-reader` is installed; the example clearly
reports when this optional dependency is unavailable. Existing tracked experimental
files are read in place and never copied. Figures are saved only as PNG or PDF.

The release's real-data check is intentionally separate from the deterministic
example suite. With `vgd-reader` installed, run
`PYTHONPATH=src MPLBACKEND=Agg python scripts/validate_experimental_workflow.py` to
create ignored PNG/PDF publication, diagnostic, comparison, and raw-series figures
for the tracked PDI spectra. The experimental title is `PDI-H-COOH`; `Synthetic`
is retained only by deterministic validation examples. See
`docs/experimental_validation.md`; successful optimisation is not presented as
chemical validation.
