"""Controlled publication-figure exports."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from matplotlib.figure import Figure

from .themes import (
    SUPPORTED_OUTPUT_FORMATS,
    PlotTheme,
    _apply_figure_font_family,
    load_theme,
    theme_context,
    validate_theme,
)

SUPPORTED_FORMATS = SUPPORTED_OUTPUT_FORMATS


def export_figure(
    figure: Figure,
    output: str | Path,
    *,
    formats: Iterable[str] | None = None,
    theme: str | PlotTheme = "angze_publication",
    transparent: bool | None = None,
    metadata: dict[str, str] | None = None,
    tight: bool = False,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Path]:
    selected = load_theme(theme)
    output = Path(output)
    requested = [output.suffix.lstrip(".").lower()] if formats is None and output.suffix else list(formats or ("png",))
    requested = list(dict.fromkeys(item.lower() for item in requested))
    if not requested:
        raise ValueError("at least one output format is required")
    try:
        validate_theme(selected, output_formats=tuple(requested))
    except ValueError as exc:
        raise ValueError(f"{exc}. No file was written.") from exc
    stem = output.with_suffix("") if output.suffix else output
    paths = {format_name: stem.with_suffix(f".{format_name}") for format_name in requested}
    collisions = [path for path in paths.values() if path.exists()]
    if collisions and not overwrite:
        names = ", ".join(str(path) for path in collisions)
        raise FileExistsError(f"output already exists: {names}; pass overwrite=True to replace it")
    if dry_run:
        return paths
    with theme_context(selected):
        _apply_figure_font_family(figure, selected.font_family)
        for format_name, path in paths.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            is_vector = format_name == "pdf"
            alpha = (
                transparent
                if transparent is not None
                else (selected.vector_transparent if is_vector else selected.raster_transparent)
            )
            figure.savefig(
                path,
                format=format_name,
                dpi=selected.dpi,
                transparent=alpha,
                bbox_inches="tight" if tight else None,
                metadata=metadata,
            )
    return paths
