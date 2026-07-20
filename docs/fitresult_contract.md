# FitResult contract

`xps_fitting.result.FitResult` is the Phase 2 numerical interface. Its curve arrays
share one ascending energy grid. `components` contains background-free labelled peak
arrays; `total_fit` equals background plus their sum and `residual` equals raw minus
total. Parameters use `<label>.<area|centre|fwhm|fraction>` keys. The remaining fields
carry uncertainty/correlation estimates, statistics, warnings, the exact configuration,
source metadata, convergence evidence, and software versions. `to_dict()` converts
arrays and NumPy scalars to JSON-compatible values. See `fitresult.schema.json`.

Phase 2 should consume this interface and must not recompute the scientific model.
