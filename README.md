# XPS fitting workbench

This project is a reproducible, chemistry-constrained X-ray photoelectron
spectroscopy fitting engine. It optimises user-proposed chemical components and
supports comparison of alternative hypotheses; it does not discover chemical
assignments or endorse a model merely because it has more peaks.

> Peak fitting requires chemical judgement. Fit statistics alone cannot establish
> a chemically correct assignment.

## Project overview and status

The workbench now treats experimental results as a scientific lifecycle rather
than a plotting session:

```text
Raw Spectrum
  -> persisted Candidate FitResult
  -> explicitly Reviewed FitResult
  -> calibrated reviewed copy
  -> publication PNG/PDF
```

Every experimental candidate is persisted before diagnostics. Review creates an
immutable version and signed decision record. Calibration uses the exact stored
C 1s reference centre and applies one common shift to every reviewed region from
the same sample, including a raw Survey spectrum. Final plotting reads only
reviewed calibrated artifacts and writes a provenance sidecar; it never refits.

Start with the [plain-language quick start](QUICKSTART.md). Scientific details are
in [the workflow](docs/scientific_workflow.md),
[review guide](docs/reviewing_fits.md), [calibration guide](docs/calibration.md),
and [backup guide](docs/artifacts_and_backups.md).

The package version is 0.3.0. `xps_fitting.__version__`, built package metadata,
and the version recorded in new `FitResult.software_versions` all derive from the
single source in `src/xps_fitting/_version.py`.

All eight retained examples now expose `main()`, run headlessly and independently,
identify synthetic versus tracked experimental input, and default to the ignored
`outputs/examples/` directory. See the [complete example index](examples/README.md)
or run `python scripts/run_all_examples.py`. Example figures use PNG and PDF only.

## Installation

```bash
uv sync --python 3.13
uv run xps-fit --help
uv run pytest
```

On macOS, `Start_XPS_Workflow.command` provides a double-click launcher for the
guided workflow.

The main directories have distinct purposes:

| Directory | Meaning | Safe to delete? |
|---|---|---|
| `data/raw/` | immutable acquired VGD/XML data | no |
| `artifacts/candidates/` | persisted unreviewed fits | only after review/backup |
| `artifacts/reviewed/` | durable scientific records | no |
| `figures/diagnostic/` | review figures | yes after review |
| `figures/final/` | regenerated manuscript PNG/PDF | yes |
| `configs/fits/` | candidate hypotheses | no |
| `configs/plots/` | figure recipes | no |

Synthetic examples and automated fixtures are marked `data_origin = synthetic`
and are never publication eligible. See [the data policy](docs/data_policy.md).

The legacy `xps_vgd_utils.py` workflow remains for its original notebook. CSV and
XLSX tables, pandas DataFrames, and VGD through the package adapter are
supported. Old binary XLS input needs a separate pandas engine and is not part of
the declared package workflow. All supported input is cleaned, duplicate energies
are averaged, and fitting arrays are ascending regardless of acquisition order; the
original order is recorded in metadata.

```python
from xps_fitting.io import read_csv
spectrum = read_csv("spectrum.csv", region="C 1s", sample_name="sample")
```

Existing notebooks may continue importing `xps_vgd_utils`. New code can use
`xps_fitting.io_vgd.read_vgd`; `vgd-reader` is installed by `uv sync`. Examples
and tests use deterministic synthetic data rather than copying
the tracked experimental files. The separate validation script reads tracked files
in place. Run `python examples/load_spectrum.py` after an editable install.

## Physical model

Implemented backgrounds are linear and iterative Shirley. Tougaard is deferred
until a responsible convention and validation dataset are selected. Gaussian,
Lorentzian, pseudo-Voigt, and true Voigt functions are area-normalised; widths are
FWHM (the true Voigt accepts separate Gaussian and Lorentzian FWHM values).

Peak configuration supports non-negative/bounded areas, fixed or bounded values,
shared width and fraction groups, fixed centre offsets, fixed area ratios, and
spin-orbit doublets. For example, `cl2p_doublet("Cl", 200.0, 1000.0)` creates a
configurable 1.6 eV-separated pair with 2:1 area, shared FWHM, and shared mixing.
Bounds and assignments remain the analyst's responsibility.

KherveFitting source was not found locally. Its named GL/LA functions can use
product or asymmetric conventions, whereas lmfit's `PseudoVoigtModel` is a linear
mixture of area-normalised Gaussian and Lorentzian profiles with a shared FWHM.
No numerical equivalence is claimed and no Kherve-compatible peak shape is exposed.

