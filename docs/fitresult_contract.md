# FitResult contract

`xps_fitting.result.FitResult` is the Phase 2 numerical interface. Its curve arrays
share one ascending energy grid. `components` contains background-free labelled peak
arrays; `total_fit` equals background plus their sum and `residual` equals raw minus
total. Parameters use `<label>.<area|centre|fwhm|fraction>` keys. The remaining fields
carry uncertainty/correlation estimates, statistics, warnings, the exact configuration,
source metadata, convergence evidence, and software versions. `to_dict()` converts
arrays and NumPy scalars to JSON-compatible values. See `fitresult.schema.json`.

Phase 2 should consume this interface and must not recompute the scientific model.

## Binding-energy calibration

`calibrate_sample_binding_energy()` derives one offset from a stored fitted reference
centre and returns calibrated copies of all supplied `FitResult` and raw `Spectrum`
objects for that sample. In each result it shifts the energy array, all fitted
parameters ending in `.centre`, and the absolute centres/bounds retained in the fit
configuration. It deliberately leaves all y arrays, widths, areas, uncertainties,
statistics, correlations, relative centre offsets, and residual identities unchanged.

The same offset is applied to unfitted core levels and recorded deterministically in
every object's `binding_energy_calibration` metadata. The API rejects mixed sample
identities, a missing or non-finite reference, and an existing calibration record to
prevent accidental double shifts. Export and reload preserve the calibrated grid,
centres, and provenance.
