# Figure gallery

The gallery is generated locally and is intentionally not committed. Run the examples
below; outputs appear under the ignored `outputs/examples/` directory.

| Figure | Command | Output |
|---|---|---|
| Single C 1s publication/diagnostic/monochrome | `python examples/plot_single_fit.py` | `outputs/examples/c1s_*` |
| Three-compound PDI series | `python examples/plot_pdi_c1s_series.py` | `outputs/examples/pdi_c1s_three_sample_series.{png,pdf}` |
| Four- vs five-component model comparison | `python examples/compare_pdi_h_cooh_models.py` | `outputs/examples/pdi_h_cooh_model_comparison.{png,pdf}` |
| C/N/O core-level panel | `python examples/plot_core_level_panel.py` | `outputs/examples/pdi_h_cooh_core_level_panel.{png,pdf}` |
| Complete fit/export/reload/publication chain | `python examples/end_to_end_publication.py` | `outputs/examples/end_to_end_publication/` |
| Reviewed PDI-H-COOH C 1s publication figure | `python examples/plot_pdi_h_cooh_c1s_publication.py --fit-result PATH` | `outputs/examples/pdi_h_cooh_c1s_publication.{png,pdf}` |

Fitting examples use deterministic synthetic spectra. The dedicated experimental
publication example is plotting-only and requires a reviewed Phase 1 export; no raw
experimental data are copied or refitted.
