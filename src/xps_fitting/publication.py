"""Plotting-only publication exports from calibrated reviewed artifacts."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from ._version import __version__
from .artifacts import BundleValidationReport, canonical_region, load_publication_bundle
from .plotting.configuration import load_plot_config
from .plotting.recipes import plot_from_config
from .sample_manifest import load_sample_manifest


def _repository_root(anchor: Path, explicit: str | Path | None) -> Path | None:
    if explicit is not None:
        return Path(explicit).resolve()
    for parent in (anchor.resolve(), *anchor.resolve().parents):
        if (parent / "pyproject.toml").is_file():
            return parent
    return None


def _resolve_link(value: str, anchor: Path, repository_root: Path | None) -> Path:
    recorded = Path(value)
    candidates = [recorded] if recorded.is_absolute() else []
    if repository_root is not None and not recorded.is_absolute():
        candidates.append(repository_root / recorded)
    if not recorded.is_absolute():
        candidates.append(anchor / recorded)
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"sample-manifest link does not resolve: {value}")


def load_publication_region(
    manifest_path: str | Path,
    region: str,
    *,
    repository_root: str | Path | None = None,
) -> tuple[Any, BundleValidationReport, dict[str, Any]]:
    """Load one calibrated reviewed FitResult and its sample-level provenance."""
    path = Path(manifest_path).resolve()
    manifest = load_sample_manifest(path)
    canonical = canonical_region(region)
    if manifest.calibration_status != "calibrated" or not manifest.calibration:
        raise ValueError(f"sample {manifest.sample} has no active calibration record")
    if canonical not in manifest.calibrated:
        raise KeyError(f"calibrated reviewed region is unavailable: {canonical}")
    root = _repository_root(path.parent, repository_root)
    calibration_path = _resolve_link(manifest.calibration, path.parent, root)
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    bundle = _resolve_link(manifest.calibrated[canonical], path.parent, root)
    result, report = load_publication_bundle(bundle, require_calibrated=True, repository_root=root)
    metadata = result.metadata.get("binding_energy_calibration", {})
    if report.sample != manifest.sample or report.region != canonical:
        raise ValueError("publication bundle sample or region is inconsistent with the sample manifest")
    if calibration.get("sample") != manifest.sample or canonical not in calibration.get("applied_regions", []):
        raise ValueError("calibration record is inconsistent with the requested sample region")
    if calibration.get("energy_offset_eV") != manifest.energy_offset_eV:
        raise ValueError("sample manifest and calibration record offsets differ")
    if metadata.get("offset_eV") != manifest.energy_offset_eV:
        raise ValueError("bundle and sample manifest calibration offsets differ")
    return (
        result,
        report,
        {
            "sample_manifest": str(path),
            "reviewed_calibrated_bundle": str(bundle),
            "calibration_record": str(calibration_path),
            "energy_offset_eV": manifest.energy_offset_eV,
            "sample": manifest.sample,
            "region": canonical,
        },
    )


def plot_publication_region(
    manifest_path: str | Path,
    region: str,
    recipe: str | Path,
    output_directory: str | Path,
    *,
    repository_root: str | Path | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
):
    """Render PNG/PDF from a stored calibrated result without fitting or mutation."""
    result, report, provenance = load_publication_region(
        manifest_path,
        region,
        repository_root=repository_root,
    )
    recipe_path = Path(recipe).resolve()
    config = load_plot_config(recipe_path)
    if set(config.output_formats) != {"png", "pdf"}:
        raise ValueError("final publication recipes must request exactly PNG and PDF")
    provenance.update(
        {
            "plot_recipe": str(recipe_path),
            "package_version": __version__,
            "publication_validation": report.to_dict(),
        }
    )
    config = replace(
        config,
        metadata={
            "Title": config.output_filename,
            "Subject": (
                f"Reviewed calibrated {provenance['sample']} {provenance['region']}; "
                f"energy offset {provenance['energy_offset_eV']:+.8g} eV"
            ),
            "Creator": f"xps-fitting-workbench {__version__}",
        },
    )
    provenance_path = Path(output_directory) / f"{config.output_filename}.provenance.json"
    if provenance_path.exists() and not overwrite:
        raise FileExistsError(f"figure provenance already exists: {provenance_path}")
    before = result.to_dict()
    figure, axes, paths = plot_from_config(
        result,
        config,
        output_directory,
        overwrite=overwrite,
        dry_run=dry_run,
    )
    if result.to_dict() != before:
        raise RuntimeError("publication plotting mutated the reviewed FitResult")
    provenance["outputs"] = {name: str(path) for name, path in paths.items()}
    if not dry_run:
        provenance_path.parent.mkdir(parents=True, exist_ok=True)
        provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return figure, axes, {**paths, "provenance": provenance_path}, provenance
