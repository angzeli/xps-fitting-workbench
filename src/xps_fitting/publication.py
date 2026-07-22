"""Plotting-only publication exports from calibrated reviewed artifacts."""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np

from ._version import __version__
from .artifacts import canonical_region, load_publication_bundle, utc_now
from .plotting.configuration import load_plot_config
from .plotting.recipes import plot_from_config
from .plotting.sample_panel import PANEL_REGIONS, plot_sample_panel
from .plotting.survey import plot_survey_from_config
from .result import FitResult
from .sample_manifest import EXPECTED_REGIONS, load_sample_manifest
from .spectrum import Spectrum
from .spectrum_artifacts import load_spectrum_bundle, validate_spectrum_bundle


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
) -> tuple[Any, Any, dict[str, Any]]:
    """Load one calibrated reviewed fitted region or Survey and its provenance."""
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
    bundle_manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    if bundle_manifest.get("format") == "xps-fitting-workbench-fit-bundle":
        result, report = load_publication_bundle(bundle, require_calibrated=True, repository_root=root)
    elif bundle_manifest.get("format") == "xps-fitting-workbench-spectrum-bundle":
        result = load_spectrum_bundle(bundle)
        report = validate_spectrum_bundle(bundle, require_calibrated=True, repository_root=root)
        if not report.publication_eligible:
            reasons = (*report.errors, *report.publication_reasons)
            raise ValueError("spectrum is not publication eligible:\n" + "\n".join(reasons))
    else:
        raise ValueError(f"unsupported calibrated artifact bundle: {bundle}")
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
    if config.core_level and canonical_region(config.core_level) != canonical_region(region):
        raise ValueError("publication recipe core level does not match the requested region")
    if set(config.output_formats) != {"png", "pdf"}:
        raise ValueError("final publication recipes must request exactly PNG and PDF")
    provenance.update(
        {
            "plot_recipe": str(recipe_path),
            "package_version": __version__,
            "generation_timestamp": utc_now(),
            "publication_validation": asdict(report),
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
    if isinstance(result, FitResult):
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
    elif isinstance(result, Spectrum):
        before_energy = result.binding_energy.copy()
        before_intensity = result.intensity.copy()
        figure, axes, paths = plot_survey_from_config(
            result,
            config,
            output_directory,
            overwrite=overwrite,
            dry_run=dry_run,
        )
        if not np.array_equal(result.binding_energy, before_energy) or not np.array_equal(
            result.intensity, before_intensity
        ):
            raise RuntimeError("publication plotting mutated the reviewed Survey")
    else:
        raise TypeError("unsupported publication artifact type")
    provenance["outputs"] = {name: str(path) for name, path in paths.items()}
    if not dry_run:
        provenance_path.parent.mkdir(parents=True, exist_ok=True)
        provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return figure, axes, {**paths, "provenance": provenance_path}, provenance


def plot_publication_sample(
    manifest_path: str | Path,
    recipe: str | Path,
    output_directory: str | Path,
    *,
    repository_root: str | Path | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> tuple[dict[str, dict[str, Path]], dict[str, Any]]:
    """Generate all five individual figures and the complete sample panel without fitting."""
    path = Path(manifest_path).resolve()
    manifest = load_sample_manifest(path)
    if manifest.calibration_status != "calibrated" or set(manifest.calibrated) != set(EXPECTED_REGIONS):
        raise ValueError("publication plotting requires all five reviewed regions under one active calibration")
    recipe_path = Path(recipe).resolve()
    data = json.loads(recipe_path.read_text(encoding="utf-8"))
    if data.get("kind") != "pdi_sample_publication":
        raise ValueError("sample publication recipe has an unsupported kind")
    regions = tuple(data.get("regions", ()))
    if regions != PANEL_REGIONS:
        raise ValueError("sample publication recipe must contain Survey, C1s, N1s, O1s, and Cl2p")
    output_formats = tuple(data.get("output_formats", ()))
    if set(output_formats) != {"png", "pdf"}:
        raise ValueError("sample publication recipe must request exactly PNG and PDF")
    individual_recipe_values = dict(data.get("individual_recipes", {}))
    if set(individual_recipe_values) != set(PANEL_REGIONS):
        raise ValueError("sample publication recipe must provide one recipe for every region")

    datasets = {}
    validations = {}
    source_bundles = {}
    offsets = set()
    calibration_records = set()
    configs = {}
    recipe_paths = {}
    for region in PANEL_REGIONS:
        dataset, report, provenance = load_publication_region(path, region, repository_root=repository_root)
        datasets[region] = dataset
        validations[region] = asdict(report)
        source_bundles[region] = provenance["reviewed_calibrated_bundle"]
        offsets.add(provenance["energy_offset_eV"])
        calibration_records.add(provenance["calibration_record"])
        recorded_recipe = Path(individual_recipe_values[region])
        recipe_paths[region] = recorded_recipe if recorded_recipe.is_absolute() else recipe_path.parent / recorded_recipe
        configs[region] = load_plot_config(recipe_paths[region])
    if len(offsets) != 1 or len(calibration_records) != 1:
        raise ValueError("publication inputs contain mixed calibration states")

    outputs: dict[str, dict[str, Path]] = {}
    import matplotlib.pyplot as plt

    for region in PANEL_REGIONS:
        figure, _, paths, _ = plot_publication_region(
            path,
            region,
            recipe_paths[region],
            output_directory,
            repository_root=repository_root,
            overwrite=overwrite,
            dry_run=dry_run,
        )
        plt.close(figure)
        outputs[region] = paths
    panel_filename = str(data.get("output_filename", "pdi_h_cooh_xps_panel"))
    panel_provenance_path = Path(output_directory) / f"{panel_filename}.provenance.json"
    if panel_provenance_path.exists() and not overwrite:
        raise FileExistsError(f"figure provenance already exists: {panel_provenance_path}")
    panel_provenance = {
        "sample_manifest": str(path),
        "source_reviewed_bundles": source_bundles,
        "calibration_record": next(iter(calibration_records)),
        "energy_offset_eV": next(iter(offsets)),
        "plot_recipe": str(recipe_path),
        "package_version": __version__,
        "generation_timestamp": utc_now(),
        "publication_validation": validations,
    }
    panel, _, panel_paths = plot_sample_panel(
        datasets,
        configs,
        output_directory,
        output_filename=panel_filename,
        output_formats=output_formats,
        dpi=int(data.get("dpi", 600)),
        metadata={
            "Title": panel_filename,
            "Subject": f"Reviewed calibrated {manifest.sample}; energy offset {next(iter(offsets))!r} eV",
            "Creator": f"xps-fitting-workbench {__version__}",
        },
        overwrite=overwrite,
        dry_run=dry_run,
    )
    plt.close(panel)
    panel_provenance["outputs"] = {name: str(output) for name, output in panel_paths.items()}
    if not dry_run:
        panel_provenance_path.parent.mkdir(parents=True, exist_ok=True)
        panel_provenance_path.write_text(json.dumps(panel_provenance, indent=2) + "\n", encoding="utf-8")
    outputs["panel"] = {**panel_paths, "provenance": panel_provenance_path}
    return outputs, panel_provenance
