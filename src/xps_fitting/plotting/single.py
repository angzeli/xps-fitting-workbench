"""Publication-quality rendering of one immutable FitResult."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator, ScalarFormatter
import numpy as np

from ..result import FitResult
from .annotations import PDI_H_C1S_LABELS, statistics_text
from .palettes import component_colour, component_style, core_level_colour
from .themes import PlotTheme, theme_context
from .validation import validate_result_curves

DISPLAY_MODES = {"lines", "filled", "filled_to_background", "stacked_visualisation", "outline_only", "hidden"}


def plot_xps_fit(
    result: FitResult, *, theme: str | PlotTheme = "angze_publication", core_level: str | None = None,
    component_style_mode: str = "filled", component_style: str | None = None,
    show_residual: bool = False, show_residual_zero: bool | None = None,
    show_baseline: bool = False, peak_labels: bool = False, area_percentages: bool = False,
    fit_statistics: bool = False, intensity_units: str = "a.u.", y_label: str | None = None,
    scale_factor: float = 1.0, hide_y_tick_labels: bool = False,
    x_limits: tuple[float, float] | None = None, tick_spacing: float | None = None,
    sample_label: str | None = None, panel_label: str | None = None,
    legend_order: Sequence[str] | None = None, label_map: Mapping[str, str] | None = None,
    component_colours: Mapping[str, str] | None = None, y_start: float | None = 0.0,
    title: str | None = None,
) -> tuple[Figure, Axes | np.ndarray]:
    """Render supplied curves without recalculation, interpolation, or mutation."""
    mode = component_style or component_style_mode
    if mode not in DISPLAY_MODES:
        raise ValueError(f"component display mode must be one of {sorted(DISPLAY_MODES)}")
    if not np.isfinite(scale_factor) or scale_factor <= 0:
        raise ValueError("scale_factor must be finite and positive")
    validate_result_curves(result)
    labels = dict(PDI_H_C1S_LABELS); labels.update(label_map or {})
    with theme_context(theme) as selected:
        if show_residual:
            height = selected.residual_height_ratio
            figure, axes = plt.subplots(2, 1, figsize=selected.figure_size, sharex=True, layout="constrained", gridspec_kw={"height_ratios": [1 - height, height], "hspace": 0.05})
            main, residual_axis = axes
        else:
            figure, main = plt.subplots(figsize=selected.figure_size, layout="constrained")
            axes, residual_axis = main, None
        energy = np.asarray(result.energy); background = np.asarray(result.background) / scale_factor
        raw = np.asarray(result.raw_intensity) / scale_factor; total = np.asarray(result.total_fit) / scale_factor
        raw_line, = main.plot(energy, raw, linestyle="none", marker=selected.marker, markersize=selected.marker_size, markerfacecolor=selected.raw_face, markeredgecolor=selected.raw_edge, markeredgewidth=0.7, label="Experimental", zorder=5)
        background_line, = main.plot(energy, background, selected.background_line_style, color="#555555", linewidth=selected.background_line_width, label="Background", zorder=2)
        component_artists = {}
        cumulative = background.copy()
        total_component_area = sum(float(np.trapz(curve, energy)) for curve in result.components.values())
        for label, source_curve in result.components.items():
            curve = np.asarray(source_curve) / scale_factor
            colour = component_colour(label, dict(component_colours or {}))
            display_label = labels.get(label, label)
            if area_percentages and total_component_area:
                display_label += f" ({100 * float(np.trapz(source_curve, energy)) / total_component_area:.1f}%)"
            linestyle = component_style_fn(label) if selected.name == "monochrome_publication" else "-"
            if mode == "hidden":
                continue
            if mode == "stacked_visualisation":
                next_curve = cumulative + curve
                plotted = next_curve
                artist = main.fill_between(energy, cumulative, next_curve, color=colour, alpha=selected.component_alpha, label=display_label)
                main.plot(energy, next_curve, color=colour, linewidth=selected.component_line_width, linestyle=linestyle)
                cumulative = next_curve
            else:
                plotted = background + curve
                if mode in {"filled", "filled_to_background"}:
                    lower = background if mode == "filled_to_background" else np.zeros_like(curve)
                    artist = main.fill_between(energy, lower, plotted, color=colour, alpha=selected.component_alpha, label=display_label)
                    main.plot(energy, plotted, color=colour, linewidth=selected.component_line_width, linestyle=linestyle)
                else:
                    artist, = main.plot(energy, plotted, color=colour, linewidth=selected.component_line_width, linestyle=linestyle, label=display_label)
            component_artists[label] = artist
            if peak_labels:
                index = int(np.argmax(source_curve)); main.annotate(display_label.split(" (")[0], (energy[index], plotted[index]), xytext=(0, 5), textcoords="offset points", ha="center", fontsize=selected.tick_label_size)
        total_line, = main.plot(energy, total, color=core_level_colour(core_level or result.configuration.get("region", "")), linewidth=selected.fit_line_width, label="Total fit", zorder=6)
        if show_baseline:
            main.axhline(0, color="#777777", linewidth=0.7, zorder=0)
        ylabel = y_label or f"Intensity ({intensity_units})"
        if scale_factor != 1:
            ylabel += f" × {scale_factor:g}"
        main.set_ylabel(ylabel, labelpad=selected.axis_padding)
        main.tick_params(top=selected.top_spine, right=selected.right_spine)
        main.spines["top"].set_visible(selected.top_spine); main.spines["right"].set_visible(selected.right_spine)
        if y_start is not None:
            main.set_ylim(bottom=y_start)
        if hide_y_tick_labels:
            main.tick_params(labelleft=False)
        if x_limits:
            main.set_xlim(x_limits)
        if selected.invert_binding_energy and not main.xaxis_inverted():
            main.invert_xaxis()
        if tick_spacing:
            main.xaxis.set_major_locator(MultipleLocator(tick_spacing))
        main.yaxis.set_major_formatter(ScalarFormatter(useMathText=True))
        if title and selected.show_title:
            main.set_title(title)
        if sample_label:
            main.text(0.03, 0.96, sample_label, transform=main.transAxes, va="top", fontweight="bold")
        if core_level:
            main.text(0.97, 0.96, core_level, transform=main.transAxes, va="top", ha="right")
        if panel_label:
            main.text(0.01, 1.02, selected.panel_label_template.format(label=panel_label), transform=main.transAxes, va="bottom", fontweight="bold")
        if fit_statistics:
            main.text(0.97, 0.72, statistics_text(result), transform=main.transAxes, va="top", ha="right", fontsize=selected.tick_label_size)
        ordered = [raw_line, total_line, background_line]
        if legend_order:
            component_sequence = [component_artists[label] for label in legend_order if label in component_artists]
        else:
            component_sequence = list(component_artists.values())
        handles = ordered + component_sequence
        main.legend(handles=handles, frameon=selected.legend_frame, labelspacing=selected.legend_spacing)
        if residual_axis is not None:
            residual_axis.plot(energy, np.asarray(result.residual) / scale_factor, color="#222222", linewidth=1)
            zero = selected.residual_zero_line if show_residual_zero is None else show_residual_zero
            if zero:
                residual_axis.axhline(0, color="#777777", linewidth=0.7)
            residual_axis.set_ylabel("Residual", labelpad=selected.axis_padding)
            residual_axis.set_xlabel("Binding energy (eV)", labelpad=selected.axis_padding)
            residual_axis.spines["top"].set_visible(False); residual_axis.spines["right"].set_visible(selected.right_spine)
            if tick_spacing:
                residual_axis.xaxis.set_major_locator(MultipleLocator(tick_spacing))
        else:
            main.set_xlabel("Binding energy (eV)", labelpad=selected.axis_padding)
    return figure, axes


component_style_fn = component_style
