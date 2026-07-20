"""Fit and compare synthetic PDI-H-COOH C 1s candidate hypotheses."""

from pathlib import Path

import numpy as np

from xps_fitting.configuration import load_config
from xps_fitting.lineshapes import pseudo_voigt
from xps_fitting.model_comparison import compare_models, comparison_table
from xps_fitting.plotting import plot_fit
from xps_fitting.spectrum import Spectrum

root = Path(__file__).resolve().parents[1]
x = np.linspace(280, 294, 561)
y = 25 + sum(pseudo_voigt(x, area, centre, width, 0.5) for area, centre, width in [(1200, 284.65, 1.35), (500, 285.85, 1.45), (400, 287.9, 1.5), (250, 289.15, 1.55), (120, 290.7, 2.2)])
configs = [load_config(root / "configs" / f"pdi_h_cooh_c1s_{count}.json") for count in (4, 5)]
results = compare_models(Spectrum(x, y, region="C 1s", sample_name="synthetic PDI-H-COOH"), configs)
print(comparison_table(results))
output = root / "outputs"; output.mkdir(exist_ok=True)
plot_fit(results["C1s_5"], output / "pdi_h_cooh_c1s_diagnostic.png")
