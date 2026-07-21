"""Labels and compact statistical annotations."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.text import Annotation, Text

from ..result import FitResult
from .themes import PlotTheme

PDI_H_C1S_LABELS = {
    "aromatic_C-C_C=C": "Aromatic C=C/C–C",
    "C-N_C-Cl": "C–N/C–Cl",
    "imide_N-C=O": "Imide N–C=O",
    "acid_O-C=O": "Carboxylic O–C=O",
    "pi-pi_star": r"$\pi$–$\pi^*$ satellite",
}


def statistics_text(result: FitResult) -> str:
    parts = []
    for key, label in (("aicc", "AICc"), ("bic", "BIC"), ("reduced_chi_square", r"$\chi_\nu^2$")):
        if key in result.fit_statistics:
            parts.append(f"{label} = {result.fit_statistics[key]:.3g}")
    return "\n".join(parts)


def annotate_peak_positions(
    axis: Axes,
    result: FitResult,
    displayed_components: Mapping[str, np.ndarray],
    component_colours: Mapping[str, str],
    theme: PlotTheme,
    *,
    precision: int = 1,
    include_unit: bool = True,
    leaders: bool = True,
    offsets: Mapping[str, tuple[float, float]] | None = None,
    include_negligible: bool = False,
    obstacles: tuple[Artist, ...] = (),
) -> list[Annotation]:
    """Annotate fitted centres above displayed component apices."""
    if isinstance(precision, bool) or not isinstance(precision, int) or precision < 0:
        raise ValueError("peak-position precision must be a non-negative integer")
    manual_offsets = dict(offsets or {})
    for label, offset in manual_offsets.items():
        try:
            offset_x, offset_y = offset
        except (TypeError, ValueError) as exc:
            raise ValueError(f"peak annotation offset for {label!r} must contain two finite values") from exc
        if not all(np.isfinite(value) for value in (offset_x, offset_y)):
            raise ValueError(f"peak annotation offset for {label!r} must contain two finite values")

    if not displayed_components:
        return []
    source_maximum = max(
        (float(np.nanmax(np.abs(np.asarray(result.components[label])))) for label in displayed_components),
        default=0.0,
    )
    candidates = []
    for label, displayed_curve in displayed_components.items():
        centre = result.fitted_parameters.get(f"{label}.centre")
        if centre is None or not np.isfinite(centre):
            continue
        source_curve = np.asarray(result.components[label])
        amplitude = float(np.nanmax(np.abs(source_curve)))
        if (
            not include_negligible
            and source_maximum > 0
            and amplitude < theme.negligible_component_fraction * source_maximum
        ):
            continue
        displayed_curve = np.asarray(displayed_curve)
        apex_index = int(np.nanargmax(displayed_curve))
        candidates.append((float(centre), label, float(displayed_curve[apex_index])))

    x_lower, x_upper = sorted(axis.get_xlim())
    x_span = max(x_upper - x_lower, np.finfo(float).eps)
    collision_distance = theme.peak_annotation_collision_fraction * x_span
    x_margin = 0.015 * x_span
    annotations: list[Annotation] = []
    previous_centre: float | None = None
    stagger_level = 0
    for centre, label, apex_height in sorted(candidates):
        if previous_centre is not None and abs(centre - previous_centre) < collision_distance:
            stagger_level += 1
        else:
            stagger_level = 0
        previous_centre = centre
        manual_x, manual_y = manual_offsets.get(label, (0.0, 0.0))
        anchor_x = min(max(centre, x_lower + x_margin), x_upper - x_margin)
        text = f"{centre:.{precision}f}" + (" eV" if include_unit else "")
        colour = component_colours[label]
        arrowprops = None
        if leaders:
            arrowprops = {
                "arrowstyle": "-",
                "color": colour,
                "linewidth": theme.peak_annotation_leader_width,
                "shrinkA": 2,
                "shrinkB": 2,
            }
        annotation = axis.annotate(
            text,
            xy=(anchor_x, apex_height),
            xytext=(
                manual_x,
                theme.peak_annotation_offset_points + stagger_level * theme.peak_annotation_stagger_points + manual_y,
            ),
            textcoords="offset points",
            ha="center",
            va="bottom",
            color=colour,
            fontsize=theme.peak_annotation_size,
            fontweight="bold",
            arrowprops=arrowprops,
            annotation_clip=True,
            zorder=9,
        )
        annotation.set_clip_on(True)
        annotation.set_gid(f"peak-position:{label}")
        annotation._xps_component_label = label
        annotation._xps_fitted_centre = centre
        annotation._xps_stagger_level = stagger_level
        annotations.append(annotation)
    _keep_annotations_inside_axes(axis, annotations, obstacles)
    return annotations


def _keep_annotations_inside_axes(
    axis: Axes,
    annotations: list[Annotation],
    obstacles: tuple[Artist, ...],
) -> None:
    """Keep annotation text inside the axes and clear of framed legends."""
    if not annotations:
        return
    canvas = axis.figure.canvas
    padding = 3.0
    points_per_pixel = 72.0 / axis.figure.dpi
    for _ in range(3):
        canvas.draw()
        renderer = canvas.get_renderer()
        axes_box = axis.get_window_extent(renderer)
        obstacle_boxes = [artist.get_window_extent(renderer) for artist in obstacles if artist.get_visible()]
        adjusted = False
        for annotation in annotations:
            box = Text.get_window_extent(annotation, renderer)
            shift_x = 0.0
            shift_y = 0.0
            for obstacle_box in obstacle_boxes:
                if not box.overlaps(obstacle_box):
                    continue
                shift_right = obstacle_box.x1 - box.x0 + padding
                shift_left = obstacle_box.x0 - box.x1 - padding
                if box.x1 + shift_right <= axes_box.x1 - padding:
                    shift_x += shift_right
                elif box.x0 + shift_left >= axes_box.x0 + padding:
                    shift_x += shift_left
                else:
                    shift_y += obstacle_box.y0 - box.y1 - padding
            shifted_x0 = box.x0 + shift_x
            shifted_x1 = box.x1 + shift_x
            shifted_y0 = box.y0 + shift_y
            shifted_y1 = box.y1 + shift_y
            shift_x += max(axes_box.x0 + padding - shifted_x0, 0.0)
            shift_x += min(axes_box.x1 - padding - shifted_x1, 0.0)
            shift_y += max(axes_box.y0 + padding - shifted_y0, 0.0)
            shift_y += min(axes_box.y1 - padding - shifted_y1, 0.0)
            if shift_x or shift_y:
                current_x, current_y = annotation.get_position()
                annotation.set_position(
                    (
                        current_x + shift_x * points_per_pixel,
                        current_y + shift_y * points_per_pixel,
                    )
                )
                adjusted = True
        if not adjusted:
            break
