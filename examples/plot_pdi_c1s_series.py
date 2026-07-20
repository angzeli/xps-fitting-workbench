"""Three-sample synthetic PDI C 1s series with disclosed normalisation."""

from pathlib import Path
import numpy as np
from xps_fitting.result import FitResult
from xps_fitting.plotting import export_figure, plot_xps_series

root = Path(__file__).resolve().parents[1]; x = np.linspace(280, 294, 301); results = []
for sample, shift in (("PDI-H-COOH", 0.0), ("PDI-Me-COOH", 0.08), ("PDI-OMe-COOH", -0.06)):
    bg = np.linspace(0.04, 0.06, x.size); components = {"aromatic_C-C_C=C": np.exp(-((x - 284.65 - shift) / 0.7) ** 2), "C-N_C-Cl": 0.45 * np.exp(-((x - 285.85 - shift) / 0.8) ** 2)}
    total = bg + sum(components.values()); results.append(FitResult(x, total, bg, components, total, np.zeros_like(x), {}, configuration={"region": "C 1s"}, metadata={"sample_name": sample}))
figure, _ = plot_xps_series(results, normalised=True, core_levels="C 1s", x_limits=(294, 280))
export_figure(figure, root / "outputs/pdi_c1s_series.svg")
