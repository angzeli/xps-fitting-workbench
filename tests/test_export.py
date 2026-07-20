import json

import numpy as np
import pandas as pd

from xps_fitting.configuration import FitConfig, PeakConfig
from xps_fitting.export import export_result
from xps_fitting.lineshapes import gaussian
from xps_fitting.optimiser import fit_spectrum
from xps_fitting.spectrum import Spectrum


def test_export_bundle_and_curve_consistency(tmp_path) -> None:
    x = np.linspace(0, 10, 101); y = 2 + gaussian(x, 100, 5, 1)
    result = fit_spectrum(Spectrum(x, y, metadata={"id": "synthetic"}), FitConfig("export", "test", [PeakConfig("p", 5, (4, 6), 90, fwhm=1, fwhm_bounds=(0.8, 1.2), line_shape="gaussian")]))
    paths = export_result(result, tmp_path)
    assert all(path.stat().st_size > 0 for path in paths.values())
    csv = pd.read_csv(paths["csv"]); xlsx = pd.read_excel(paths["xlsx"], sheet_name="curves")
    assert list(csv.columns) == list(xlsx.columns)
    assert json.loads(paths["json"].read_text())["metadata"]["id"] == "synthetic"
