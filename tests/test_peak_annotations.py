import copy
from itertools import combinations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.text import Text

from xps_fitting.plotting import component_colour, export_figure, plot_xps_fit, plot_xps_series
from xps_fitting.result import FitResult


def annotation_result(sample: str = "PDI-H-COOH") -> FitResult:
    energy = np.linspace(280, 292, 241)
    background = np.linspace(2, 3, energy.size)
    aromatic = 10 * np.exp(-(((energy - 285.0) / 0.55) ** 2))
    carbon_nitrogen = 7 * np.exp(-(((energy - 285.25) / 0.65) ** 2))
    negligible = 0.005 * np.exp(-(((energy - 289.0) / 0.5) ** 2))
    components = {
        "aromatic_C-C_C=C": aromatic,
        "C-N_C-Cl": carbon_nitrogen,
        "acid_O-C=O": negligible,
    }
    total = background + sum(components.values())
    return FitResult(
        energy,
        total,
        background,
        components,
        total,
        np.zeros_like(energy),
        {
            "aromatic_C-C_C=C.centre": 285.0,
            "C-N_C-Cl.centre": 285.25,
            "acid_O-C=O.centre": 289.0,
        },
        configuration={"region": "C 1s"},
        metadata={"sample_name": sample},
    )


def peak_annotations(axis):
    return [text for text in axis.texts if (text.get_gid() or "").startswith("peak-position:")]


def test_peak_positions_format_colour_centres_stagger_offsets_and_exports(tmp_path) -> None:
    result = annotation_result()
    before = copy.deepcopy(result.to_dict())
    figure, axis = plot_xps_fit(
        result,
        component_display_mode="filled_to_background",
        show_peak_positions=True,
        peak_annotation_offsets={"C-N_C-Cl": (4, 3)},
    )
    annotations = peak_annotations(axis)
    figure.canvas.draw()
    assert [annotation.get_text() for annotation in annotations] == ["285.0 eV", "285.2 eV"]
    assert [annotation._xps_fitted_centre for annotation in annotations] == [285.0, 285.25]
    assert [annotation.xy[0] for annotation in annotations] == [285.0, 285.25]
    assert [annotation._xps_stagger_level for annotation in annotations] == [0, 1]
    assert annotations[1].get_position()[0] == 4
    assert annotations[1].get_position()[1] > annotations[0].get_position()[1]
    assert annotations[0].get_color() == component_colour("aromatic_C-C_C=C")
    assert annotations[1].get_color() == component_colour("C-N_C-Cl")
    assert all(annotation.get_fontweight() == "bold" for annotation in annotations)
    assert all(annotation.arrow_patch is not None for annotation in annotations)
    assert all(
        not Text.get_window_extent(first).overlaps(Text.get_window_extent(second))
        for first, second in combinations(annotations, 2)
    )
    assert all(
        Text.get_window_extent(annotation).y0
        > axis.transData.transform((annotation.xy[0], annotation._xps_clearance_height))[1]
        for annotation in annotations
    )
    for annotation in annotations:
        text_box = Text.get_window_extent(annotation)
        for line in axis.lines:
            vertices = line.get_transform().transform_path(line.get_path()).vertices
            within_text_width = (vertices[:, 0] >= text_box.x0) & (vertices[:, 0] <= text_box.x1)
            assert not np.any(within_text_width) or np.max(vertices[within_text_width, 1]) < text_box.y0
    assert axis.xaxis_inverted()
    axes_box = axis.get_window_extent()
    assert all(
        axes_box.contains(*annotation.get_window_extent().get_points()[0])
        and axes_box.contains(*annotation.get_window_extent().get_points()[1])
        for annotation in annotations
    )
    assert result.to_dict() == before
    paths = export_figure(figure, tmp_path / "annotated", formats=("png", "pdf"))
    assert all(path.stat().st_size > 100 for path in paths.values())
    plt.close(figure)


