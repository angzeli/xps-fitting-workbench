"""FitResult export bundle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from ._version import __version__
from .integrity import sha256_file, validate_result_integrity
from .naming import validate_output_stem
from .plotting import plot_fit
from .plotting.export import export_figure
from .result import FitResult


def curve_table(result: FitResult) -> pd.DataFrame:
    """Return aligned energy, measured, fitted, component, and residual columns."""
    data: dict[str, Any] = {
        "binding_energy_eV": result.energy,
        "raw_intensity": result.raw_intensity,
        "background": result.background,
    }
    data.update({f"component:{label}": curve for label, curve in result.components.items()})
    data.update({"total_fit": result.total_fit, "residual": result.residual})
    return pd.DataFrame(data)


def _summary(result: FitResult) -> dict[str, Any]:
    complete = result.to_dict()
    return {
        key: complete[key]
        for key in (
            "fitted_parameters",
            "parameter_uncertainties",
            "correlation_matrix",
            "fit_statistics",
            "warnings",
            "configuration",
            "metadata",
            "convergence",
            "software_versions",
        )
    }


def _check_collisions(paths: dict[str, Path], *, overwrite: bool) -> None:
    collisions = [path for path in paths.values() if path.exists()]
    if collisions and not overwrite:
        names = ", ".join(str(path) for path in collisions)
        raise FileExistsError(f"output already exists: {names}; pass overwrite=True to replace it")


def export_result(
    result: FitResult,
    directory: str | Path,
    stem: str = "fit",
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Path]:
    """Write XLSX, CSV, JSON, Markdown, and diagnostic PNG exports."""
    directory = Path(directory)
    stem = validate_output_stem(stem)
    paths = {suffix: directory / f"{stem}.{suffix}" for suffix in ("xlsx", "csv", "json", "md", "png")}
    _check_collisions(paths, overwrite=overwrite)
    if dry_run:
        return paths
    directory.mkdir(parents=True, exist_ok=True)
    curves = curve_table(result)
    curves.to_csv(paths["csv"], index=False)
    parameters = pd.DataFrame(
        [
            {"parameter": key, "value": value, "standard_error": result.parameter_uncertainties.get(key)}
            for key, value in result.fitted_parameters.items()
        ]
    )
    with pd.ExcelWriter(paths["xlsx"], engine="openpyxl") as writer:
        curves.to_excel(writer, sheet_name="curves", index=False)
        parameters.to_excel(writer, sheet_name="parameters", index=False)
        pd.DataFrame([result.fit_statistics]).to_excel(writer, sheet_name="statistics", index=False)
        pd.DataFrame({"warning": result.warnings}).to_excel(writer, sheet_name="warnings", index=False)
        pd.DataFrame(
            [{"key": key, "value": json.dumps(value, default=str)} for key, value in result.metadata.items()]
        ).to_excel(writer, sheet_name="metadata", index=False)
    paths["json"].write_text(
        json.dumps(_summary(result), indent=2, allow_nan=False, default=str) + "\n", encoding="utf-8"
    )
    rows = [
        "# XPS fitting report",
        "",
        f"Model: `{result.configuration.get('name', 'unknown')}`",
        "",
        "## Fit statistics",
        "",
    ]
    rows.extend(f"- {key}: {value:.8g}" for key, value in result.fit_statistics.items())
    rows.extend(["", "## Parameters", ""])
    rows.extend(f"- {key}: {value:.8g}" for key, value in result.fitted_parameters.items())
    rows.extend(["", "## Warnings", ""])
    rows.extend(f"- {warning}" for warning in result.warnings or ["None"])
    paths["md"].write_text("\n".join(rows) + "\n", encoding="utf-8")
    figure = plot_fit(result)
    import matplotlib.pyplot as plt

    export_figure(figure, paths["png"], theme="angze_diagnostic", overwrite=True)
    plt.close(figure)
    return paths


def save_fit_bundle(
    result: FitResult,
    directory: str | Path,
    *,
    artifact: Mapping[str, Any] | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Path]:
    """Save a readable bundle, optionally with lifecycle provenance."""
    directory = Path(directory)
    paths = {
        "manifest": directory / "manifest.json",
        "curves": directory / "curves.csv",
        "metadata": directory / "metadata.json",
    }
    if directory.exists() and not directory.is_dir():
        raise NotADirectoryError(f"bundle path is not a directory: {directory}")
    _check_collisions(paths, overwrite=overwrite)
    if dry_run:
        return paths
    validate_result_integrity(result)
    directory.mkdir(parents=True, exist_ok=True)
    curve_table(result).to_csv(paths["curves"], index=False)
    paths["metadata"].write_text(
        json.dumps(_summary(result), indent=2, allow_nan=False, default=str) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "format": "xps-fitting-workbench-fit-bundle",
        "format_version": 1,
        "package_version": __version__,
        "files": {"curves": paths["curves"].name, "metadata": paths["metadata"].name},
        "integrity": {
            paths["curves"].name: sha256_file(paths["curves"]),
            paths["metadata"].name: sha256_file(paths["metadata"]),
        },
    }
    if artifact is not None:
        manifest["artifact"] = dict(artifact)
    paths["manifest"].write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return paths


def read_fit_bundle_manifest(directory: str | Path) -> dict[str, Any]:
    """Read and validate the base manifest header without loading arrays."""
    manifest_path = Path(directory) / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"fit bundle manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "xps-fitting-workbench-fit-bundle" or manifest.get("format_version") != 1:
        raise ValueError(f"unsupported fit bundle manifest: {manifest_path}")
    return manifest


def load_fit_bundle(directory: str | Path) -> FitResult:
    """Reload a directory created by :func:`save_fit_bundle`."""
    from .plotting.io import load_curve_result

    directory = Path(directory)
    manifest = read_fit_bundle_manifest(directory)

    def member(name: str) -> Path:
        candidate = (directory / str(manifest["files"][name])).resolve()
        if directory.resolve() not in candidate.parents:
            raise ValueError(f"fit bundle member escapes its directory: {candidate}")
        if not candidate.is_file():
            raise FileNotFoundError(f"fit bundle member is missing: {candidate}")
        expected_hash = manifest.get("integrity", {}).get(candidate.name)
        if expected_hash is not None and sha256_file(candidate) != expected_hash:
            raise ValueError(f"fit bundle member hash mismatch: {candidate}")
        return candidate

    result = load_curve_result(member("curves"), member("metadata"))
    validate_result_integrity(result)
    return result
