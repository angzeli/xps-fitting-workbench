"""Compare the deterministic four- and five-component C 1s hypotheses."""

import argparse

from _shared import ROOT, add_output_argument, prepare_output, synthetic_c1s

from xps_fitting.configuration import load_config
from xps_fitting.model_comparison import compare_models
from xps_fitting.plotting import export_figure, plot_fit_comparison


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_output_argument(parser)
    args = parser.parse_args(argv)
    output = prepare_output(args.output_dir)
    configs = [load_config(ROOT / f"configs/pdi_h_cooh_c1s_{count}.json") for count in (4, 5)]
    figure, _ = plot_fit_comparison(
        compare_models(synthetic_c1s(), configs),
        show_residual=False,
        show_peak_positions=True,
    )
    paths = export_figure(
        figure, output / "pdi_h_cooh_model_comparison", formats=("png", "pdf"), overwrite=args.overwrite
    )
    print("Synthetic candidate-model comparison created:", ", ".join(map(str, paths.values())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
