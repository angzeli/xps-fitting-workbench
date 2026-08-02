"""Fit and compare deterministic synthetic PDI-H-COOH C 1s hypotheses."""

import argparse

from _shared import ROOT, add_output_argument, prepare_output, synthetic_c1s

from xps_fitting.configuration import load_config
from xps_fitting.model_comparison import compare_models, comparison_table
from xps_fitting.plotting import export_figure, plot_xps_fit


def main(argv: list[str] | None = None) -> int:
    """Fit and export diagnostics for both synthetic C 1s hypotheses.

    Args:
        argv: Optional command-line arguments; process arguments are used if absent.

    Returns:
        Zero after writing one diagnostic PNG per ordered candidate model.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    add_output_argument(parser)
    args = parser.parse_args(argv)
    output = prepare_output(args.output_dir)
    configs = [load_config(ROOT / "configs" / "fits" / f"pdi_h_cooh_c1s_{count}.json") for count in (4, 5)]
    results = compare_models(synthetic_c1s(561), configs)
    paths = []
    for name, result in results.items():
        figure, _ = plot_xps_fit(
            result, theme="angze_diagnostic", core_level="C 1s", sample_label=f"Synthetic {name}", show_residual=True
        )
        paths.extend(
            export_figure(
                figure, output / f"pdi_h_cooh_{name.lower()}_diagnostic", formats=("png",), overwrite=args.overwrite
            ).values()
        )
    print(comparison_table(results))
    print("Created:", ", ".join(map(str, paths)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
