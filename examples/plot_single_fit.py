"""Generate publication, residual-diagnostic, and monochrome synthetic examples."""

import argparse

from xps_fitting.configuration import load_config
from xps_fitting.optimiser import fit_spectrum
from xps_fitting.plotting import export_figure, plot_xps_fit

from _shared import ROOT, add_output_argument, prepare_output, synthetic_c1s


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); add_output_argument(parser); args = parser.parse_args(argv)
    output = prepare_output(args.output_dir)
    result = fit_spectrum(synthetic_c1s(), load_config(ROOT / "configs/pdi_h_cooh_c1s_5.json"))
    recipes = {
        "c1s_publication": ({}, ("png", "pdf")),
        "c1s_diagnostic_residual": ({"theme": "angze_diagnostic", "show_residual": True, "fit_statistics": True}, ("png",)),
        "c1s_monochrome_si": ({"theme": "monochrome_publication", "component_style": "outline_only"}, ("pdf",)),
    }
    paths = []
    for name, (kwargs, formats) in recipes.items():
        figure, _ = plot_xps_fit(result, core_level="C 1s", sample_label="Synthetic PDI-H-COOH", **kwargs)
        paths.extend(export_figure(figure, output / name, formats=formats, theme=kwargs.get("theme", "angze_publication")).values())
    print("Created:", ", ".join(map(str, paths)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
