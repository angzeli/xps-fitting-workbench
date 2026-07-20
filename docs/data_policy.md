# Data policy

Only small, anonymised, scientifically useful text fixtures belong in `tests/data/`
or `examples/data/`. A reduced experimental fixture must remove private paths and
sample identifiers and document the source range, columns, downsampling, and any
normalisation. Raw VGD files and bulk `raw_data/` or `processed_data/` directories
are excluded because they may contain private metadata and are unsuitable for Git.

The raw files already tracked in this repository predate this policy. They are left
untouched, are not copied into tests, and should be reviewed by the data owner.
Deterministic synthetic spectra are the default for tests and examples.
