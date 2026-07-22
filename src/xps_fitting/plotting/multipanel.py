"""Aligned XPS series and core-level panels."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.artist import Artist
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator

from ..result import FitResult
from .annotations import PDI_H_C1S_LABELS, annotate_peak_positions
from .palettes import component_colour
from .themes import (
    PlotTheme,
    apply_vertical_headroom,
    figure_size_preset,
    fitted_region_y_limits,
    load_theme,
    style_axes,
    style_legend,
    theme_context,
)
from .validation import validate_result_curves


def plot_xps_series(
    results: Sequence[FitResult],
    *,
    theme: str | PlotTheme = "angze_publication",
    layout: str = "horizontal",
    nrows: int | None = None,
    ncols: int | None = None,
    sharex: bool = True,
    sharey: bool = False,
    independent_y: bool = True,
    sample_labels: Sequence[str] | None = None,
    panel_labels: Sequence[str] | None = None,
    core_levels: Sequence[str] | str | None = None,
    shared_legend: bool = True,
    show_components: bool | Sequence[bool] = True,
    show_residual: bool = False,
    x_limits: tuple[float, float] | None = None,
    tick_spacing: float | None = None,
    intensity_offsets: Sequence[float] | None = None,
    normalised: bool = False,
    spacing: tuple[float, float] = (0.08, 0.12),
    label_map: Mapping[str, str] | None = None,
    show_peak_positions: bool = False,
    peak_position_precision: int = 1,
    peak_position_unit: bool = True,
    peak_annotation_leaders: bool = True,
    peak_annotation_offsets: Mapping[str, tuple[float, float]] | None = None,
    peak_annotations: Mapping[str, Mapping[str, object]] | None = None,
    annotate_negligible_components: bool = False,
    annotate_hidden_components: bool = False,
) -> tuple[Figure, np.ndarray]:
    """Plot related immutable results on an aligned grid."""
    if not results:
        raise ValueError("at least one result is required")
    for result in results:
        validate_result_curves(result)
    count = len(results)
    if nrows is None or ncols is None:
        nrows, ncols = (1, count) if layout == "horizontal" else (count, 1)
    if nrows * ncols < count:
        raise ValueError("panel grid is too small")
    samples = list(
        sample_labels
        or [str(result.metadata.get("sample_name", f"Sample {index + 1}")) for index, result in enumerate(results)]
    )
    panels = list(panel_labels or [chr(97 + index) for index in range(count)])
    offsets = list(intensity_offsets or [0.0] * count)
    components_visible = [show_components] * count if isinstance(show_components, bool) else list(show_components)
    levels = [core_levels] * count if isinstance(core_levels, str) or core_levels is None else list(core_levels)
    if not all(len(values) == count for values in (samples, panels, offsets, components_visible, levels)):
        raise ValueError("per-panel options must match the number of results")
    labels = dict(PDI_H_C1S_LABELS)
    labels.update(label_map or {})
    base_theme = load_theme(theme)
    plotting_theme = base_theme.for_multipanel() if count > 1 else base_theme
    with theme_context(plotting_theme) as selected:
        height_multiplier = 1.28 if show_residual else 1.0
        if count == 1:
            figure_size = selected.figure_size
        elif selected.name == "presentation":
            width, height = figure_size_preset("presentation")
            figure_size = (width, height * nrows * height_multiplier)
        elif ncols > 1:
            width, height = figure_size_preset("double-column")
            figure_size = (width, height * nrows * height_multiplier)
        else:
            width, height = figure_size_preset("one-and-a-half-column")
            figure_size = (width, height * nrows * height_multiplier)
        figure, axes = plt.subplots(
            nrows, ncols, squeeze=False, sharex=sharex, sharey=sharey, figsize=figure_size, layout="constrained"
        )
        flat = axes.ravel()
        legend_handles: dict[str, object] = {}
        for index, (result, axis) in enumerate(zip(results, flat)):
            offset = offsets[index]
            energy = np.asarray(result.energy)
            axis.plot(
                energy,
                np.asarray(result.raw_intensity) + offset,
                linestyle="none",
                marker=selected.marker,
                markersize=selected.marker_size,
                markerfacecolor=selected.raw_face,
                markeredgecolor=selected.raw_edge,
                markeredgewidth=selected.marker_edge_width,
                label="Experimental",
                zorder=7,
            )
            displayed_curves = [np.asarray(result.raw_intensity) + offset, np.asarray(result.background) + offset]
            axis.plot(
                energy,
                np.asarray(result.background) + offset,
                selected.background_line_style,
                color="#555555",
                linewidth=selected.background_line_width,
                label="_nolegend_",
            )
            displayed_components = {}
            annotation_colours = {}
            for label, curve in result.components.items():
                colour = component_colour(label)
                displayed_component = np.asarray(result.background) + np.asarray(curve) + offset
                if components_visible[index]:
                    axis.fill_between(
                        energy,
                        np.asarray(result.background) + offset,
                        displayed_component,
                        color=colour,
                        alpha=selected.component_alpha,
                        label=labels.get(label, label),
                    )
                    axis.plot(
                        energy,
                        displayed_component,
                        color=colour,
                        linewidth=selected.component_line_width,
                    )
                    displayed_curves.append(displayed_component)
                if components_visible[index] or annotate_hidden_components:
                    displayed_components[label] = displayed_component
                    annotation_colours[label] = colour
            level = levels[index] or result.configuration.get("region", "")
            displayed_total = np.asarray(result.total_fit) + offset
            displayed_curves.append(displayed_total)
            axis.plot(
                energy,
                displayed_total,
                color=selected.fit_colour,
                linewidth=selected.fit_line_width,
                label="Total fit",
                zorder=6,
            )
            panel_title = f"{selected.panel_label_template.format(label=panels[index])} {samples[index]}"
            axis.set_title(
                panel_title,
                loc="left",
                pad=selected.title_padding,
                fontsize=selected.title_size,
                fontweight="bold",
            )
            if level:
                axis.set_title(
                    level,
                    loc="right",
                    pad=selected.title_padding,
                    fontsize=selected.core_level_size,
                )
            disclosures = []
            if normalised:
                disclosures.append("normalised")
            if offset:
                disclosures.append(f"offset {offset:+g}")
            if disclosures:
                axis.text(
                    0.03,
                    0.86,
                    "; ".join(disclosures),
                    transform=axis.transAxes,
                    va="top",
                    fontsize=selected.tick_label_size,
                )
            if x_limits:
                axis.set_xlim(x_limits)
            if selected.invert_binding_energy and not axis.xaxis_inverted():
                axis.invert_xaxis()
            if tick_spacing:
                axis.xaxis.set_major_locator(MultipleLocator(tick_spacing))
            if independent_y:
                axis.set_ylim(
                    fitted_region_y_limits(
                        np.asarray(result.raw_intensity) + offset,
                        np.asarray(result.background) + offset,
                        displayed_total,
                        selected,
                    )
                )
            else:
                apply_vertical_headroom(
                    axis,
                    selected,
                    minimum=min(float(np.min(curve)) for curve in displayed_curves),
                    maximum=max(float(np.max(curve)) for curve in displayed_curves),
                    bottom=0.0,
                )
            style_axes(axis, selected)
            if index % ncols == 0:
                axis.set_ylabel("Normalised intensity" if normalised else "Intensity (a.u.)")
            if index // ncols == nrows - 1:
                axis.set_xlabel("Binding energy (eV)")
            legend_obstacles: tuple[Artist, ...] = ()
            if not shared_legend:
                legend = axis.legend(
                    frameon=selected.legend_frame,
                    fancybox=selected.legend_fancybox,
                    framealpha=selected.legend_frame_alpha,
                    facecolor=selected.legend_face_colour,
                    edgecolor=selected.legend_edge_colour,
                    labelspacing=selected.legend_spacing,
                    prop={"size": selected.legend_font_size, "weight": selected.legend_font_weight},
                )
                style_legend(legend, selected)
                legend_obstacles = (legend,)
            else:
                handles, handle_labels = axis.get_legend_handles_labels()
                for handle, handle_label in zip(handles, handle_labels):
                    legend_handles.setdefault(handle_label, handle)
            if show_peak_positions:
                annotate_peak_positions(
                    axis,
                    result,
                    displayed_components,
                    annotation_colours,
                    selected,
                    precision=peak_position_precision,
                    include_unit=peak_position_unit,
                    leaders=peak_annotation_leaders,
                    offsets=peak_annotation_offsets,
                    annotation_options=peak_annotations,
                    include_negligible=annotate_negligible_components,
                    clearance_curves=displayed_curves,
                    obstacles=legend_obstacles,
                )
        for axis in flat[count:]:
            axis.set_visible(False)
        if shared_legend and legend_handles:
            legend = figure.legend(
                list(legend_handles.values()),
                list(legend_handles),
                loc="outside lower center",
                ncol=min(4, len(legend_handles)),
                frameon=selected.legend_frame,
                fancybox=selected.legend_fancybox,
                framealpha=selected.legend_frame_alpha,
                facecolor=selected.legend_face_colour,
                edgecolor=selected.legend_edge_colour,
                prop={"size": selected.legend_font_size, "weight": selected.legend_font_weight},
            )
            style_legend(legend, selected)
        figure.get_layout_engine().set(w_pad=spacing[0], h_pad=spacing[1])
        if show_residual:
            # Residuals remain available as a compact inset and use the exact Phase 1 arrays.
            for result, axis, offset in zip(results, flat, offsets):
                inset = axis.inset_axes([0.12, -0.34, 0.82, 0.22])
                inset.plot(result.energy, result.residual, color="#222222", linewidth=0.8)
                inset.axhline(0, color="#777777", linewidth=0.6)
                inset.set_ylabel("res.", fontsize=selected.tick_label_size)
                inset.tick_params(labelsize=selected.tick_label_size)
                style_axes(inset, selected)
                if x_limits:
                    inset.set_xlim(x_limits)
                if selected.invert_binding_energy and not inset.xaxis_inverted():
                    inset.invert_xaxis()
        return figure, axes


plot_core_level_panel = plot_xps_series
