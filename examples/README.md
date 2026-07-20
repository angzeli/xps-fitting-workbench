# Executable examples

All examples are deterministic and headless. Unless noted otherwise they use
synthetic spectra and write beneath the ignored `outputs/examples/` directory.
Override the destination with `--output-dir PATH`.

| Example | Workflows | Expected outputs |
|---|---|---|
| `load_spectrum.py` | DataFrame, CSV, XLSX, optional tracked experimental VGD | CSV and XLSX input tables |
| `fit_pdi_h_cooh_c1s.py` | Four- and five-component synthetic C 1s fits | Two diagnostic PNGs |
| `compare_pdi_h_cooh_models.py` | Four-versus-five model comparison | PNG and PDF |
| `fit_cl2p_doublet.py` | Constrained 2:1 synthetic Cl 2p doublet | PNG and PDF |
| `plot_single_fit.py` | Publication, residual diagnostic, monochrome SI | PNG and PDF |
| `plot_pdi_c1s_series.py` | Three-sample synthetic multipanel | PNG and PDF |
| `plot_core_level_panel.py` | Synthetic C 1s/N 1s/O 1s panel | PNG and PDF |
| `end_to_end_publication.py` | Fit, Phase 1 export, XLSX reload, curve-table plotting, CLI | Numerical bundle files, PNG and PDF |

Run one example:

```bash
PYTHONPATH=src MPLBACKEND=Agg python examples/plot_single_fit.py
```

Run every retained example independently:

```bash
python scripts/run_all_examples.py
```

The VGD path is exercised only when `vgd-reader` is installed; the example clearly
reports when this optional dependency is unavailable. Existing tracked experimental
files are read in place and never copied. Figures are saved only as PNG or PDF.
