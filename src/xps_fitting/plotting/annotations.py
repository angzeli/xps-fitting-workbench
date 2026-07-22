"""Labels and compact statistical annotations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.text import Annotation, Text
from matplotlib.transforms import Bbox

from ..result import FitResult
from .themes import PlotTheme

PDI_H_C1S_LABELS = {
    "aromatic_C-C_C=C": "Aromatic C=C/C–C",
    "C-N_C-Cl": "C–N/C–Cl",
    "imide_N-C=O": "Imide N–C=O",
    "acid_O-C=O": "Carboxylic O–C=O",
    "pi-pi_star": "π–π* satellite",
    "carbonyl_O": "Carbonyl O",
    "imide_carbonyl_O": "Imide C=O",
    "acid_carbonyl_O": "Acid C=O",
    "acid_hydroxyl_OH": "Acid O–H",
    "methoxy_C": "Methoxy C",
    "methoxy_O": "Methoxy O",
    "C-N_C-Cl_methoxy_C": "C–N/C–Cl/methoxy C",
}

_HORIZONTAL_ALIGNMENTS = frozenset({"left", "center", "right"})
_VERTICAL_ALIGNMENTS = frozenset({"bottom", "center", "top"})
_PEAK_ANNOTATION_KEYS = frozenset({"offset_points", "connector", "horizontal_alignment", "vertical_alignment"})


@dataclass(frozen=True)
class PeakAnnotationOptions:
    offset_points: tuple[float, float]
    connector: bool
    horizontal_alignment: str
    vertical_alignment: str


def validate_peak_annotation_options(
    options_by_label: Mapping[str, Mapping[str, object]],
    *,
    default_connector: bool,
    max_connector_points: float,
) -> dict[str, PeakAnnotationOptions]:
    """Validate and normalise exact per-component annotation presentation."""
    normalised: dict[str, PeakAnnotationOptions] = {}
    for label, options in options_by_label.items():
        unknown = set(options) - _PEAK_ANNOTATION_KEYS
        if unknown:
            raise ValueError(f"unknown peak annotation option(s) for {label!r}: {', '.join(sorted(unknown))}")
        raw_offset = options.get("offset_points", (0.0, 0.0))
        if not isinstance(raw_offset, (list, tuple)) or len(raw_offset) != 2:
            raise ValueError(f"peak annotation offset for {label!r} must contain two finite values")
        raw_x, raw_y = raw_offset
        if any(isinstance(value, bool) for value in (raw_x, raw_y)):
            raise ValueError(f"peak annotation offset for {label!r} must contain two finite values")
        offset = (float(raw_x), float(raw_y))
        if not all(np.isfinite(value) for value in offset):
            raise ValueError(f"peak annotation offset for {label!r} must contain two finite values")
        connector = options.get("connector", default_connector)
        if not isinstance(connector, bool):
            raise ValueError(f"peak annotation connector for {label!r} must be true or false")
        if connector and float(np.hypot(*offset)) > max_connector_points:
            raise ValueError(
                f"peak annotation connector for {label!r} exceeds the {max_connector_points:g}-point limit"
            )
        horizontal_alignment = options.get("horizontal_alignment", "center")
        vertical_alignment = options.get("vertical_alignment", "bottom")
        if horizontal_alignment not in _HORIZONTAL_ALIGNMENTS:
            raise ValueError(f"invalid peak annotation horizontal alignment for {label!r}")
        if vertical_alignment not in _VERTICAL_ALIGNMENTS:
            raise ValueError(f"invalid peak annotation vertical alignment for {label!r}")
        normalised[label] = PeakAnnotationOptions(
            offset_points=offset,
            connector=connector,
            horizontal_alignment=str(horizontal_alignment),
            vertical_alignment=str(vertical_alignment),
        )
    return normalised


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
    annotation_options: Mapping[str, Mapping[str, object]] | None = None,
    include_negligible: bool = False,
    clearance_curves: Sequence[np.ndarray] = (),
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
    configured_options = validate_peak_annotation_options(
        annotation_options or {},
        default_connector=leaders,
        max_connector_points=theme.peak_annotation_max_connector_points,
    )

    if not displayed_components:
        return []
    source_maximum = max(
        (float(np.nanmax(np.abs(np.asarray(result.components[label])))) for label in displayed_components),
        default=0.0,
    )
    energy = np.asarray(result.energy)
    clearance_arrays = [np.asarray(curve) for curve in clearance_curves]
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
        centre_index = int(np.nanargmin(np.abs(energy - centre)))
        clearance_height = max(
            [float(displayed_curve[apex_index])]
            + [float(curve[centre_index]) for curve in clearance_arrays if curve.shape == energy.shape]
        )
        candidates.append((float(centre), label, float(displayed_curve[apex_index]), clearance_height))

    x_lower, x_upper = sorted(axis.get_xlim())
    x_span = max(x_upper - x_lower, np.finfo(float).eps)
    collision_distance = theme.peak_annotation_collision_fraction * x_span
    x_margin = 0.015 * x_span
    annotations: list[Annotation] = []
    previous_centre: float | None = None
    stagger_level = 0
    for centre, label, apex_height, clearance_height in sorted(candidates):
        if previous_centre is not None and abs(centre - previous_centre) < collision_distance:
            stagger_level += 1
        else:
            stagger_level = 0
        previous_centre = centre
        configured = configured_options.get(label)
        manual_x, manual_y = (
            configured.offset_points if configured is not None else manual_offsets.get(label, (0.0, 0.0))
        )
        anchor_x = min(max(centre, x_lower + x_margin), x_upper - x_margin)
        apex_y_pixels = axis.transData.transform((anchor_x, apex_height))[1]
        clearance_y_pixels = axis.transData.transform((anchor_x, clearance_height))[1]
        clearance_points = max(0.0, clearance_y_pixels - apex_y_pixels) * 72.0 / axis.figure.dpi
        text = f"{centre:.{precision}f}" + (" eV" if include_unit else "")
        colour = component_colours[label]
        connector = configured.connector if configured is not None else leaders
        arrowprops = None
        if connector:
            arrowprops = {
                "arrowstyle": "-",
                "color": colour,
                "linewidth": theme.peak_annotation_leader_width,
                "shrinkA": 2,
                "shrinkB": 2,
            }
        if configured is None:
            text_offset_y = (
                theme.peak_annotation_offset_points
                + clearance_points
                + stagger_level * theme.peak_annotation_stagger_points
                + manual_y
            )
            horizontal_alignment = "center"
            vertical_alignment = "bottom"
        else:
            text_offset_y = manual_y + (clearance_points if not connector else 0.0)
            horizontal_alignment = configured.horizontal_alignment
            vertical_alignment = configured.vertical_alignment
        annotation = axis.annotate(
            text,
            xy=(anchor_x, apex_height),
            xytext=(
                manual_x,
                text_offset_y,
            ),
            textcoords="offset points",
            ha=horizontal_alignment,
            va=vertical_alignment,
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
        annotation._xps_clearance_height = clearance_height
        annotation._xps_explicit_placement = configured is not None
        annotation._xps_configured_offset = (manual_x, manual_y) if configured is not None else None
        annotations.append(annotation)
    automatic_annotations = [item for item in annotations if not item._xps_explicit_placement]
    for _ in range(3):
        _lift_annotations_above_lines(axis, automatic_annotations)
        _lift_annotations_above_clearance(axis, automatic_annotations)
    _keep_annotations_inside_axes(axis, annotations, obstacles)
    return annotations


def _lift_annotations_above_clearance(axis: Axes, annotations: list[Annotation]) -> None:
    """Preserve the curve clearance after any automatic y-limit expansion."""
    canvas = axis.figure.canvas
    canvas.draw()
    renderer = canvas.get_renderer()
    points_per_pixel = 72.0 / axis.figure.dpi
    padding = 3.0
    for annotation in annotations:
        clearance_y = axis.transData.transform((annotation.xy[0], annotation._xps_clearance_height))[1]
        text_box = Text.get_window_extent(annotation, renderer)
        shift = clearance_y + padding - text_box.y0
        if shift > 0:
            current_x, current_y = annotation.get_position()
            annotation.set_position((current_x, current_y + shift * points_per_pixel))


def _lift_annotations_above_lines(axis: Axes, annotations: list[Annotation]) -> None:
    """Lift text above every visible curve that crosses its rendered width."""
    canvas = axis.figure.canvas
    canvas.draw()
    renderer = canvas.get_renderer()
    points_per_pixel = 72.0 / axis.figure.dpi
    padding = 3.0
    paths = [line.get_transform().transform_path(line.get_path()).vertices for line in axis.lines if line.get_visible()]
    for annotation in annotations:
        text_box = Text.get_window_extent(annotation, renderer)
        crossing_heights = [
            float(np.max(vertices[inside, 1]))
            for vertices in paths
            if np.any(inside := ((vertices[:, 0] >= text_box.x0) & (vertices[:, 0] <= text_box.x1)))
        ]
        if not crossing_heights:
            continue
        shift = max(crossing_heights) + padding - text_box.y0
        if shift > 0:
            current_x, current_y = annotation.get_position()
            annotation.set_position((current_x, current_y + shift * points_per_pixel))


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
    for _ in range(5):
        canvas.draw()
        renderer = canvas.get_renderer()
        axes_box = axis.get_window_extent(renderer)
        obstacle_boxes = [artist.get_window_extent(renderer) for artist in obstacles if artist.get_visible()]
        adjusted = False
        placed_boxes: list[Bbox] = []
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
            shifted_box = box.translated(shift_x, shift_y)
            for placed_box in placed_boxes:
                if shifted_box.overlaps(placed_box):
                    extra_y = placed_box.y1 - shifted_box.y0 + padding
                    shift_y += extra_y
                    shifted_box = shifted_box.translated(0.0, extra_y)
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
            placed_boxes.append(box.translated(shift_x, shift_y))
        if not adjusted:
            break
