"""End-to-end deterministic Phase 1 fit and Phase 2 publication export."""

from pathlib import Path
import numpy as np

from xps_fitting.configuration import load_config
from xps_fitting.export import export_result
from xps_fitting.lineshapes import pseudo_voigt
from xps_fitting.optimiser import fit_spectrum
from xps_fitting.plotting import export_figure, load_curve_result, plot_xps_fit
from xps_fitting.spectrum import Spectrum

root = Path(__file__).resolve().parents[1]; output = root / "outputs/end_to_end"
x = np.linspace(280, 294, 401)
y = 20 + sum(pseudo_voigt(x, a, c, w, 0.5) for a, c, w in [(1000, 284.65, 1.4), (500, 285.85, 1.4), (400, 287.9, 1.5), (250, 289.15, 1.5), (150, 290.7, 2.2)])
result = fit_spectrum(Spectrum(x, y, region="C 1s", sample_name="synthetic PDI-H-COOH"), load_config(root / "configs/pdi_h_cooh_c1s_5.json"))
paths = export_result(result, output, "pdi_h_cooh_c1s")
reloaded = load_curve_result(paths["xlsx"], paths["json"])
figure, _ = plot_xps_fit(reloaded, core_level="C 1s", sample_label="PDI-H-COOH", component_style="filled_to_background")
export_figure(figure, output / "pdi_h_cooh_c1s_publication", formats=("png", "svg", "pdf"), metadata={"Title": "Synthetic PDI-H-COOH C 1s"})
