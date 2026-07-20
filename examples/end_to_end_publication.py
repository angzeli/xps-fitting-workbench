"""End-to-end deterministic Phase 1 fit and Phase 2 publication export."""

import argparse

from _shared import ROOT, add_output_argument, prepare_output, synthetic_c1s

from xps_fitting.cli import main as cli_main
from xps_fitting.configuration import load_config
from xps_fitting.export import export_result
from xps_fitting.optimiser import fit_spectrum
from xps_fitting.plotting import export_figure, load_curve_result, plot_xps_fit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_output_argument(parser)
    args = parser.parse_args(argv)
    output = prepare_output(args.output_dir)
    result = fit_spectrum(synthetic_c1s(), load_config(ROOT / "configs/pdi_h_cooh_c1s_5.json"))
    paths = export_result(result, output, "pdi_h_cooh_c1s", overwrite=args.overwrite)
    reloaded = load_curve_result(paths["xlsx"], paths["json"])
    figure, _ = plot_xps_fit(
        reloaded, core_level="C 1s", sample_label="Synthetic PDI-H-COOH", component_display_mode="filled_to_background"
    )
    publication = export_figure(
        figure,
        output / "pdi_h_cooh_c1s_publication",
        formats=("png", "pdf"),
        metadata={"Title": "Synthetic PDI-H-COOH C 1s"},
        overwrite=args.overwrite,
    )
    cli_output = prepare_output(output / "cli")
    cli_arguments = [
        "plot",
        str(paths["csv"]),
        "--metadata",
        str(paths["json"]),
        "--recipe",
        str(ROOT / "configs/plots/c1s_publication.json"),
        "--output-dir",
        str(cli_output),
    ]
    if args.overwrite:
        cli_arguments.append("--overwrite")
    if cli_main(cli_arguments) != 0:
        raise RuntimeError("CLI plotting example failed")
    print(
        "Phase 1 export/reload and CLI plot succeeded. Created:",
        ", ".join(map(str, [*paths.values(), *publication.values()])),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
