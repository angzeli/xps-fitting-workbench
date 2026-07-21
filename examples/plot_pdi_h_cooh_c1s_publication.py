"""Render the reviewed PDI-H-COOH C 1s FitResult without refitting."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from _shared import ROOT, add_output_argument, prepare_output

from xps_fitting.plotting import load_curve_result, load_plot_config, plot_from_config

DEFAULT_SOURCE = ROOT / "outputs" / "experimental_validation" / "pdi_h_cooh_c1s_reviewed.bundle"
DEFAULT_RECIPE = ROOT / "configs" / "plots" / "c1s_publication.json"


def _metadata_path(source: Path, supplied: Path | None) -> Path | None:
    if source.is_dir() or source.suffix.lower() == ".json":
        if supplied is not None:
            raise ValueError("bundle and full-JSON sources contain metadata; omit --metadata")
        return None
    candidate = supplied or source.with_suffix(".json")
    if not candidate.is_file():
        raise FileNotFoundError(f"Phase 1 metadata is missing: {candidate}; pass --metadata PATH")
    return candidate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fit-result",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Reviewed fit bundle, full-result JSON, or CSV/XLSX curve table.",
    )
    parser.add_argument("--metadata", type=Path, help="Phase 1 JSON metadata paired with a curve table.")
    parser.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE, help="Publication plotting recipe.")
    add_output_argument(parser)
    args = parser.parse_args(argv)

    source = args.fit_result.resolve()
    if not source.exists():
        parser.error(f"reviewed Phase 1 FitResult export not found: {source}; pass --fit-result PATH")
    recipe_path = args.recipe.resolve()
    if not recipe_path.is_file():
        parser.error(f"plotting recipe not found: {recipe_path}")

    metadata = _metadata_path(source, args.metadata.resolve() if args.metadata else None)
    result = load_curve_result(source, metadata)
    config = load_plot_config(recipe_path)
    required_components = set(config.peak_annotation_offsets)
    missing_components = sorted(required_components - set(result.components))
    missing_centres = sorted(
        label for label in required_components if f"{label}.centre" not in result.fitted_parameters
    )
    if missing_components or missing_centres:
        details = []
        if missing_components:
            details.append(f"components: {', '.join(missing_components)}")
        if missing_centres:
            details.append(f"fitted centres: {', '.join(missing_centres)}")
        raise ValueError("reviewed FitResult is incomplete for this recipe; missing " + "; ".join(details))

    output_dir = prepare_output(args.output_dir.resolve())
    figure, _, paths = plot_from_config(result, config, output_dir, overwrite=args.overwrite)
    plt.close(figure)
    print(f"Input: {source}")
    if metadata is not None:
        print(f"Metadata: {metadata}")
    print(f"Recipe: {recipe_path}")
    print("Created: " + ", ".join(str(path.resolve()) for path in paths.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
