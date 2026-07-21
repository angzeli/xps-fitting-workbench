# Data policy

The project-owned experimental acquisitions live under `data/raw/SAMPLE/`. They
are immutable scientific inputs: preserve acquisition names and metadata, record
SHA-256 values, and never overwrite them during fitting or calibration. The data
owner must review privacy and repository-size implications before adding a new raw
dataset; Git LFS or an external backed-up store may be more appropriate for large
collections.

Only small, anonymised fixtures belong under `tests/fixtures/` or synthetic example
data locations. A reduced experimental fixture must document its source range,
columns, downsampling, and normalisation. Automated tests use unmistakably marked
synthetic spectra by default. Synthetic artifacts set `data_origin = synthetic`
and `publication_eligible = false`.
