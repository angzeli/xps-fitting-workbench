# Plotting style guide

## Visual hierarchy

Experimental observations use small dark markers, the unchanged total fit uses the
strongest line, the stored background is thin and dashed, and components use stable
semantic colours with restrained transparency. Binding energy decreases left to
right. Grids, decorative frames, and titles are absent from publication defaults.

The core-level colours are Survey `#111810`, C 1s `#8C8C8C`, N 1s `#2F80ED`,
O 1s `#EB5757`, S 2p `#F2C94C`, and Cl 2p `#27AE60`. Established element colours
are retained even where a pale hue has limited white-background contrast; they are
used as lines/fills rather than small text. Semantic component lines meet a 3:1
white-background contrast check. The aromatic, C-N/C-Cl, imide, carboxylic and
satellite C 1s assignments; both Cl 2p partners; and the defined O 1s and N 1s
assignments have stable colours across single and multipanel figures. Monochrome
figures add deterministic line styles.

## Geometry and typography

All visible spines in `angze_publication`, `monochrome_publication`, and
`presentation` are exactly 1.8 pt. The same central theme value is applied to main,
residual, multipanel, and inset axes; plotting functions do not override it. Ticks
point inward and use the audited 1.8 pt width. Grids remain off, axis labels are
bold, the total-fit line is strongest, and PDF output uses TrueType-compatible font
embedding where Matplotlib supports it.

Named physical presets are:

| Preset | Width × height (in) | Intended use |
|---|---:|---|
| `single-column` | 3.45 × 2.8 | One fitted region |
| `one-and-a-half-column` | 5.2 × 3.4 | Tall or vertical comparison |
| `double-column` | 7.1 × 3.8 | Horizontal multipanel manuscript figure |
| `presentation` | 8 × 5 | Slide figure |

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
