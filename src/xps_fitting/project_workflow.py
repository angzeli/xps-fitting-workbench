"""Repository-aware sample inspection, fitting, and validation workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .artifacts import canonical_region, validate_fit_bundle
from .configuration import load_config
from .integrity import sha256_file
from .io_vgd import read_vgd
from .model_comparison import compare_models
from .plotting import export_figure, plot_fit_comparison, plot_xps_fit
from .sample_manifest import (
    create_sample_manifest,
    discover_raw_regions,
    load_sample_manifest,
)
from .spectrum_artifacts import validate_spectrum_bundle
from .workflows import persist_candidate_results


def find_repository_root(start: str | Path = ".") -> Path:
    resolved = Path(start).resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise FileNotFoundError(f"no pyproject.toml found above {resolved}")


def sample_raw_directory(root: str | Path, sample: str) -> Path:
    repository = Path(root).resolve()
    choices = (repository / "data" / "raw" / sample, repository / "example_data" / sample)
    return next((path for path in choices if path.is_dir()), choices[0])


def sample_manifest_path(root: str | Path, sample: str) -> Path:
    return Path(root).resolve() / "artifacts" / "reviewed" / sample / "sample_manifest.json"


def ensure_sample_manifest(root: str | Path, sample: str):
    repository = Path(root).resolve()
    path = sample_manifest_path(repository, sample)
    if path.is_file():
        return load_sample_manifest(path)
    return create_sample_manifest(
        sample,
        sample_raw_directory(repository, sample),
        path,
        repository_root=repository,
    )


def inspect_sample(root: str | Path, sample: str) -> dict[str, Any]:
    repository = Path(root).resolve()
    raw_directory = sample_raw_directory(repository, sample)
    regions = discover_raw_regions(raw_directory)
    raw: dict[str, Any] = {}
    for region, source in regions.items():
        spectrum = read_vgd(source)
        raw[region] = {
            "path": str(source),
            "sha256": sha256_file(source),
            "point_count": int(spectrum.binding_energy.size),
            "energy_min_eV": float(np.min(spectrum.binding_energy)),
            "energy_max_eV": float(np.max(spectrum.binding_energy)),
            "acquisition_metadata": spectrum.metadata,
        }
    manifest_path = sample_manifest_path(repository, sample)
    manifest = load_sample_manifest(manifest_path) if manifest_path.is_file() else None
    candidates = repository / "artifacts" / "candidates" / sample
    return {
        "sample": sample,
        "raw_directory": str(raw_directory),
        "raw_regions": raw,
        "missing_expected_regions": [region for region in ("C1s", "N1s", "O1s", "Cl2p", "Survey") if region not in raw],
        "candidate_bundles": [str(path) for path in sorted(candidates.glob("*/*.bundle"))],
        "sample_manifest": str(manifest_path) if manifest else None,
        "reviewed_uncalibrated": manifest.reviewed_uncalibrated if manifest else {},
        "calibrated": manifest.calibrated if manifest else {},
        "calibration_status": manifest.calibration_status if manifest else "not_created",
    }


def discover_fit_configs(root: str | Path, sample: str, region: str) -> tuple[Path, ...]:
    repository = Path(root).resolve()
    sample_key = "_".join(part.casefold() for part in sample.split("-"))
    region_key = canonical_region(region).casefold()
    directories = (repository / "configs" / "fits", repository / "configs")
    matches: list[Path] = []
    for directory in directories:
        if directory.is_dir():
            matches.extend(sorted(directory.glob(f"{sample_key}_{region_key}_*.json")))
    return tuple(dict.fromkeys(matches))


def fit_region_candidates(
    root: str | Path,
    sample: str,
    region: str,
    *,
    configuration_paths: tuple[str | Path, ...] = (),
    overwrite_candidates: bool = False,
    overwrite_figures: bool = False,
) -> dict[str, Any]:
    """Fit, persist every candidate, and only then render diagnostic figures."""
    repository = Path(root).resolve()
    canonical = canonical_region(region)
    sources = discover_raw_regions(sample_raw_directory(repository, sample))
    if canonical not in sources:
        raise FileNotFoundError(f"raw {canonical} VGD file is unavailable for {sample}")
    selected = tuple(Path(path) for path in configuration_paths) or discover_fit_configs(repository, sample, canonical)
    if not selected:
        raise FileNotFoundError(f"no candidate fit configurations found for {sample} {canonical}")
    configurations = [load_config(path) for path in selected]
    spectrum = read_vgd(sources[canonical])
    results = compare_models(spectrum, configurations)
    bundles = persist_candidate_results(
        results,
        sample=sample,
        region=canonical,
        source_path=sources[canonical],
        artifacts_root=repository / "artifacts" / "candidates",
        repository_root=repository,
        overwrite=overwrite_candidates,
    )
    diagnostic_directory = repository / "figures" / "diagnostic" / sample / canonical
    figures: dict[str, list[str]] = {}
    for model, result in results.items():
        figure, _ = plot_xps_fit(
            result,
            theme="angze_diagnostic",
            core_level=canonical,
            sample_label=f"{sample} — {model} candidate (not reviewed)",
            show_residual=True,
            show_peak_positions=True,
            fit_statistics=True,
        )
        paths = export_figure(
            figure,
            diagnostic_directory / model.casefold(),
            formats=("png", "pdf"),
            overwrite=overwrite_figures,
        )
        import matplotlib.pyplot as plt

        plt.close(figure)
        figures[model] = [str(path) for path in paths.values()]
    if len(results) > 1:
        comparison, _ = plot_fit_comparison(results, show_residual=False, show_peak_positions=True)
        paths = export_figure(
            comparison,
            diagnostic_directory / "model_comparison",
            formats=("png", "pdf"),
            overwrite=overwrite_figures,
        )
        import matplotlib.pyplot as plt

        plt.close(comparison)
        figures["comparison"] = [str(path) for path in paths.values()]
    return {
        "sample": sample,
        "region": canonical,
        "candidate_bundles": {model: str(bundle) for model, bundle in bundles.items()},
        "diagnostic_figures": figures,
        "review_required": True,
        "publication_eligible": False,
    }


def _resolve_manifest_link(value: str, manifest_path: Path, repository: Path) -> Path:
    recorded = Path(value)
    candidates = [recorded] if recorded.is_absolute() else [repository / recorded, manifest_path.parent / recorded]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"sample-manifest link does not resolve: {value}")


def validate_sample(root: str | Path, sample: str, *, require_calibrated: bool = False) -> dict[str, Any]:
    repository = Path(root).resolve()
    path = sample_manifest_path(repository, sample)
    manifest = load_sample_manifest(path)
    errors: list[str] = []
    warnings: list[str] = []
    raw_directory = sample_raw_directory(repository, sample)
    raw = discover_raw_regions(raw_directory)
    for region, recorded_hash in manifest.raw_sha256.items():
        if region not in raw:
            errors.append(f"raw {region} file is missing")
        elif sha256_file(raw[region]) != recorded_hash:
            errors.append(f"raw {region} SHA-256 differs from the manifest")
    if manifest.missing_raw_regions:
        warnings.append("missing raw regions: " + ", ".join(manifest.missing_raw_regions))
    checked: dict[str, Any] = {}
    links = manifest.calibrated if require_calibrated else manifest.reviewed_uncalibrated
    for region, value in links.items():
        bundle = _resolve_manifest_link(value, path, repository)
        bundle_manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        if bundle_manifest.get("format") == "xps-fitting-workbench-fit-bundle":
            report = validate_fit_bundle(
                bundle,
                require_calibrated=require_calibrated,
                repository_root=repository,
            )
        else:
            report = validate_spectrum_bundle(
                bundle,
                require_calibrated=require_calibrated,
                repository_root=repository,
            )
        checked[region] = {
            "path": str(bundle),
            "publication_eligible": report.publication_eligible,
            "errors": list(report.errors),
            "publication_reasons": list(report.publication_reasons),
        }
        errors.extend(f"{region}: {message}" for message in report.errors)
        errors.extend(f"{region}: {message}" for message in report.publication_reasons)
    if require_calibrated and manifest.calibration_status != "calibrated":
        errors.append("sample manifest is not calibrated")
    return {
        "sample": sample,
        "manifest": str(path),
        "calibration_status": manifest.calibration_status,
        "energy_offset_eV": manifest.energy_offset_eV,
        "checked_artifacts": checked,
        "errors": errors,
        "warnings": warnings,
        "valid": not errors,
    }
