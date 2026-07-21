"""Render the reviewed PDI-H-COOH C 1s FitResult without refitting."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from _shared import ROOT, add_output_argument, prepare_output

from xps_fitting.plotting import load_curve_result, load_plot_config, plot_from_config
from xps_fitting.result import FitResult

DEFAULT_SOURCE = ROOT / "outputs" / "experimental_validation" / "pdi_h_cooh_c1s_reviewed.bundle"
DEFAULT_RECIPE = ROOT / "configs" / "plots" / "c1s_publication.json"
_ACQUISITION_METADATA = {"technique", "pass_energy_eV", "dwell_time_s", "vgd_spectrum_index"}


def _metadata_path(source: Path, supplied: Path | None) -> Path | None:
    if source.is_dir() or source.suffix.lower() == ".json":
        if supplied is not None:
            raise ValueError("bundle and full-JSON sources contain metadata; omit --metadata")
        return None
    candidate = supplied or source.with_suffix(".json")
    if not candidate.is_file():
        raise FileNotFoundError(f"Phase 1 metadata is missing: {candidate}; pass --metadata PATH")
    return candidate


def _resolved_source_paths(source: Path, metadata: Path | None) -> tuple[Path, Path]:
    if source.is_dir():
        manifest_path = source / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"fit bundle manifest is missing: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        try:
            curves = (source / str(manifest["files"]["curves"])).resolve()
            details = (source / str(manifest["files"]["metadata"])).resolve()
        except KeyError as exc:
            raise ValueError(f"fit bundle manifest lacks {exc.args[0]!r}: {manifest_path}") from exc
        return curves, details
    if source.suffix.lower() == ".json":
        return source, source
    assert metadata is not None
    return source, metadata


def _source_type(result: FitResult) -> str:
    origin = str(result.metadata.get("data_origin", "")).strip().casefold()
    if any(marker in origin for marker in ("synthetic", "fixture", "generated")):
        return "synthetic"
    if "experimental" in origin or _ACQUISITION_METADATA.issubset(result.metadata):
        return "experimental"
    return "unclassified"


def _numerical_audit(result: FitResult) -> dict[str, float]:
    reconstructed = result.background + sum(result.components.values(), start=np.zeros_like(result.energy))
    return {
        "max_abs_raw_minus_total": float(np.max(np.abs(result.raw_intensity - result.total_fit))),
        "background_min": float(np.min(result.background)),
        "background_max": float(np.max(result.background)),
        "max_abs_reconstruction_minus_total": float(np.max(np.abs(reconstructed - result.total_fit))),
    }


def _validate_experimental_result(result: FitResult, source_type: str) -> None:
    if source_type != "experimental":
        raise ValueError(
            f"publication input is {source_type}, not confirmed experimental data; "
            "supply the reviewed Phase 1 experimental FitResult export"
        )
    if np.allclose(result.raw_intensity, result.total_fit, rtol=1e-10, atol=1e-12):
        raise ValueError(
            "publication input has raw_intensity equal to total_fit; stored experimental raw intensity is required"
        )
    if np.allclose(result.background, 0.0, rtol=0.0, atol=1e-12):
        raise ValueError("publication input has a zero background; the stored fitted background is required")


def _array_snapshot(result: FitResult) -> dict[str, np.ndarray]:
    arrays = {
        "energy": result.energy,
        "raw_intensity": result.raw_intensity,
        "background": result.background,
        "total_fit": result.total_fit,
        "residual": result.residual,
    }
    arrays.update({f"component:{label}": curve for label, curve in result.components.items()})
    return {name: np.array(values, copy=True) for name, values in arrays.items()}


def _unchanged_arrays(result: FitResult, before: dict[str, np.ndarray]) -> dict[str, bool]:
    after = _array_snapshot(result)
    return {
        name: bool(np.allclose(values, after[name], rtol=0.0, atol=0.0, equal_nan=True))
        for name, values in before.items()
    }


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

    try:
        metadata = _metadata_path(source, args.metadata.resolve() if args.metadata else None)
        curve_path, metadata_path = _resolved_source_paths(source, metadata)
        print(f"Curve table: {curve_path}")
        print(f"Metadata: {metadata_path}")
        result = load_curve_result(source, metadata)
        source_type = _source_type(result)
        audit = _numerical_audit(result)
        print(f"Source type: {source_type}")
        print("Source-file metadata: " + json.dumps(result.metadata, sort_keys=True, default=str))
        for name, value in audit.items():
            print(f"{name}: {value:.17g}")
        _validate_experimental_result(result, source_type)
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
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

    before = _array_snapshot(result)
    output_dir = prepare_output(args.output_dir.resolve())
    figure, _, paths = plot_from_config(result, config, output_dir, overwrite=args.overwrite)
    plt.close(figure)
    unchanged = _unchanged_arrays(result, before)
    if not all(unchanged.values()):
        changed = ", ".join(name for name, is_unchanged in unchanged.items() if not is_unchanged)
        raise RuntimeError(f"plotting mutated FitResult arrays: {changed}")
    print("Plot-input np.allclose: " + ", ".join(f"{name}={value}" for name, value in unchanged.items()))
    print(f"Input: {source}")
    print(f"Recipe: {recipe_path}")
    print("Created: " + ", ".join(str(path.resolve()) for path in paths.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