## Fitting and diagnostics

`fit_spectrum(spectrum, config)` performs staged optimisation: areas, bounded
centres, bounded FWHMs, then optional mixing fractions. Shirley backgrounds are
updated between stages. Seeded multistart fitting detects sensitivity to guesses.
The primary and default backend is lmfit bounded least squares. SciPy's bounded
`least_squares` is available with `backend="scipy"`; both support selectable robust
loss and record the chosen backend in convergence metadata.

The returned `FitResult` is the Phase 2 contract: ordered energy, raw intensity,
background, labelled component arrays, total fit, residual, fitted parameters,
uncertainties, correlation matrix, fit statistics (RSS, reduced chi-square, AIC,
AICc, BIC, Durbin-Watson, and runs), warnings, configuration, metadata,
convergence details, and software versions. `to_dict()` is JSON-compatible.

Warnings identify bound hits, high correlations, negligible/unresolved components,
nonphysical backgrounds, convergence problems, and multistart sensitivity. These
diagnostics do not prove chemical correctness. `plot_fit` draws raw points,
background, components, total fit, and an optional residual panel with the binding
energy axis reversed; it can save a diagnostic PNG.

## Candidate models

JSON configuration files in `configs/` define the four- and five-component
PDI-H-COOH C 1s hypotheses. The four legend assignments are Aromatic C=C/C–C
(284.65 eV), C–N/C–Cl (285.85 eV), Imide N–C=O (287.90 eV), and Carboxylic
O–C=O (289.15 eV). The
five-component alternative adds a broader pi-pi* satellite near 290.70 eV. There
is deliberately no default 284.10 eV component, and ordinary widths have separate
1.1–2.0 eV bounds rather than an exact global equality. Config objects also support
shared-width groups, a width soft-penalty setting, and relative satellite offsets.

`compare_models` returns every `FitResult`; `comparison_table` reports AIC/AICc/BIC,
RSS, residual diagnostics, warnings, and multistart stability. Resolution and
meaningfulness warnings must be reviewed alongside chemical knowledge: a lower
information criterion is not a declaration of chemical truth.

```bash
MPLBACKEND=Agg python examples/fit_pdi_h_cooh_c1s.py
MPLBACKEND=Agg python examples/fit_cl2p_doublet.py
```

## Experimental workflow validation

The tracked VGD inventory was exercised in place for all three PDI samples. All 15
VGD files parse; PDI-H-COOH C 1s was run through both candidate configurations,
PDI-H-COOH Cl 2p through the constrained doublet, PDI-H-COOH N 1s/O 1s through raw
plotting, and all three C 1s scans through an unnormalised raw comparison. Reproduce
the ignored local PNG/PDF set with:

```bash
PYTHONPATH=src MPLBACKEND=Agg python scripts/validate_experimental_workflow.py
```

Real C 1s residuals were strongly correlated and multiple parameters reached
bounds; the five-component model's lower information criteria do not prove its
satellite assignment. The constrained Cl 2p fit also retained structured residuals
despite a clean convergence status. Review calibration, background, line shapes,
constraints, uncertainty, and chemical evidence before reporting assignments. Full
results and unsupported legacy inputs are recorded in
[the experimental validation report](docs/experimental_validation.md).

## Exports and linked fitting

`export_result(result, directory)` writes a curve CSV, an XLSX workbook with curves,
parameters, statistics, warnings and metadata, a JSON parameter/configuration
summary, a Markdown report, and a diagnostic PNG. Generated files belong in the
ignored `outputs/` directory. The complete result API and schema are documented in
[`docs/fitresult_contract.md`](docs/fitresult_contract.md).

For convenient reload, a fit bundle is a transparent directory rather than an
opaque archive. It contains `manifest.json`, `curves.csv`, and `metadata.json`, so
curves remain spreadsheet-readable while parameters, warnings, configuration,
convergence, provenance, and software versions reload together:

```python
from xps_fitting import load_fit_bundle, save_fit_bundle

save_fit_bundle(result, "outputs/pdi-h-c1s.bundle")
reloaded = load_fit_bundle("outputs/pdi-h-c1s.bundle")
```

### Sample-wide binding-energy calibration

`calibrate_sample_binding_energy()` applies one reviewed rigid correction to every
core level from the same sample without refitting. The reference offset is the target
energy minus the stored fitted C 1s component centre. Pass fitted core levels in the
first mapping and any unfitted raw regions (for example N 1s, O 1s, and Survey) in
`spectra`:

