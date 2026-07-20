"""Three-sample synthetic PDI C 1s series with disclosed normalisation."""

import argparse
import numpy as np
from xps_fitting.result import FitResult
from xps_fitting.plotting import export_figure, plot_xps_series

from _shared import add_output_argument, prepare_output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); add_output_argument(parser); args = parser.parse_args(argv)
    output = prepare_output(args.output_dir); energy = np.linspace(280, 294, 301); results = []
    for sample, shift in (("PDI-H-COOH", 0.0), ("PDI-Me-COOH", 0.08), ("PDI-OMe-COOH", -0.06)):
        background = np.linspace(0.04, 0.06, energy.size)
        components = {"aromatic_C-C_C=C": np.exp(-((energy - 284.65 - shift) / 0.7) ** 2), "C-N_C-Cl": 0.45 * np.exp(-((energy - 285.85 - shift) / 0.8) ** 2)}
        total = background + sum(components.values())
        results.append(FitResult(energy, total, background, components, total, np.zeros_like(energy), {}, configuration={"region": "C 1s"}, metadata={"sample_name": sample, "data_origin": "deterministic synthetic"}))
    figure, _ = plot_xps_series(results, normalised=True, core_levels="C 1s", x_limits=(294, 280))
    paths = export_figure(figure, output / "pdi_c1s_three_sample_series", formats=("png", "pdf"))
    print("Created:", ", ".join(map(str, paths.values())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
