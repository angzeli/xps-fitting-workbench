# Scientific workflow

The durable workflow is:

```text
Raw Spectrum
  -> persisted Candidate FitResult
  -> explicitly Reviewed FitResult
  -> calibrated reviewed copy
  -> publication PNG/PDF
```

A raw spectrum contains measured energy and intensity. A `FitResult` additionally
contains the exact background, component curves, total fit, residual, fitted
parameters, uncertainties, configuration, convergence evidence, and provenance.
It is not reviewed merely because optimisation converged.

Review is a human scientific decision. Information criteria and residual metrics
help compare models, but they do not prove an assignment. Approval creates a new,
immutable, versioned artifact plus a review record. Calibration then creates new
copies; it never overwrites the reviewed uncalibrated artifacts.

Final plotting accepts only experimental, reviewed, calibrated artifacts with
valid hashes and complete stored curves. Diagnostic plotting may use candidates,
but must label them as unreviewed. Synthetic fixtures are diagnostic/test data and
are never publication eligible.

Saving only PNG or PDF is insufficient. A figure does not preserve full-precision
centres, uncertainties, background values, component arrays, residuals,
configuration, or source hashes. Deleting a figure is safe; losing a reviewed
bundle is loss of scientific evidence.
