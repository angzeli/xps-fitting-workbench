# Figure gallery

The gallery is generated locally and is intentionally not committed. Run the examples
below; outputs appear under the ignored `outputs/` directory.

| Figure | Command | Output |
|---|---|---|
| Single C 1s publication/diagnostic/monochrome | `python examples/plot_single_fit.py` | `outputs/c1s_*` |
| Three-compound PDI series | `python examples/plot_pdi_c1s_series.py` | `outputs/pdi_c1s_series.svg` |
| Four- vs five-component model comparison | `python examples/compare_pdi_h_cooh_models.py` | `outputs/pdi_h_model_comparison.pdf` |
| C/N/O core-level panel | `python examples/plot_core_level_panel.py` | `outputs/core_level_panel.svg` |
| Complete fit/export/reload/publication chain | `python examples/end_to_end_publication.py` | `outputs/end_to_end/` |

All examples use deterministic synthetic spectra; no raw experimental data are copied.