def test_peak_positions_hidden_negligible_units_and_leaders_can_be_controlled() -> None:
    result = annotation_result()
    figure, axis = plot_xps_fit(result, component_display_mode="hidden", show_peak_positions=True)
    assert not peak_annotations(axis)
    plt.close(figure)

    figure, axis = plot_xps_fit(
        result,
        component_display_mode="hidden",
        show_peak_positions=True,
        annotate_hidden_components=True,
        annotate_negligible_components=True,
        peak_position_precision=2,
        peak_position_unit=False,
        peak_annotation_leaders=False,
    )
    annotations = peak_annotations(axis)
    assert [annotation.get_text() for annotation in annotations] == ["285.00", "285.25", "289.00"]
    assert all(annotation.arrow_patch is None for annotation in annotations)
    plt.close(figure)


def test_exact_annotation_options_control_connectors_alignment_and_preserve_limits() -> None:
    energy = np.linspace(280, 292, 241)
    background = np.full_like(energy, 20.0)
    aromatic = 10 * np.exp(-(((energy - 285.0) / 0.55) ** 2))
    carbon_nitrogen = 4 * np.exp(-(((energy - 287.0) / 0.6) ** 2))
    total = background + aromatic + carbon_nitrogen
    result = FitResult(
        energy,
        total,
        background,
        {"aromatic_C-C_C=C": aromatic, "C-N_C-Cl": carbon_nitrogen},
        total,
        np.zeros_like(energy),
        {"aromatic_C-C_C=C.centre": 285.0, "C-N_C-Cl.centre": 287.0},
    )
    unannotated, plain_axis = plot_xps_fit(result)
    expected_limits = plain_axis.get_ylim()

    figure, axis = plot_xps_fit(
        result,
        show_peak_positions=True,
        peak_annotations={
            "aromatic_C-C_C=C": {
                "offset_points": (0, 16),
                "connector": False,
                "horizontal_alignment": "center",
                "vertical_alignment": "bottom",
            },
            "C-N_C-Cl": {
                "offset_points": (-18, 20),
                "connector": True,
                "horizontal_alignment": "right",
                "vertical_alignment": "bottom",
            },
        },
    )
    annotations = {item._xps_component_label: item for item in peak_annotations(axis)}
    aromatic_annotation = annotations["aromatic_C-C_C=C"]
    carbon_nitrogen_annotation = annotations["C-N_C-Cl"]
    figure.canvas.draw()

    assert axis.get_ylim() == expected_limits
    assert aromatic_annotation.arrow_patch is None
    assert aromatic_annotation.get_ha() == "center" and aromatic_annotation.get_va() == "bottom"
    assert aromatic_annotation._xps_configured_offset == (0.0, 16.0)
    assert (
        Text.get_window_extent(aromatic_annotation).y0
        > axis.transData.transform((aromatic_annotation.xy[0], aromatic_annotation._xps_clearance_height))[1]
    )
    assert carbon_nitrogen_annotation.arrow_patch is not None
    assert carbon_nitrogen_annotation.get_ha() == "right" and carbon_nitrogen_annotation.get_va() == "bottom"
    assert carbon_nitrogen_annotation._xps_configured_offset == (-18.0, 20.0)
    assert np.hypot(*carbon_nitrogen_annotation.get_position()) <= 30

    plt.close(unannotated)
    plt.close(figure)


def test_peak_positions_work_in_multipanel_without_input_mutation() -> None:
    results = [annotation_result("PDI-H-COOH"), annotation_result("PDI-Me-COOH")]
    before = copy.deepcopy([result.to_dict() for result in results])
    figure, axes = plot_xps_series(results, show_peak_positions=True)
    assert [len(peak_annotations(axis)) for axis in axes.ravel()] == [2, 2]
    assert all(axis.xaxis_inverted() for axis in axes.ravel())
    assert [result.to_dict() for result in results] == before
    plt.close(figure)


def test_peak_position_text_avoids_the_framed_legend() -> None:
    energy = np.linspace(280, 292, 241)
    background = np.ones_like(energy)
    peak = 10 * np.exp(-(((energy - 290.5) / 0.45) ** 2))
    result = FitResult(
        energy,
        background + peak,
        background,
        {"aromatic_C-C_C=C": peak},
        background + peak,
        np.zeros_like(energy),
        {"aromatic_C-C_C=C.centre": 290.5},
    )
    figure, axis = plot_xps_fit(result, show_peak_positions=True)
    figure.canvas.draw()
    annotation = peak_annotations(axis)[0]
    assert not Text.get_window_extent(annotation).overlaps(axis.get_legend().get_window_extent())
    plt.close(figure)
