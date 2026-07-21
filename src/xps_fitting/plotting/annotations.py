"""Labels and compact statistical annotations."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
from matplotlib.axes import Axes
from matplotlib.text import Annotation

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
    return annotations
