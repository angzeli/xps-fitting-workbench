# XPS fitting workbench

This project is a reproducible, chemistry-constrained X-ray photoelectron
spectroscopy fitting engine. It optimises user-proposed chemical components and
supports comparison of alternative hypotheses; it does not discover chemical
assignments or endorse a model merely because it has more peaks.

> Peak fitting requires chemical judgement. Fit statistics alone cannot establish
> a chemically correct assignment.

## Status

Phase 1 provides the numerical fitting contract. Phase 2 is adding reusable,
publication-ready rendering while preserving every fitted array exactly.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
```

The project uses a `src/xps_fitting/` package, `tests/`, `examples/`, `configs/`,
and `docs/`. Raw experimental data, generated outputs, reports, and figures are
ignored. Deliberately curated small text fixtures may be committed under
`tests/data/` or `examples/data/`; see [the data policy](docs/data_policy.md).

The legacy `xps_vgd_utils.py` workflow remains in place while package I/O support
is developed. CSV and XLSX tables, pandas DataFrames, and VGD through the optional
legacy adapter are supported. All input is cleaned, duplicate energies are averaged,
and fitting arrays are ascending regardless of acquisition order; the original order
is recorded in metadata.

```python
from xps_fitting.io import read_csv
spectrum = read_csv("spectrum.csv", region="C 1s", sample_name="sample")
```

Existing notebooks may continue importing `xps_vgd_utils`. New code can use
`xps_fitting.io_vgd.read_vgd`; it requires the separately installed `vgd-reader`
package. Examples and tests use deterministic synthetic data rather than copying
the tracked experimental files. Run `python examples/load_spectrum.py` after an
editable install.

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
PDI-H-COOH C 1s hypotheses. The four assignments are aromatic C-C/C=C (284.65 eV),
C-N/C-Cl (285.85 eV), imide N-C=O (287.90 eV), and acid O-C=O (289.15 eV). The
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

## Exports and linked fitting

`export_result(result, directory)` writes a curve CSV, an XLSX workbook with curves,
parameters, statistics, warnings and metadata, a JSON parameter/configuration
summary, a Markdown report, and a diagnostic PNG. Generated files belong in the
ignored `outputs/` directory. The complete result API and schema are documented in
[`docs/fitresult_contract.md`](docs/fitresult_contract.md).

`fit_shared_shapes` provides limited global-fitting groundwork: it performs separate
first-pass fits, averages selected FWHM/fraction values, and fixes those consensus
values during a second pass. Areas, centres, and intensity remain sample-specific;
configured relative offsets stay exact. This is not simultaneous optimisation,
does not estimate joint covariance, and does not yet fit a sample-wide charging
shift or bounded per-sample deviations.

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
and approximate rather than
joint global fitting. See [the methodology](docs/fitting_methodology.md). Phase 2
builds publication-quality styling strictly on the `FitResult` arrays.

## Publication themes and colours

`load_theme("angze_publication")` returns a validated, immutable theme. Additional
built-ins are `angze_diagnostic`, `monochrome_publication`, and `presentation`.
Themes are applied through a local Matplotlib context and never leak global
`rcParams` changes.

```python
from xps_fitting.plotting import load_theme, core_level_colour
theme = load_theme("angze_publication")
colour = core_level_colour("C1s_Scan")  # #8C8C8C
```

The core-level palette preserves Survey `#111810`, C 1s `#8C8C8C`, N 1s
`#2F80ED`, O 1s `#EB5757`, S 2p `#F2C94C`, and Cl 2p `#27AE60`, including compact
and `_Scan` aliases. Semantic component colours are deterministic across figures;
monochrome output additionally uses stable line styles. Plotting validates—but
never changes, smooths, normalises, or refits—the Phase 1 arrays.

## Publication single-spectrum plots

```python
from xps_fitting.plotting import export_figure, plot_xps_fit
fig, axes = plot_xps_fit(
    result, theme="angze_publication", core_level="C 1s",
    component_style="filled_to_background", sample_label="PDI-H-COOH",
)
export_figure(fig, "outputs/c1s", formats=("png", "svg", "pdf"))
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

PNG, SVG, PDF, and TIFF exports support physical theme dimensions, DPI, tight
bounding boxes, metadata where supported, and transparent backgrounds. Run
`PYTHONPATH=src MPLBACKEND=Agg python examples/plot_single_fit.py` for publication,
diagnostic-residual, and monochrome synthetic examples.
