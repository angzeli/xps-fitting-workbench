import matplotlib as mpl

from xps_fitting.plotting import canonical_core_level, component_colour, core_level_colour, load_theme, theme_context


def test_themes_aliases_and_deterministic_colours() -> None:
    assert load_theme("angze_publication").dpi == 300
    assert load_theme("presentation").figure_size == (8, 5)
    for alias in ("C1s", "C1s_Scan", "C 1s"):
        assert canonical_core_level(alias) == "C 1s"
        assert core_level_colour(alias) == "#8C8C8C"
    assert component_colour("unknown assignment") == component_colour("unknown assignment")


def test_theme_context_does_not_leak_rcparams() -> None:
    before = mpl.rcParams.copy()
    with theme_context("presentation"):
        assert mpl.rcParams["font.size"] == 15
    assert dict(mpl.rcParams) == dict(before)
