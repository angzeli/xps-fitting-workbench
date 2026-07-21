# Figure reproducibility

Archive the fit configuration, numerical CSV/XLSX and JSON metadata, plotting recipe,
package version, and final PDF export. Prefer a full `FitResult.to_dict()` JSON
when complete standalone reconstruction is required; the compact Phase 1 JSON export
must be paired with its curve table.

For routine work, `save_fit_bundle()` writes a readable directory containing a
manifest, CSV curves, and complete non-array metadata. `load_fit_bundle()` resolves
those members safely and reconstructs the numerical contract. Existing compact
exports remain supported. All output APIs check the complete target set before
writing and require an explicit overwrite opt-in when a collision exists.

Every plotting entry point validates that component arrays plus background reproduce
the stored total and that raw minus total reproduces the stored residual. Rendering
uses the source sample points directly: there is no fitting, smoothing, interpolation,
normalisation, background calculation, or replacement envelope. Tests compare every
plotted y array against in-memory, CSV, XLSX, and full-JSON sources.
New fits also preserve the spectrum's source file, sample name, and region in
`FitResult.metadata`; VGD ingestion records `data_origin` as experimental.

Use a committed recipe and run headlessly for repeatable automation. PDF metadata
and exact bytes may vary with Matplotlib/font versions; numerical curves, colours,
layout parameters, and physical dimensions remain controlled by the result and recipe.
PNG and PDF are the only supported saved figure formats.

Peak-position annotations are also recipe-controlled. Their text is generated from
the stored fitted centre, not a visual re-fit; their height uses the already displayed
component-plus-background curve. Formatting, leader visibility, negligible/hidden
component policy, and finite per-component point offsets are serialized in
`PlotConfig`. The deterministic collision stagger depends only on fitted centres and
the plotted energy span, so reversed binding-energy axes produce the same labels.

## Exact PDI-H-COOH C 1s figure

The repository previously provided a real-data validation script that called the
optimiser and a generic curve-table CLI, but it did not provide a dedicated
plotting-only command for the accepted experimental C 1s result. The reproducible
route is now:

```bash
PYTHONPATH=src MPLBACKEND=Agg python examples/plot_pdi_h_cooh_c1s_publication.py \
  --fit-result outputs/experimental_validation/pdi_h_cooh_c1s_reviewed.bundle \
  --output-dir outputs/manuscript
```

The default bundle directory must contain `manifest.json`, `curves.csv`, and
`metadata.json`. The curve table supplies binding energy, raw intensity, background,
five component arrays, total fit, and residual. Metadata supplies the accepted fitted
centres and the rest of the `FitResult` contract. The example loads those files with
`load_curve_result()`, applies `configs/plots/c1s_publication.json` through
`plot_from_config()`, and writes only the named 600 dpi PNG and vector PDF. Before
rendering it prints the two resolved member paths, acquisition metadata, and numerical
identity checks. Synthetic/test-fixture provenance, identical raw and fitted curves,
zero backgrounds, and absent raw/background columns are hard errors.

The reviewed experimental bundle is not committed because it is a private project
artifact. There is intentionally no fallback to fitting raw data: a missing or
incomplete export is reported as an error. The generic plotting CLI does not certify
experimental provenance and is therefore not the accepted route for this exact
figure. Clone the recipe and change the core
level, energy limits, output name, and per-assignment annotation offsets to reproduce
the same style for another region.

The broader tracked-data validation workflow can be repeated with
`PYTHONPATH=src MPLBACKEND=Agg python scripts/validate_experimental_workflow.py`.
It performs fitting checks and is not the accepted plotting-only reproduction route.
Its local outputs are deliberately ignored; numerical observations and manual-review
cautions are recorded in `docs/experimental_validation.md`.

The historical validation run saved figures but did not save its in-memory C 1s
`FitResult`. Consequently those PNG/PDF files are not a substitute for the reviewed
curve table, and the plotting-only workflow cannot recover arrays from them. Supply
the archived Phase 1 bundle rather than rerunning the optimiser.
