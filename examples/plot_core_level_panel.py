"""Several core levels for one synthetic sample."""

from pathlib import Path
import numpy as np
from xps_fitting.plotting import export_figure, plot_core_level_panel
from xps_fitting.result import FitResult

root = Path(__file__).resolve().parents[1]; results = []
for region, centre, colour_label in (("C 1s", 285, "aromatic_C-C_C=C"), ("N 1s", 400, "imide_N-C=O"), ("O 1s", 532, "acid_O-C=O")):
    x = np.linspace(centre - 6, centre + 6, 241); bg = np.full_like(x, 2.0); peak = 20 * np.exp(-((x - centre) / 0.8) ** 2); total = bg + peak
    results.append(FitResult(x, total, bg, {colour_label: peak}, total, np.zeros_like(x), {}, configuration={"region": region}))
figure, _ = plot_core_level_panel(results, layout="vertical", sharex=False, core_levels=["C 1s", "N 1s", "O 1s"], sample_labels=["PDI-H-COOH"] * 3, shared_legend=False)
export_figure(figure, root / "outputs/core_level_panel.svg")
