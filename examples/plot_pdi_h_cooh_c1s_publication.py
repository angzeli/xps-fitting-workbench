"""Render the active calibrated reviewed PDI-H-COOH C 1s artifact without refitting."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from _shared import ROOT, add_output_argument, prepare_output

from xps_fitting.publication import plot_publication_region

DEFAULT_MANIFEST = ROOT / "artifacts" / "reviewed" / "PDI-H-COOH" / "sample_manifest.json"
DEFAULT_RECIPE = ROOT / "configs" / "plots" / "c1s_publication.json"


def main(argv: list[str] | None = None) -> int:
    """Render a publication figure from an active calibrated reviewed bundle."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample-manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Sample manifest linking the active calibrated reviewed C 1s bundle.",
    )
    parser.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE, help="Publication plotting recipe.")
    add_output_argument(parser)
    args = parser.parse_args(argv)

    manifest = args.sample_manifest.resolve()
    if not manifest.is_file():
        parser.error(f"reviewed calibrated sample manifest not found: {manifest}")
    recipe_path = args.recipe.resolve()
    if not recipe_path.is_file():
        parser.error(f"plotting recipe not found: {recipe_path}")

    output_dir = prepare_output(args.output_dir.resolve())
    try:
        figure, _, paths, provenance = plot_publication_region(
            manifest,
            "C1s",
            recipe_path,
            output_dir,
            repository_root=ROOT,
            overwrite=args.overwrite,
        )
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    plt.close(figure)
    print(f"Reviewed calibrated input: {provenance['reviewed_calibrated_bundle']}")
    print(f"Calibration record: {provenance['calibration_record']}")
    print(f"Energy offset: {provenance['energy_offset_eV']:+.8g} eV")
    print(f"Recipe: {recipe_path}")
    print("Created: " + ", ".join(str(path.resolve()) for path in paths.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
