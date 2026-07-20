"""Generate publication, residual-diagnostic, and monochrome synthetic examples."""

from pathlib import Path

import numpy as np

from xps_fitting.configuration import load_config
from xps_fitting.lineshapes import pseudo_voigt
from xps_fitting.optimiser import fit_spectrum
from xps_fitting.plotting import export_figure, plot_xps_fit
from xps_fitting.spectrum import Spectrum

root = Path(__file__).resolve().parents[1]; x = np.linspace(280, 294, 401)
y = 20 + sum(pseudo_voigt(x, a, c, w, 0.5) for a, c, w in [(1000, 284.65, 1.4), (500, 285.85, 1.4), (400, 287.9, 1.5), (250, 289.15, 1.5), (150, 290.7, 2.2)])
result = fit_spectrum(Spectrum(x, y, region="C 1s"), load_config(root / "configs/pdi_h_cooh_c1s_5.json"))
output = root / "outputs"; output.mkdir(exist_ok=True)
for name, kwargs in {
    "c1s_publication": {},
    "c1s_diagnostic": {"theme": "angze_diagnostic", "show_residual": True, "fit_statistics": True},
    "c1s_monochrome": {"theme": "monochrome_publication", "component_style": "outline_only"},
}.items():
    figure, _ = plot_xps_fit(result, core_level="C 1s", sample_label="PDI-H-COOH", **kwargs)
    export_figure(figure, output / name, formats=("png", "svg"), theme=kwargs.get("theme", "angze_publication"))
