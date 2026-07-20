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

Use a committed recipe and run headlessly for repeatable automation. PDF metadata
and exact bytes may vary with Matplotlib/font versions; numerical curves, colours,
layout parameters, and physical dimensions remain controlled by the result and recipe.
PNG and PDF are the only supported saved figure formats.
