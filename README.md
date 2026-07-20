# XPS fitting workbench

This project is a reproducible, chemistry-constrained X-ray photoelectron
spectroscopy fitting engine. It optimises user-proposed chemical components and
supports comparison of alternative hypotheses; it does not discover chemical
assignments or endorse a model merely because it has more peaks.

> Peak fitting requires chemical judgement. Fit statistics alone cannot establish
> a chemically correct assignment.

## Status

Phase 1 is under active development. It establishes numerical models, diagnostics,
exports, and a stable result interface. Colourful publication figures are deferred
to Phase 2; Phase 1 plotting is diagnostic only.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
```

The project uses a `src/xps_fitting/` package, `tests/`, `examples/`, `configs/`,
and `docs/`. Raw experimental data, generated outputs, reports, and figures are
ignored. Deliberately curated small text fixtures may be committed under
`tests/data/` or `examples/data/`; see [the data policy](docs/data_policy.md).

The legacy `xps_vgd_utils.py` workflow remains in place while package I/O support
is developed. CSV and XLSX tables, pandas DataFrames, and VGD through the optional
legacy adapter are supported. All input is cleaned, duplicate energies are averaged,
and fitting arrays are ascending regardless of acquisition order; the original order
is recorded in metadata.

```python
from xps_fitting.io import read_csv
spectrum = read_csv("spectrum.csv", region="C 1s", sample_name="sample")
```

Existing notebooks may continue importing `xps_vgd_utils`. New code can use
`xps_fitting.io_vgd.read_vgd`; it requires the separately installed `vgd-reader`
package. Examples and tests use deterministic synthetic data rather than copying
the tracked experimental files. Run `python examples/load_spectrum.py` after an
editable install.