```python
from xps_fitting import calibrate_sample_binding_energy

calibrated_results, calibrated_spectra, calibration = calibrate_sample_binding_energy(
    {"C 1s": c1s_result, "Cl 2p": cl2p_result},
    spectra={"N 1s": n1s_spectrum, "O 1s": o1s_spectrum, "Survey": survey_spectrum},
    reference_component="aromatic_C-C_C=C",
    target_eV=284.8,
)
print(calibration.offset_eV)
```

The API returns copies. It shifts every energy grid, fitted `*.centre`, and absolute
configuration centre/bound by exactly the same offset. Raw intensity, background,
component y arrays, total fit, residuals, areas, widths, uncertainties, and relative
centre offsets remain unchanged. Calibration provenance is stored under
`metadata["binding_energy_calibration"]`, mixed samples and double application are
rejected, and saved fit bundles retain the record. Fixed plotting-recipe `x_limits`
may be translated by the reported offset when an identical viewport is required.

Existing outputs are never silently replaced. Python APIs require
`overwrite=True`; examples and the CLI expose `--overwrite`. Bundle and figure
APIs also support dry-run path planning without writing files.

`fit_shared_shapes` provides limited global-fitting groundwork: it performs separate
first-pass fits, averages selected FWHM/fraction values, and fixes those consensus
values during a second pass. Areas, centres, and intensity remain sample-specific;
configured relative offsets stay exact. This is not simultaneous optimisation,
does not estimate joint covariance, and does not fit a sample-wide charging shift or
bounded per-sample deviations. The calibration API applies an independently reviewed
rigid offset after fitting; it does not estimate that offset from a joint model.

## Reproducibility and development

Use explicit candidate configurations, preserve raw intensity, record crop and
acquisition metadata, set the multistart seed, inspect warnings/residuals, and export
the result bundle. Run the full validation and examples with:

```bash
MPLBACKEND=Agg pytest
PYTHONPATH=src MPLBACKEND=Agg python examples/load_spectrum.py
PYTHONPATH=src MPLBACKEND=Agg python examples/fit_pdi_h_cooh_c1s.py
PYTHONPATH=src MPLBACKEND=Agg python examples/fit_cl2p_doublet.py
```

Current limitations include no Tougaard/asymmetric lines, no uncertainty weighting,
and approximate rather than joint global fitting. See
[the methodology](docs/fitting_methodology.md). Publication styling operates
strictly on the stored `FitResult` arrays.

## Publication themes and colours

`load_theme("angze_publication")` returns a validated, immutable theme. Additional
built-ins are `angze_diagnostic`, `monochrome_publication`, and `presentation`.
Themes are applied through a local Matplotlib context and never leak global
`rcParams` changes. Every visible spine in publication and presentation themes is
fixed at 1.8 pt; attempts to override that contract fail theme validation.

```python
from xps_fitting.plotting import load_theme, core_level_colour
theme = load_theme("angze_publication")
colour = core_level_colour("C1s_Scan")  # #8C8C8C
```

The core-level palette preserves Survey `#111810`, C 1s `#8C8C8C`, N 1s
`#2F80ED`, O 1s `#EB5757`, S 2p `#F2C94C`, and Cl 2p `#27AE60`, including compact
and `_Scan` aliases. Semantic component colours are deterministic across figures;
the C 1s assignments, Cl doublet partners, and O 1s/N 1s assignments all have
stable entries. Monochrome output additionally uses stable line styles. Plotting
validates—but never changes, smooths, normalises, or refits—the Phase 1 arrays.

Physical presets are `single-column` (3.45 × 2.8 in), `one-and-a-half-column`
(5.2 × 3.4 in), `double-column` (7.1 × 3.8 in), `detailed-publication`
(8 × 6 in), and `presentation` (8 × 5 in). Detailed single-spectrum publication
figures use the 8 × 6 preset by default; smaller journal presets remain available
through `figure_size_preset()` or `figure_size_preset` in a plotting recipe.

The detailed hierarchy uses 22 pt bold axis labels, 14 pt bold ticks, a complete
1.8 pt box, hollow 4 pt experimental markers, a 2 pt dark-neutral total fit,
1.3 pt dashed background, 1.5 pt component outlines, and component alpha 0.28.
The compact upper-left legend has a restrained white frame and bold sentence-case
text. The background remains visible but is deliberately omitted from the legend.

## Publication single-spectrum plots

