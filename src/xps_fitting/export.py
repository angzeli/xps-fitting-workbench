"""FitResult export bundle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .plotting import plot_fit
from .result import FitResult


def curve_table(result: FitResult) -> pd.DataFrame:
    data: dict[str, Any] = {"binding_energy_eV": result.energy, "raw_intensity": result.raw_intensity, "background": result.background}
    data.update({f"component:{label}": curve for label, curve in result.components.items()})
    data.update({"total_fit": result.total_fit, "residual": result.residual})
    return pd.DataFrame(data)


def export_result(result: FitResult, directory: str | Path, stem: str = "fit") -> dict[str, Path]:
    """Write XLSX, CSV, JSON, Markdown, and diagnostic PNG exports."""
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    paths = {suffix: directory / f"{stem}.{suffix}" for suffix in ("xlsx", "csv", "json", "md", "png")}
    curves = curve_table(result); curves.to_csv(paths["csv"], index=False)
    parameters = pd.DataFrame([{"parameter": key, "value": value, "standard_error": result.parameter_uncertainties.get(key)} for key, value in result.fitted_parameters.items()])
    with pd.ExcelWriter(paths["xlsx"], engine="openpyxl") as writer:
        curves.to_excel(writer, sheet_name="curves", index=False)
        parameters.to_excel(writer, sheet_name="parameters", index=False)
        pd.DataFrame([result.fit_statistics]).to_excel(writer, sheet_name="statistics", index=False)
        pd.DataFrame({"warning": result.warnings}).to_excel(writer, sheet_name="warnings", index=False)
        pd.DataFrame([{"key": key, "value": json.dumps(value, default=str)} for key, value in result.metadata.items()]).to_excel(writer, sheet_name="metadata", index=False)
    complete = result.to_dict()
    summary = {key: complete[key] for key in ("configuration", "fitted_parameters", "parameter_uncertainties", "fit_statistics", "warnings", "metadata", "convergence", "software_versions")}
    paths["json"].write_text(json.dumps(summary, indent=2, allow_nan=False, default=str) + "\n", encoding="utf-8")
    rows = ["# XPS fitting report", "", f"Model: `{result.configuration.get('name', 'unknown')}`", "", "## Fit statistics", ""]
    rows.extend(f"- {key}: {value:.8g}" for key, value in result.fit_statistics.items())
    rows.extend(["", "## Parameters", ""]); rows.extend(f"- {key}: {value:.8g}" for key, value in result.fitted_parameters.items())
    rows.extend(["", "## Warnings", ""]); rows.extend(f"- {warning}" for warning in result.warnings or ["None"])
    paths["md"].write_text("\n".join(rows) + "\n", encoding="utf-8")
    figure = plot_fit(result, paths["png"])
    import matplotlib.pyplot as plt
    plt.close(figure)
    return paths
