# Reviewing candidate fits

Run `xps-fit review-region --sample SAMPLE --region REGION`. For every candidate,
inspect:

- the background type and whether it follows a defensible inelastic baseline;
- component count, labels, centres, FWHM values, areas, and area fractions;
- residual structure, RMS, extrema, and runs rather than R² alone;
- fitted values at bounds and sensitivity to starting values;
- strong parameter correlations and uncertain parameters;
- line-shape and constraint assumptions;
- chemically plausible assignments and expected stoichiometry;
- every warning printed by the optimiser.

AIC, AICc, BIC, or the highest R² cannot establish chemical correctness. Cancel
when evidence is insufficient. Approval records the reviewer, date, notes,
inspection states, warnings acknowledgement, source/configuration hashes, package
version, and selected candidate lineage. Re-review creates `review-v2`, `review-v3`,
and so on; it never overwrites `review-v1`.