```python
from xps_fitting.plotting import export_figure, plot_xps_fit
fig, axes = plot_xps_fit(
    result, theme="angze_publication", core_level="C 1s",
    component_display_mode="filled_to_background", sample_label="PDI-H-COOH",
    show_sample_title=False, core_level_label_position=(0.97, 0.96),
    show_y_ticks=False, show_top_ticks=False,
    tick_spacing=5, x_minor_interval=2.5,
    show_peak_positions=True, peak_position_precision=1,
    peak_position_unit=True, peak_annotation_leaders=True,
)
export_figure(fig, "outputs/c1s", formats=("png", "pdf"))
```

`plot_xps_fit` returns the Matplotlib Figure and Axes and never calls `show()`.
Available component modes are `lines`, `filled`, `filled_to_background`,
`stacked_visualisation`, `outline_only`, and `hidden`. Stacking is explicitly a
visual device; the strong total-fit line remains the unchanged Phase 1 envelope.
Residuals, peak labels, component percentages, statistics, sample/core/panel labels,
legend ordering, x limits, tick spacing, y-origin behavior, and hidden y ticks are
optional. Use `intensity_units="CPS"` or `"a.u."`; `scale_factor=100000` divides
displayed values and appends the disclosed factor to the axis label. It does not
normalise areas.

`show_peak_positions=True` labels each visible, non-negligible component from its
stored fitted centre while using the displayed component-plus-background apex for
vertical placement. Labels are bold, assignment-coloured, one decimal place with
`eV` by default, and deterministically staggered when neighbouring centres are
close. `peak_annotation_leaders=False` removes leader lines;
`peak_annotation_offsets={"component": (dx, dy)}` adds per-component point offsets.
Hidden and negligible components stay unlabelled unless explicitly requested. The
committed detailed C 1s recipe enables these labels by default.

### Generating the PDI-H-COOH C 1s publication figure

The final workflow resolves the active calibrated reviewed C 1s bundle from
`artifacts/reviewed/PDI-H-COOH/sample_manifest.json`. It rejects candidates,
synthetic/legacy data, unreviewed or uncalibrated bundles, missing arrays,
raw-equals-total fixtures, trivial backgrounds, source/configuration hash errors,
and inconsistent calibration records.

```bash
uv run xps-fit plot-region \
  --sample PDI-H-COOH \
  --region C1s \
  --recipe configs/plots/c1s_publication.json
```

The command creates a 600 dpi PNG, vector PDF, and provenance JSON under
`figures/final/PDI-H-COOH/` without importing or calling the optimiser. It prints
the source bundle and exact calibration offset. The generic `xps-fit plot` command
remains available for diagnostic/legacy rendering, but it is not the final
experimental publication gate.

`configs/plots/c1s_publication.json` is the complete visual provenance. Edit
`peak_annotation_offsets` to change component-specific `(x, y)` point offsets;
`show_sample_title` and `core_level_label_position` control the two title elements.
To reuse the style for N 1s, O 1s, or Cl 2p, copy the recipe, change `core_level`,
`x_limits`, `output_filename`, and the assignment-specific offsets, then pass the
matching reviewed FitResult export. No plotting code change is required.

PNG and PDF are the only supported figure formats. Exports preserve exact physical
theme dimensions, DPI, metadata, and format-appropriate transparent backgrounds.
Unsupported formats are rejected before any file is written. Run
`PYTHONPATH=src MPLBACKEND=Agg python examples/plot_single_fit.py` for publication,
diagnostic-residual, and monochrome synthetic examples.

## Multipanel series and model comparison

`plot_xps_series` supports horizontal, vertical, or explicit row/column grids,
shared or independent axes, stable assignment colours, shared/per-panel legends,
automatic panel/sample labels, common energy windows, offsets, and optional exact
residual insets. Any normalisation or intensity offset must be passed explicitly and
is disclosed inside each affected panel. `show_components=False` provides an
unfitted/raw comparison panel without changing its data. The same peak-position
options work panel by panel with compact theme-controlled annotation text.

`plot_fit_comparison` places candidate models and residuals side by side, annotates
AICc/BIC and warning counts, and records common-component centre/FWHM values on the
Figure as `_xps_component_stability`. Its shared-legend note explicitly cautions
that statistical preference is not chemical proof.

```bash
PYTHONPATH=src MPLBACKEND=Agg python examples/plot_pdi_c1s_series.py
PYTHONPATH=src MPLBACKEND=Agg python examples/compare_pdi_h_cooh_models.py
PYTHONPATH=src MPLBACKEND=Agg python examples/plot_core_level_panel.py
```

