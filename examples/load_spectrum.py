"""Load a deliberately messy synthetic table through the public I/O API."""

import pandas as pd

from xps_fitting.io import spectrum_from_dataframe

frame = pd.DataFrame({"energy": [286.0, 285.0, 285.0, "bad", 284.0], "counts": [1, 3, 5, 9, 2]})
spectrum = spectrum_from_dataframe(frame, "energy", "counts", region="C 1s", sample_name="synthetic")
print(f"Loaded {spectrum.binding_energy.size} ordered points: {spectrum.binding_energy}")
