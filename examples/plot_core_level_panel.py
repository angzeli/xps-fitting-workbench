"""Several core levels for one synthetic sample."""

import argparse
import numpy as np
from xps_fitting.plotting import export_figure, plot_core_level_panel
from xps_fitting.result import FitResult

from _shared import add_output_argument, prepare_output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); add_output_argument(parser); args = parser.parse_args(argv)
    output = prepare_output(args.output_dir); results = []
    levels = (("C 1s", 285, "aromatic_C-C_C=C"), ("N 1s", 400, "imide_N-C=O"), ("O 1s", 532, "acid_O-C=O"))
    for region, centre, assignment in levels:
        energy = np.linspace(centre - 6, centre + 6, 241); background = np.full_like(energy, 2.0); peak = 20 * np.exp(-((energy - centre) / 0.8) ** 2); total = background + peak
        results.append(FitResult(energy, total, background, {assignment: peak}, total, np.zeros_like(energy), {}, configuration={"region": region}, metadata={"data_origin": "deterministic synthetic"}))
    figure, _ = plot_core_level_panel(results, layout="vertical", sharex=False, core_levels=[item[0] for item in levels], sample_labels=["Synthetic PDI-H-COOH"] * 3, shared_legend=False)
    paths = export_figure(figure, output / "pdi_h_cooh_core_level_panel", formats=("png", "pdf"))
    print("Created:", ", ".join(map(str, paths.values())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
