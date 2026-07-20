"""Command-line entry points."""

from __future__ import annotations

import argparse

from .plotting.configuration import load_plot_config
from .plotting.io import load_curve_result
from .plotting.recipes import plot_from_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="xps-fit")
    subparsers = parser.add_subparsers(dest="command", required=True)
    plot_parser = subparsers.add_parser("plot", help="render Phase 1 curves without refitting")
    plot_parser.add_argument("source"); plot_parser.add_argument("--metadata"); plot_parser.add_argument("--recipe", required=True); plot_parser.add_argument("--output-dir", default=".")
    args = parser.parse_args(argv)
    result = load_curve_result(args.source, args.metadata)
    plot_from_config(result, load_plot_config(args.recipe), args.output_dir)
    return 0
