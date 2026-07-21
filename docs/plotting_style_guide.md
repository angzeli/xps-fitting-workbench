# Plotting style guide

## Visual hierarchy

Experimental observations use hollow 4 pt markers with 0.9 pt dark edges, the
unchanged total fit uses a 2 pt dark-neutral line, the stored background is a 1.3 pt
dashed neutral line, and components use 1.5 pt stable semantic outlines with alpha
0.28 fills. Binding energy decreases left to right and grids remain off.

Publication legends use a compact white frame with a dark 1 pt edge, 0.95 frame
alpha, minimally rounded corners, and approximately 11 pt bold text. Labels use
sentence case and typographic en dashes. The background stays visible on the axes
but is omitted from the legend. Deterministic C 1s labels are Aromatic C=C/C–C,
C–N/C–Cl, Imide N–C=O, Carboxylic O–C=O, and π–π* satellite.

The core-level colours are Survey `#111810`, C 1s `#8C8C8C`, N 1s `#2F80ED`,
O 1s `#EB5757`, S 2p `#F2C94C`, and Cl 2p `#27AE60`. Established element colours
are retained even where a pale hue has limited white-background contrast; they are
used as lines/fills rather than small text. Semantic component lines meet a 3:1
white-background contrast check. The aromatic, C-N/C-Cl, imide, carboxylic and
satellite C 1s assignments; both Cl 2p partners; and the defined O 1s and N 1s
assignments have stable colours across single and multipanel figures. Monochrome
figures add deterministic line styles.

## Geometry and typography

All four spines in `angze_publication`, `monochrome_publication`, and `presentation`
are visible and exactly 1.8 pt. The same central theme value is applied to main,
residual, multipanel, and inset axes; plotting functions do not override it. Ticks
point inward, use the audited 1.8 pt width, and have bold 14 pt labels on both axes.
Detailed axis labels are 22 pt bold, sample titles are 18 pt bold, and core-level
labels are 16.5 pt. Multipanel figures retain those weights and line values but use
the theme's compact 10 pt axis labels, 9 pt ticks, 9 pt titles, 8.5 pt core-level
labels, and 9 pt legends. PDF output uses TrueType-compatible font embedding where
Matplotlib supports it.

Named physical presets are:

| Preset | Width × height (in) | Intended use |
|---|---:|---|
| `single-column` | 3.45 × 2.8 | One fitted region |
| `one-and-a-half-column` | 5.2 × 3.4 | Tall or vertical comparison |
| `double-column` | 7.1 × 3.8 | Horizontal multipanel manuscript figure |
| `detailed-publication` | 8 × 6 | Detailed single-spectrum fit and annotations |
| `presentation` | 8 × 5 | Slide figure |

The detailed publication theme uses 10% vertical headroom above the highest
displayed curve so peaks and later annotations do not touch the complete box.

## Component binding-energy annotations

Set `show_peak_positions=True` to place an assignment-coloured, bold binding-energy
label above each visible component. The numeric value comes from
`FitResult.fitted_parameters["<component>.centre"]`; the vertical anchor comes from
the apex of the component as it is displayed, including its fitted background.
Values use one decimal place and `eV` by default and are not added to the legend.

Close fitted centres are detected from a theme-controlled fraction of the displayed
energy span and staggered vertically in point units. Short colour-matched leaders
preserve association. `peak_annotation_leaders=False` disables them, while
`peak_annotation_offsets={"component": (dx, dy)}` applies finite manual point
offsets after staggering. Anchors are clamped just inside either orientation of the
x axis; rendered text bounds are then kept inside the axes and shifted clear of a
framed per-axis legend while colour-matched leaders preserve the fitted-centre
association. Negligible and hidden components are omitted unless their explicit
include options are enabled. Multipanels use the same algorithm with compact 8 pt
text.

PNG is the supported raster output and PDF is the supported vector output. Format
validation happens before directory creation or rendering, so an unsupported request
cannot leave a partial output set.

## Scientific conventions

Filled components extend from the stored background when using
`filled_to_background`. `stacked_visualisation` is display-only and never replaces
the Phase 1 total envelope. Scaling divides all displayed y curves uniformly and is
printed in the axis label. Normalisation and offsets require explicit disclosures.
Never infer comparable absolute intensity from independently scaled panels.

Themes are immutable and scoped with `matplotlib.rc_context`, so plotting leaves
application-wide `rcParams` unchanged. `validate_theme()` checks the fixed spine
rule, format choices, alpha range, line hierarchy, required semantic colours, and
unknown override keys.
