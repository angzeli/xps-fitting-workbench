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
white-background contrast check. Monochrome figures add deterministic line styles.

## Scientific conventions

Filled components extend from the stored background when using
`filled_to_background`. `stacked_visualisation` is display-only and never replaces
the Phase 1 total envelope. Scaling divides all displayed y curves uniformly and is
printed in the axis label. Normalisation and offsets require explicit disclosures.
Never infer comparable absolute intensity from independently scaled panels.
