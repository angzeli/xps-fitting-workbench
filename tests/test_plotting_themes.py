import warnings

import matplotlib as mpl
import pytest

from xps_fitting.plotting import (
    FIGURE_SIZE_PRESETS,
    VISIBLE_SPINE_WIDTH,
    PlotTheme,
    canonical_core_level,
    component_colour,
    core_level_colour,
    figure_size_preset,
    load_theme,
    theme_context,
    validate_theme,
)
from xps_fitting.plotting.palettes import COMPONENT_COLOURS, UNKNOWN_COMPONENT_COLOUR
from xps_fitting.plotting.validation import contrast_ratio


def test_themes_aliases_and_deterministic_colours() -> None:
    assert load_theme("angze_publication").dpi == 300
    assert load_theme("presentation").figure_size == (8, 5)
    assert figure_size_preset("double_column") == FIGURE_SIZE_PRESETS["double-column"]
    assert figure_size_preset("detailed_publication") == (8, 6)
    assert load_theme("angze_publication").figure_size == (8, 6)
    assert all(
        load_theme(name).spine_width == VISIBLE_SPINE_WIDTH
        for name in ("angze_publication", "monochrome_publication", "presentation")
    )
    for alias in ("C1s", "C1s_Scan", "C 1s"):
        assert canonical_core_level(alias) == "C 1s"
        assert core_level_colour(alias) == "#8C8C8C"
    with pytest.warns(UserWarning, match="has no semantic colour"):
        assert component_colour("unknown assignment") == UNKNOWN_COMPONENT_COLOUR


def test_theme_context_does_not_leak_rcparams() -> None:
    before = mpl.rcParams.copy()
    with theme_context("presentation"):
        assert mpl.rcParams["font.size"] == 15
    assert dict(mpl.rcParams) == dict(before)


def test_semantic_component_lines_have_white_background_contrast() -> None:
    assert all(contrast_ratio(colour) >= 3 for colour in COMPONENT_COLOURS.values())


def test_semantic_component_colours_are_sample_order_and_extension_independent() -> None:
    expected = {
        "aromatic_C-C_C=C": "#5B6F8A",
        "C-N_C-Cl": "#2563EB",
        "imide_N-C=O": "#7C3AED",
        "acid_O-C=O": "#EA580C",
        "pi-pi_star": "#0F766E",
        "imide_carbonyl_O": "#D62728",
        "acid_carbonyl_O": "#E66101",
        "acid_hydroxyl_OH": "#C2185B",
        "Cl_2p3/2": "#166534",
        "Cl_2p1/2": "#4C956C",
        "methoxy_C": "#8C564B",
        "methoxy_O": "#17A2B8",
        "C-N_C-Cl_methoxy_C": "#4C78A8",
    }
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        for _sample in ("PDI-H-COOH", "PDI-Me-COOH", "PDI-OMe-COOH", "another-methoxy-PDI"):
            assert {key: component_colour(key) for key in expected} == expected
    assert {key: component_colour(key) for key in reversed(expected)} == dict(reversed(tuple(expected.items())))
    extended = {**expected, "future_assignment": "#000000"}
    assert {key: extended[key] for key in expected} == expected


def test_theme_validation_rejects_style_contract_violations() -> None:
    with pytest.raises(ValueError, match="1.8 pt"):
        load_theme(PlotTheme("angze_publication", spine_width=1.2))
    with pytest.raises(ValueError, match="unrecognised theme override"):
        load_theme("angze_publication", invented_key=True)
    with pytest.raises(ValueError, match="unsupported output"):
        validate_theme(load_theme(), output_formats=("eps",))
    with pytest.raises(ValueError, match="missing assignment colour"):
        validate_theme(load_theme(), assignment_colours={}, required_assignments=("Cl_2p3/2",))
