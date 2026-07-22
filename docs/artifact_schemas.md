# Artifact schema versions

All current lifecycle records use schema version `1`. Readers must fail clearly
when required publication fields are absent; they must not make a legacy bundle
eligible by supplying defaults.

## Fit and spectrum artifact descriptor

Stored inside `manifest.json` under `artifact`: artifact ID/state, sample, region,
model or `raw_spectrum`, creation time, experimental origin, source path/hash/point
count, configuration hash, review state, calibration state, review/calibration
record links, and lineage hashes.

## Review record

Required fields include sample, region, selected candidate/model, accepted decision,
reviewer/date/notes, residual/background/assignment inspection states, constraints
reviewed, warnings acknowledged, source/configuration hashes, candidate artifact
ID, candidate bundle hash, review version, and software/schema versions. Survey
review records omit fit-only inspection fields and identify the raw source hash.

## Calibration record

Required fields include sample, reference region/component/display label, exact
centre before correction, target energy, calculated offset, sign convention,
applied and missing regions, date/reviewer/rationale, source reviewed-bundle hashes,
calibrated-bundle hashes, and software/schema versions.

## Sample manifest

The manifest contains raw region paths/hashes, expected/missing regions, active
uncalibrated reviewed paths and versions, calibrated paths, calibration-record
path/status/offset/timestamp, and creation/update timestamps. It contains no
scientific curve arrays.
