"""Compatibility rendering for the original Phase 1 diagnostic view."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from ..result import FitResult
from .annotations import PDI_H_C1S_LABELS
from .export import export_figure
from .themes import _apply_figure_font_family, load_theme


def plot_fit(result: FitResult, path: str | Path | None = None, *, residual_panel: bool = True) -> Figure:
    """Render stored fit curves in the legacy diagnostic artist hierarchy.

    Binding energy is displayed in eV and inverted. Intensity and residuals retain
    their source-defined scale; providing ``path`` exports after rendering without
    changing the returned figure or the input result.
    """
    figure, axes = plt.subplots(
        2 if residual_panel else 1, 1, sharex=True, gridspec_kw={"height_ratios": [3, 1]} if residual_panel else None
    )
    main = axes[0] if residual_panel else axes
    main.plot(result.energy, result.raw_intensity, ".", color="0.35", label="Experimental")
    main.plot(result.energy, result.background, "--", color="0.5", label="_nolegend_")
    for label, curve in result.components.items():
        main.plot(result.energy, result.background + curve, lw=1, label=PDI_H_C1S_LABELS.get(label, label))
    main.plot(result.energy, result.total_fit, color="black", label="Total fit")
    main.legend()
    main.set_ylabel("Intensity")
    main.invert_xaxis()
    if residual_panel:
        axes[1].axhline(0, color="0.5", lw=0.8)
        axes[1].plot(result.energy, result.residual, color="black")
        axes[1].set_ylabel("Residual")
        axes[1].set_xlabel("Binding energy (eV)")
    else:
        main.set_xlabel("Binding energy (eV)")
    figure.tight_layout()
    theme = load_theme("angze_diagnostic")
    _apply_figure_font_family(figure, theme.font_family)
    if path is not None:
        export_figure(figure, path, theme=theme, tight=False)
    return figure