Use shared y axes only when intensities are directly comparable. Independent axes
are appropriate for different acquisition scales but must not be interpreted as
absolute intensity comparisons. PDF is recommended for multipanel manuscripts and
PNG for raster review copies.

## Reproducible plotting recipes

Validated JSON recipes under `configs/plots/` cover C 1s, O 1s, N 1s, Cl 2p,
three-sample PDI comparison, residual diagnostics, monochrome SI, and presentations.
They serialize theme, dimensions, formats, colours, component mode, line/marker
sizes, labels, legend order, limits, ticks, disclosures, and panel layout. Invalid
settings fail at load time. `PlotConfig.save()` round-trips custom recipes exactly.

After `pip install -e .`, a Phase 1 curve export can be rendered without refitting:

```bash
xps-fit plot outputs/fit.csv \
  --metadata outputs/fit.json \
  --recipe configs/plots/c1s_publication.json \
  --output-dir outputs/manuscript
```

Fit-bundle directories can be supplied directly. Multiple inputs preserve command
order and use a multipanel recipe; repeat `--sample-label` in the same order:

```bash
xps-fit plot outputs/pdi-h.bundle outputs/pdi-me.bundle outputs/pdi-ome.bundle \
  --recipe configs/plots/pdi_three_sample.json \
  --sample-label PDI-H-COOH \
  --sample-label PDI-Me-COOH \
  --sample-label PDI-OMe-COOH \
  --output-dir outputs/manuscript
```

Use `--dry-run` to validate and print planned paths, `--output-name` for a safe
explicit stem, `--overwrite` for intentional replacement, and `--verbose` only
when a traceback is useful. Ordinary input errors print a concise message and exit
non-zero. The CLI validates PNG/PDF-only recipes before loading curves and never
invokes the optimiser.

Use recipe files as manuscript/SI provenance and commit them alongside analysis
configuration. Prefer PDF for line art, PNG for review, monochrome SI when
colour reproduction is uncertain, and the presentation recipe only for slides.

## Quick start

Fit a chemically proposed model, then pass its result directly to the plotting API:

```python
from xps_fitting.optimiser import fit_spectrum
from xps_fitting.plotting import plot_xps_fit

result = fit_spectrum(spectrum, fit_config)
figure, axes = plot_xps_fit(result, core_level="C 1s")
```

The C 1s examples demonstrate PDI-H-COOH, PDI-Me-COOH, and PDI-OMe-COOH series;
the Cl 2p example preserves its constrained 2:1 doublet. See [the gallery](docs/gallery.md).

## Numerical integrity and scientific cautions

Publication rendering consumes `FitResult`, CSV/XLSX curves plus JSON metadata, or
a full `FitResult.to_dict()` representation. It checks component/background sums and
residual identity before plotting. It never calls the optimiser or recalculates,
smooths, interpolates, renormalises, or edits curves. Good statistics and attractive
figures still do not establish chemical correctness.

## Data import and policy

DataFrame, CSV, XLSX, and optional VGD imports produce ascending fitting arrays
while preserving acquisition order in metadata. Existing legacy `.xls` workbooks
are not supported without an additional engine. Raw experimental files are excluded
from new commits; deterministic synthetic data drive tests and examples, while the
release validation reads already tracked inputs in place. See
[the data policy](docs/data_policy.md).

## Testing and development

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/xps-mpl pytest
ruff check .
ruff format --check .
mypy
python -m build
python scripts/run_all_examples.py --output-dir outputs/examples/quality-check
```

The lightweight local pre-commit hooks run Ruff lint/format and the selected mypy
surface. GitHub Actions tests Python 3.10–3.13, uses headless Matplotlib, runs all
examples, builds the package, and imports the wheel in a clean environment. A
specific third-party `fontTools.misc.py23` deprecation warning is filtered in the
test configuration; unrelated warnings remain visible.

Contributions should add no private/raw data or generated galleries, preserve the
`FitResult` contract, include no-mutation tests for renderers, and update recipes and
documentation with behavior changes.

## Roadmap and limitations

Next priorities are simultaneous global fitting, weighted residual statistics,
validated Tougaard/asymmetric line shapes, and optional journal-specific recipe
packs. Current global fitting remains a two-pass approximation. Figure rasterisation
can vary slightly with local font/Matplotlib versions, and no automatic chemical
assignment or unrestricted peak discovery is planned.

Further guidance: [plotting style](docs/plotting_style_guide.md),
[figure reproducibility](docs/figure_reproducibility.md), and
[FitResult contract](docs/fitresult_contract.md).
