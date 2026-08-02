"""Validate tracked PDI workflow mechanics without automating chemical approval.

The script fits experimental inputs, persists candidates before diagnostics, and
exports raw/fitted panels. Its success establishes software workflow integrity,
not scientific acceptance of a component assignment or model.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

# Select the non-interactive backend before importing pyplot.
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from xps_fitting.configuration import load_config
from xps_fitting.io_vgd import read_vgd
from xps_fitting.model_comparison import compare_models, comparison_table
from xps_fitting.optimiser import fit_spectrum
from xps_fitting.plotting import (
    export_figure,
    figure_size_preset,
    load_theme,
    plot_fit_comparison,
    plot_xps_fit,
    style_axes,
    theme_context,
)
from xps_fitting.workflows import persist_candidate_results

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ("PDI-H-COOH", "PDI-Me-COOH", "PDI-OMe-COOH")


def _raw_panel(spectra, labels, core_levels):
    """Plot stored arrays without fitting or normalising source intensities.

    Binding energy is displayed in eV. The recorded intensity scale is labelled as
    counts only because the tracked acquisition supplies that authoritative label.
    """
    with theme_context(load_theme("angze_publication").for_multipanel()) as theme:
        figure, axes = plt.subplots(
            1,
            len(spectra),
            figsize=figure_size_preset("double-column"),
            squeeze=False,
        )
        panels = zip(axes.ravel(), spectra, labels, core_levels)
        for index, (axis, spectrum, label, core_level) in enumerate(panels):
            axis.plot(
                spectrum.binding_energy,
                spectrum.intensity,
                linestyle="none",
                marker=theme.marker,
                markersize=theme.marker_size,
                markerfacecolor=theme.raw_face,
                markeredgecolor=theme.raw_edge,
                markeredgewidth=theme.marker_edge_width,
            )
            style_axes(axis, theme)
            axis.set_xlabel("Binding energy (eV)")
            axis.set_ylabel("Intensity (counts)" if index == 0 else "")
            axis.set_title(
                label,
                loc="left",
                pad=theme.title_padding,
                fontsize=theme.title_size,
                fontweight="bold",
            )
            axis.set_title(
                core_level,
                loc="right",
                pad=theme.title_padding,
                fontsize=theme.core_level_size,
            )
            axis.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
            if theme.invert_binding_energy:
                axis.invert_xaxis()
        figure.tight_layout()
    return figure


def _export(figure, output: Path, *, overwrite: bool) -> list[str]:
    """Save and close a figure, returning PNG/PDF paths in export order."""
    paths = export_figure(figure, output, formats=("png", "pdf"), overwrite=overwrite)
    plt.close(figure)
    return [str(path) for path in paths.values()]


def main(argv: list[str] | None = None) -> int:
    """Fit, persist, and plot the tracked spectra for workflow validation.

    Candidate bundles are written before their diagnostic figures. On success,
    the JSON summary is printed to standard output and zero is returned.

    Args:
        argv: Optional command-line arguments. Process arguments are used when
            this is ``None``.

    Returns:
        Zero after all candidate bundles and figures have been written.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "figures" / "diagnostic" / "experimental_validation",
    )
    parser.add_argument("--artifacts-dir", type=Path, default=ROOT / "artifacts" / "candidates")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--overwrite-candidates", action="store_true")
    args = parser.parse_args(argv)

    # Persist both C 1s candidates before rendering diagnostics from their fitted arrays.
    configs = [load_config(ROOT / "configs" / "fits" / f"pdi_h_cooh_c1s_{count}.json") for count in (4, 5)]
    c1s = read_vgd(ROOT / "data" / "raw" / "PDI-H-COOH" / "C1s Scan.VGD")
    c1s_results = compare_models(c1s, configs)
    c1s_bundles = persist_candidate_results(
        c1s_results,
        sample="PDI-H-COOH",
        region="C1s",
        source_path=ROOT / "data" / "raw" / "PDI-H-COOH" / "C1s Scan.VGD",
        artifacts_root=args.artifacts_dir,
        repository_root=ROOT,
        overwrite=args.overwrite_candidates,
    )
    created: list[str] = []
    for model, result in c1s_results.items():
        diagnostic, _ = plot_xps_fit(
            result,
            theme="angze_diagnostic",
            core_level="C 1s",
            sample_label=f"PDI-H-COOH — {model} candidate",
            component_display_mode="filled_to_background",
            show_peak_positions=True,
            show_residual=True,
            fit_statistics=True,
        )
        created.extend(
            _export(
                diagnostic,
                args.output_dir / f"pdi_h_cooh_{model.casefold()}_candidate",
                overwrite=args.overwrite,
            )
        )
    comparison, _ = plot_fit_comparison(c1s_results, show_residual=False, show_peak_positions=True)
    created.extend(
        _export(
            comparison,
            args.output_dir / "pdi_h_cooh_c1s_model_comparison",
            overwrite=args.overwrite,
        )
    )

    # Persist the configured constrained Cl 2p candidate before plotting it.
    cl2p = read_vgd(ROOT / "data" / "raw" / "PDI-H-COOH" / "Cl2p Scan.VGD")
    cl_config = load_config(ROOT / "configs" / "fits" / "pdi_h_cooh_cl2p_constrained.json")
    cl_result = fit_spectrum(cl2p, cl_config)
    cl_bundles = persist_candidate_results(
        {cl_config.name: cl_result},
        sample="PDI-H-COOH",
        region="Cl2p",
        source_path=ROOT / "data" / "raw" / "PDI-H-COOH" / "Cl2p Scan.VGD",
        artifacts_root=args.artifacts_dir,
        repository_root=ROOT,
        overwrite=args.overwrite_candidates,
    )
    cl_figure, _ = plot_xps_fit(
        cl_result,
        theme="angze_publication",
        core_level="Cl 2p",
        sample_label="PDI-H-COOH",
        show_residual=True,
        show_peak_positions=True,
        label_map={"Cl_2p3/2": "Cl 2p3/2", "Cl_2p1/2": "Cl 2p1/2"},
    )
    created.extend(
        _export(
            cl_figure,
            args.output_dir / "pdi_h_cooh_cl2p_constrained",
            overwrite=args.overwrite,
        )
    )

    # Compare the three stored C 1s intensity arrays without fitting or normalising them.
    c1s_series = [read_vgd(ROOT / "data" / "raw" / sample / "C1s Scan.VGD") for sample in SAMPLES]
    series_figure = _raw_panel(c1s_series, SAMPLES, ("C 1s",) * len(SAMPLES))
    created.extend(_export(series_figure, args.output_dir / "pdi_c1s_raw_series", overwrite=args.overwrite))

    # Plot the stored N 1s and O 1s intensity arrays without fitting them.
    n1s = read_vgd(ROOT / "data" / "raw" / "PDI-H-COOH" / "N1s Scan.VGD")
    o1s = read_vgd(ROOT / "data" / "raw" / "PDI-H-COOH" / "O1s Scan.VGD")
    heteroatom_figure = _raw_panel(
        (n1s, o1s),
        ("PDI-H-COOH", "PDI-H-COOH"),
        ("N 1s", "O 1s"),
    )
    created.extend(
        _export(
            heteroatom_figure,
            args.output_dir / "pdi_h_cooh_n1s_o1s_raw",
            overwrite=args.overwrite,
        )
    )

    # Record candidate review state explicitly; this workflow does not create publication figures.
    summary = {
        "c1s_candidate_models": comparison_table(c1s_results),
        "candidate_bundles": {
            "C1s": {model: str(path) for model, path in c1s_bundles.items()},
            "Cl2p": {model: str(path) for model, path in cl_bundles.items()},
        },
        "cl2p": {
            "fit_statistics": cl_result.fit_statistics,
            "warnings": cl_result.warnings,
            "convergence": cl_result.convergence,
            "fitted_parameters": cl_result.fitted_parameters,
        },
        "raw_spectra_plotted": [f"{sample}/C1s Scan.VGD" for sample in SAMPLES]
        + ["PDI-H-COOH/N1s Scan.VGD", "PDI-H-COOH/O1s Scan.VGD"],
        "created": created,
        "review_required": True,
        "publication_figure_created": False,
        "scientific_caution": "Convergence and information criteria do not establish chemical assignments.",
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
