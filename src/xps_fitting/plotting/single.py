"""Publication-quality rendering of one immutable FitResult."""

from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator, ScalarFormatter

from ..result import FitResult
from .annotations import PDI_H_C1S_LABELS, annotate_peak_positions, statistics_text
from .palettes import component_colour
from .palettes import component_style as monochrome_component_style
from .themes import PlotTheme, apply_vertical_headroom, style_axes, style_legend, theme_context
from .validation import validate_result_curves

DISPLAY_MODES = {"lines", "filled", "filled_to_background", "stacked_visualisation", "outline_only", "hidden"}


def plot_xps_fit(
    result: FitResult,
    *,
    theme: str | PlotTheme = "angze_publication",
    core_level: str | None = None,
    component_display_mode: str = "filled",
    component_style_mode: str | None = None,
    component_style: str | None = None,
    show_residual: bool = False,
    show_residual_zero: bool | None = None,
    show_baseline: bool = False,
    peak_labels: bool = False,
    show_peak_positions: bool = False,
    peak_position_precision: int = 1,
    peak_position_unit: bool = True,
    peak_annotation_leaders: bool = True,
    peak_annotation_offsets: Mapping[str, tuple[float, float]] | None = None,
    annotate_negligible_components: bool = False,
    annotate_hidden_components: bool = False,
    area_percentages: bool = False,
    fit_statistics: bool = False,
    intensity_units: str = "a.u.",
    y_label: str | None = None,
    scale_factor: float = 1.0,
    hide_y_tick_labels: bool = False,
    x_limits: tuple[float, float] | None = None,
    tick_spacing: float | None = None,
    sample_label: str | None = None,
    panel_label: str | None = None,
    legend_order: Sequence[str] | None = None,
    label_map: Mapping[str, str] | None = None,
    component_colours: Mapping[str, str] | None = None,
    y_start: float | None = 0.0,
    title: str | None = None,
    fit_colour: str | None = None,
) -> tuple[Figure, Axes | np.ndarray]:
    """Render supplied curves without recalculation, interpolation, or mutation."""
    aliases = [("component_style_mode", component_style_mode), ("component_style", component_style)]
    supplied_aliases = [(name, value) for name, value in aliases if value is not None]
    if len({value for _, value in supplied_aliases}) > 1:
        raise ValueError("deprecated component display aliases disagree")
    mode = component_display_mode
    if supplied_aliases:
        name, alias_value = supplied_aliases[0]
        if component_display_mode != "filled" and component_display_mode != alias_value:
            raise ValueError(f"{name} conflicts with component_display_mode")
        warnings.warn(f"{name} is deprecated; use component_display_mode", DeprecationWarning, stacklevel=2)
        mode = alias_value
    if mode not in DISPLAY_MODES:
        raise ValueError(f"component display mode must be one of {sorted(DISPLAY_MODES)}")
    if not np.isfinite(scale_factor) or scale_factor <= 0:
        raise ValueError("scale_factor must be finite and positive")
    validate_result_curves(result)
    labels = dict(PDI_H_C1S_LABELS)
    labels.update(label_map or {})
    with theme_context(theme) as selected:
        if show_residual:
            height = selected.residual_height_ratio
            figure, axes = plt.subplots(
                2,
                1,
                figsize=selected.figure_size,
                sharex=True,
                layout="constrained",
                gridspec_kw={"height_ratios": [1 - height, height], "hspace": 0.05},
            )
            main, residual_axis = axes
        else:
            figure, main = plt.subplots(figsize=selected.figure_size, layout="constrained")
            axes, residual_axis = main, None
        energy = np.asarray(result.energy)
        background = np.asarray(result.background) / scale_factor
        raw = np.asarray(result.raw_intensity) / scale_factor
        total = np.asarray(result.total_fit) / scale_factor
        (raw_line,) = main.plot(
            energy,
            raw,
            linestyle="none",
            marker=selected.marker,
            markersize=selected.marker_size,
            markerfacecolor=selected.raw_face,
            markeredgecolor=selected.raw_edge,
            markeredgewidth=selected.marker_edge_width,
            label="Experimental",
            zorder=7,
        )
        main.plot(
            energy,
            background,
            selected.background_line_style,
            color="#555555",
            linewidth=selected.background_line_width,
            label="_nolegend_",
            zorder=2,
        )
        component_artists = {}
        displayed_components = {}
        annotation_colours = {}
        displayed_curves = [raw, background, total]
        cumulative = background.copy()
        total_component_area = sum(float(np.trapz(curve, energy)) for curve in result.components.values())
        for label, source_curve in result.components.items():
            curve = np.asarray(source_curve) / scale_factor
            colour = component_colour(label, dict(component_colours or {}))
            display_label = labels.get(label, label)
            if area_percentages and total_component_area:
                display_label += f" ({100 * float(np.trapz(source_curve, energy)) / total_component_area:.1f}%)"
            linestyle = monochrome_component_style(label) if selected.name == "monochrome_publication" else "-"
            if mode == "hidden":
                if annotate_hidden_components:
                    displayed_components[label] = background + curve
                    annotation_colours[label] = colour
                continue
            if mode == "stacked_visualisation":
                next_curve = cumulative + curve
                plotted = next_curve
                artist = main.fill_between(
                    energy, cumulative, next_curve, color=colour, alpha=selected.component_alpha, label=display_label
                )
                main.plot(
                    energy, next_curve, color=colour, linewidth=selected.component_line_width, linestyle=linestyle
                )
                cumulative = next_curve
            else:
                plotted = background + curve
                if mode in {"filled", "filled_to_background"}:
                    lower = background if mode == "filled_to_background" else np.zeros_like(curve)
                    artist = main.fill_between(
                        energy, lower, plotted, color=colour, alpha=selected.component_alpha, label=display_label
                    )
                    main.plot(
                        energy, plotted, color=colour, linewidth=selected.component_line_width, linestyle=linestyle
                    )
                else:
                    (artist,) = main.plot(
                        energy,
                        plotted,
                        color=colour,
                        linewidth=selected.component_line_width,
                        linestyle=linestyle,
                        label=display_label,
                    )
            component_artists[label] = artist
            displayed_components[label] = plotted
            annotation_colours[label] = colour
            displayed_curves.append(plotted)
            if peak_labels:
                index = int(np.argmax(source_curve))
                main.annotate(
                    display_label.split(" (")[0],
                    (energy[index], plotted[index]),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha="center",
                    fontsize=selected.tick_label_size,
                )
        (total_line,) = main.plot(
            energy,
            total,
            color=fit_colour or selected.fit_colour,
            linewidth=selected.fit_line_width,
            label="Total fit",
            zorder=6,
        )
        if show_baseline:
            main.axhline(0, color="#777777", linewidth=0.7, zorder=0)
        ylabel = y_label or f"Intensity ({intensity_units})"
        if scale_factor != 1:
            ylabel += f" × {scale_factor:g}"
        main.set_ylabel(ylabel, labelpad=selected.axis_padding)
        if hide_y_tick_labels:
            main.tick_params(labelleft=False)
        if x_limits:
            main.set_xlim(x_limits)
        if selected.invert_binding_energy and not main.xaxis_inverted():
            main.invert_xaxis()
        if tick_spacing:
            main.xaxis.set_major_locator(MultipleLocator(tick_spacing))
        main.yaxis.set_major_formatter(ScalarFormatter(useMathText=True))
        visible_minimum = min(float(np.min(curve)) for curve in displayed_curves)
        visible_maximum = max(float(np.max(curve)) for curve in displayed_curves)
        apply_vertical_headroom(
            main,
            selected,
            minimum=visible_minimum,
            maximum=visible_maximum,
            bottom=y_start,
        )
        style_axes(main, selected)
        if title and selected.show_title:
            main.set_title(title, fontsize=selected.title_size, fontweight="bold")
        if sample_label:
            main.text(
                0.0,
                1.02,
                sample_label,
                transform=main.transAxes,
                va="bottom",
                fontsize=selected.title_size,
                fontweight="bold",
            )
        if core_level:
            main.text(
                1.0,
                1.02,
                core_level,
                transform=main.transAxes,
                va="bottom",
                ha="right",
                fontsize=selected.core_level_size,
            )
        if panel_label:
            main.text(
                -0.12,
                1.02,
                selected.panel_label_template.format(label=panel_label),
                transform=main.transAxes,
                va="bottom",
                fontsize=selected.title_size,
                fontweight="bold",
            )
        if show_peak_positions:
            annotate_peak_positions(
                main,
                result,
                displayed_components,
                annotation_colours,
                selected,
                precision=peak_position_precision,
                include_unit=peak_position_unit,
                leaders=peak_annotation_leaders,
                offsets=peak_annotation_offsets,
                include_negligible=annotate_negligible_components,
            )
        if fit_statistics:
            main.text(
                0.97,
                0.96,
                statistics_text(result),
                transform=main.transAxes,
                va="top",
                ha="right",
                fontsize=selected.tick_label_size,
            )
        ordered = [raw_line, total_line]
        if legend_order:
            component_sequence = [component_artists[label] for label in legend_order if label in component_artists]
        else:
            component_sequence = list(component_artists.values())
        handles = ordered + component_sequence
        legend = main.legend(
            handles=handles,
            loc="upper left",
            frameon=selected.legend_frame,
            fancybox=selected.legend_fancybox,
            framealpha=selected.legend_frame_alpha,
            facecolor=selected.legend_face_colour,
            edgecolor=selected.legend_edge_colour,
            labelspacing=selected.legend_spacing,
            prop={"size": selected.legend_font_size, "weight": selected.legend_font_weight},
        )
        style_legend(legend, selected)
        if residual_axis is not None:
            residual_axis.plot(energy, np.asarray(result.residual) / scale_factor, color="#222222", linewidth=1)
            zero = selected.residual_zero_line if show_residual_zero is None else show_residual_zero
            if zero:
                residual_axis.axhline(0, color="#777777", linewidth=0.7)
            residual_axis.set_ylabel("Residual", labelpad=selected.axis_padding)
            residual_axis.set_xlabel("Binding energy (eV)", labelpad=selected.axis_padding)
            if tick_spacing:
                residual_axis.xaxis.set_major_locator(MultipleLocator(tick_spacing))
            style_axes(residual_axis, selected)
        else:
            main.set_xlabel("Binding energy (eV)", labelpad=selected.axis_padding)
    return figure, axes
