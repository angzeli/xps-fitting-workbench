# Experimental FitResult lifecycle audit

Audit date: 2026-07-21  
Branch: `codex/experimental-workflow-overhaul`  
Starting commit: `294044fe`

## Finding

The numerical fitting and plotting layers work, but the experimental artifact
lifecycle is incomplete. The historical PDI-H-COOH C 1s workflow created the
four- and five-component `FitResult` objects in memory, selected `C1s_5`, and
wrote PNG/PDF figures. It did not call `save_fit_bundle()` or `export_result()`.
The PDI-H-COOH Cl 2p result followed the same in-memory-only path.

The missing item is the reviewed experimental **instance** of `FitResult`, not
the `FitResult` class or its serializer. PNG/PDF files cannot recover its exact
background, component arrays, residual, fitted centres, uncertainties, or
provenance.

## Creation and persistence paths

| Path | Origin | Creates a `FitResult` | Persists before plotting |
|---|---|---:|---:|
| `scripts/validate_experimental_workflow.py` C 1s | experimental VGD | yes, two candidates | no |
| `scripts/validate_experimental_workflow.py` Cl 2p | experimental VGD | yes | no |
| N 1s, O 1s, Survey, other PDI regions | experimental VGD | no; raw-only | not applicable |
| `examples/end_to_end_publication.py` | synthetic | yes | yes |
| Other fitting examples | synthetic | yes | generally no |
| Dedicated experimental publication example | stored input | no | requires an existing export |
| Generic `xps-fit plot` | stored input | no | requires an existing export |

`fit_spectrum()`, `compare_models()`, and `fit_shared_shapes()` deliberately
return in-memory numerical objects. Persistence therefore belongs in the
experimental workflow layer, before any diagnostic or publication figure is
created.

## Recovery search

A controlled search inspected repository copies and likely user locations:

- `/Users/liangze/Desktop` (maximum depth 7)
- `/Users/liangze/Documents` (maximum depth 7)
- `/Users/liangze/Downloads` (maximum depth 7)
- `/private/tmp` (maximum depth 7)
- mounted paths beneath `/Volumes` (maximum depth 7)

The search looked for directories containing the standard bundle members
`manifest.json`, `curves.csv`, and `metadata.json`. No valid archived
experimental XPS bundle was found. The only XPS bundle was
`/private/tmp/xps-c1s-final-review.bundle`, which is a 141-point test fixture:

- `data_origin = test fixture`;
- `raw_intensity` is identical to `total_fit`;
- background is a constant 2.0;
- it is not publication eligible.

The historical result is therefore not recoverable from the locations searched.
The tracked 231-point source remains
`data/raw/PDI-H-COOH/C1s Scan.VGD`. Re-fitting it must create a **new**
candidate generation and must not be represented as recovery of the historical
accepted arrays.

## Current storage classification

- `data/raw/`: tracked raw scientific input; immutable and protected.
- `configs/`: fit hypotheses and plotting recipes; durable provenance.
- `outputs/`: 102 generated files (about 11 MB); no fit bundles or scientific
  manifests. Twelve PNG/PDF files under `outputs/experimental_validation/` are
  historically useful review images but cannot restore `FitResult` arrays.
- `artifacts/`: absent at audit time.
- `figures/`: absent at audit time.

The documented default reviewed-bundle location was under ignored `outputs/`,
which conflicts with both durable scientific records and safe generated-output
cleanup.

## Calibration and plotting gates

`calibrate_sample_binding_energy()` already uses the full-precision stored
reference centre, deep-copies inputs, applies one offset to all supplied fitted
and raw regions, and preserves intensity-domain arrays. It currently lacks a
workflow-level reviewed-state requirement, explicit reference rationale,
required-region check, confirmation, calibration record, persisted calibrated
copies, and sample-manifest update.

Curve plotting validates the two numerical identities but does not centrally
enforce experimental origin, review state, calibration state, hashes, or
publication eligibility. The dedicated C 1s example adds partial provenance
checks; the generic plotting CLI does not.

## Required architecture

Implementation must preserve the following state transitions:

```text
Raw Spectrum
  -> persisted candidate FitResult
  -> explicit human-reviewed, versioned FitResult
  -> calibrated copy plus sample-level calibration record
  -> plotting-only final PNG/PDF
```

Figures remain disposable. Raw inputs, candidate bundles, reviewed versions,
review records, sample manifests, source/configuration hashes, and calibration
records are scientific artifacts. Synthetic or legacy bundles may remain
diagnostically loadable, but missing provenance must never be defaulted into
publication eligibility.
