"""Command-line entry points."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from ._version import __version__
from .naming import make_output_name, result_output_name, validate_output_stem
from .plotting.configuration import load_plot_config
from .plotting.io import load_curve_result
from .plotting.recipes import plot_from_config, plot_series_from_config


def _metadata_sources(values: list[str] | None, count: int) -> list[str | None]:
    if not values:
        return [None] * count
    if len(values) != count:
        raise ValueError("repeat --metadata once for each input source")
    return list(values)


def _print_paths(paths: dict[str, Path], *, dry_run: bool) -> None:
    prefix = "Would create" if dry_run else "Created"
    for path in paths.values():
        print(f"{prefix}: {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="xps-fit", description="Render stored XPS fit results without invoking the optimiser."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    plot_parser = subparsers.add_parser("plot", help="render one result or an ordered multipanel comparison")
    plot_parser.add_argument(
        "sources", nargs="+", help="fit bundle directory, full-result JSON, or CSV/XLSX curve table"
    )
    plot_parser.add_argument(
        "--metadata", action="append", help="metadata JSON paired with a CSV/XLSX source; repeat in source order"
    )
    plot_parser.add_argument("--recipe", required=True, help="validated plotting recipe JSON")
    plot_parser.add_argument("--output-dir", default=".", help="directory for created PNG/PDF figures")
    plot_parser.add_argument("--output-name", help="filesystem-safe output stem overriding the recipe")
    plot_parser.add_argument("--sample-label", action="append", help="panel label; repeat in source order")
    plot_parser.add_argument("--overwrite", action="store_true", help="replace an existing output with the same name")
    plot_parser.add_argument(
        "--dry-run", action="store_true", help="validate inputs and print planned paths without writing figures"
    )
    plot_parser.add_argument("--verbose", action="store_true", help="show a traceback for unexpected failures")
    args = parser.parse_args(argv)
    try:
        config = load_plot_config(args.recipe)
        metadata = _metadata_sources(args.metadata, len(args.sources))
        results = [load_curve_result(source, details) for source, details in zip(args.sources, metadata)]
        if args.sample_label and len(args.sample_label) != len(results):
            raise ValueError("repeat --sample-label once for each input source")
        if args.output_name:
            config = replace(config, output_filename=validate_output_stem(args.output_name))
        elif config.output_filename == "xps_fit":
            if len(results) == 1:
                config = replace(config, output_filename=result_output_name(results[0], plot_type="plot"))
            else:
                generated = make_output_name(
                    sample=f"{len(results)}-samples",
                    region=config.core_level,
                    model="comparison",
                    plot_type="multipanel",
                )
                config = replace(config, output_filename=generated)
        if len(results) == 1:
            figure, _, paths = plot_from_config(
                results[0], config, args.output_dir, overwrite=args.overwrite, dry_run=args.dry_run
            )
        else:
            figure, _, paths = plot_series_from_config(
                results,
                config,
                args.output_dir,
                sample_labels=args.sample_label,
                overwrite=args.overwrite,
                dry_run=args.dry_run,
            )
        import matplotlib.pyplot as plt

        plt.close(figure)
        _print_paths(paths, dry_run=args.dry_run)
        return 0
    except Exception as exc:
        if args.verbose:
            raise
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
