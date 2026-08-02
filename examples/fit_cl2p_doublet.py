"""Fit a deterministic synthetic Cl 2p doublet with exact parameter links."""

import argparse

import numpy as np
from _shared import add_output_argument, prepare_output

from xps_fitting.configuration import FitConfig
from xps_fitting.constraints import cl2p_doublet
from xps_fitting.lineshapes import pseudo_voigt
from xps_fitting.optimiser import fit_spectrum
from xps_fitting.plotting import export_figure, plot_xps_fit
from xps_fitting.spectrum import Spectrum


def main(argv: list[str] | None = None) -> int:
    """Fit and plot a deterministic Cl 2p doublet with linked parameters.

    Args:
        argv: Optional command-line arguments; process arguments are used if absent.

    Returns:
        Zero after writing PNG/PDF figures and printing fit statistics.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    add_output_argument(parser)
    args = parser.parse_args(argv)
    output = prepare_output(args.output_dir)
    energy = np.linspace(195, 207, 481)
    intensity = 10 + pseudo_voigt(energy, 1000, 200, 1.2, 0.5) + pseudo_voigt(energy, 500, 201.6, 1.2, 0.5)
    result = fit_spectrum(
        Spectrum(energy, intensity, region="Cl 2p", metadata={"data_origin": "deterministic synthetic"}),
        FitConfig("Cl_doublet", "Cl 2p", cl2p_doublet("Cl", 199.8, 900)),
    )
    figure, _ = plot_xps_fit(
        result,
        core_level="Cl 2p",
        sample_label="Synthetic Cl 2p",
        show_residual=True,
        show_peak_positions=True,
        label_map={"Cl_2p3/2": "Cl 2p3/2", "Cl_2p1/2": "Cl 2p1/2"},
    )
    paths = export_figure(figure, output / "cl2p_constrained_doublet", formats=("png", "pdf"), overwrite=args.overwrite)
    print(result.fit_statistics)
    print("Created:", ", ".join(map(str, paths.values())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
