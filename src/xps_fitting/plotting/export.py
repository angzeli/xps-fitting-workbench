"""Controlled publication-figure exports."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from matplotlib.figure import Figure

from .themes import PlotTheme, load_theme

SUPPORTED_FORMATS = {"png", "svg", "pdf", "tiff", "tif"}


def export_figure(
    figure: Figure, output: str | Path, *, formats: Iterable[str] | None = None,
    theme: str | PlotTheme = "angze_publication", transparent: bool | None = None,
    metadata: dict[str, str] | None = None, tight: bool = True,
) -> dict[str, Path]:
    selected = load_theme(theme)
    output = Path(output)
    requested = [output.suffix.lstrip(".").lower()] if formats is None and output.suffix else list(formats or ("png",))
    stem = output.with_suffix("") if output.suffix else output
    paths: dict[str, Path] = {}
    for format_name in requested:
        format_name = format_name.lower()
        if format_name not in SUPPORTED_FORMATS:
            raise ValueError(f"unsupported figure format {format_name!r}")
        path = stem.with_suffix(f".{format_name}"); path.parent.mkdir(parents=True, exist_ok=True)
        is_vector = format_name in {"svg", "pdf"}
        alpha = transparent if transparent is not None else (selected.vector_transparent if is_vector else selected.raster_transparent)
        figure.savefig(path, format=format_name, dpi=selected.dpi, transparent=alpha, bbox_inches="tight" if tight else None, metadata=metadata if format_name in {"png", "svg", "pdf"} else None)
        paths[format_name] = path
    return paths
