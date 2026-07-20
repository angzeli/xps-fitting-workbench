"""Compare the deterministic four- and five-component C 1s hypotheses."""

from pathlib import Path
import numpy as np
from xps_fitting.configuration import load_config
from xps_fitting.lineshapes import pseudo_voigt
from xps_fitting.model_comparison import compare_models
from xps_fitting.plotting import export_figure, plot_fit_comparison
from xps_fitting.spectrum import Spectrum

root = Path(__file__).resolve().parents[1]; x = np.linspace(280, 294, 401)
y = 20 + sum(pseudo_voigt(x, a, c, w, 0.5) for a, c, w in [(1000, 284.65, 1.4), (500, 285.85, 1.4), (400, 287.9, 1.5), (250, 289.15, 1.5), (150, 290.7, 2.2)])
configs = [load_config(root / f"configs/pdi_h_cooh_c1s_{count}.json") for count in (4, 5)]
figure, _ = plot_fit_comparison(compare_models(Spectrum(x, y), configs))
export_figure(figure, root / "outputs/pdi_h_model_comparison.pdf")
