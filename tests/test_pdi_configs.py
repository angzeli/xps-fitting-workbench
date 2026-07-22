from pathlib import Path

from xps_fitting.configuration import load_config
from xps_fitting.constraints import validate_links

ROOT = Path(__file__).resolve().parents[1]
FIT_CONFIGS = ROOT / "configs" / "fits"


def test_n1s_one_component_candidates_load() -> None:
    paths = (
        FIT_CONFIGS / "pdi_h_cooh_n1s_1.json",
        FIT_CONFIGS / "pdi_h_cooh_n1s_1_shirley.json",
    )

    configs = [load_config(path) for path in paths]

    assert [config.name for config in configs] == ["N1s_1_linear", "N1s_1_shirley"]
    assert [config.background for config in configs] == ["linear", "shirley"]
    assert all(config.region == "N 1s" for config in configs)
    assert all(len(config.peaks) == 1 for config in configs)
    assert all(config.peaks[0].label == "imide_N-C=O" for config in configs)
    assert all(config.metadata["sensitivity_only"] is False for config in configs)
    assert all(config.metadata["expected_nitrogen_environments"] == 1 for config in configs)
    for config in configs:
        validate_links(config.peaks)
        peak = config.peaks[0]
        assert peak.centre_bounds[0] < 399.900054 < peak.centre_bounds[1]
        assert peak.fwhm_bounds == [0.8, 2.4]


def test_o1s_two_and_three_component_candidates_load() -> None:
    paths = (
        FIT_CONFIGS / "pdi_h_cooh_o1s_2.json",
        FIT_CONFIGS / "pdi_h_cooh_o1s_2_shirley.json",
        FIT_CONFIGS / "pdi_h_cooh_o1s_3.json",
        FIT_CONFIGS / "pdi_h_cooh_o1s_3_shirley.json",
    )

    configs = [load_config(path) for path in paths]

    assert [config.name for config in configs] == [
        "O1s_2_linear",
        "O1s_2_shirley",
        "O1s_3_linear",
        "O1s_3_shirley",
    ]
    assert [len(config.peaks) for config in configs] == [2, 2, 3, 3]
    assert [config.background for config in configs] == ["linear", "shirley", "linear", "shirley"]
    assert all(config.metadata["stoichiometry_treatment"] == "benchmark_only_not_constrained" for config in configs)
    for config in configs:
        validate_links(config.peaks)
        assert config.region == "O 1s"
        assert config.metadata["sensitivity_only"] is False
        assert {peak.width_group for peak in config.peaks} == {"structural_O"}
        assert {peak.fraction_group for peak in config.peaks} == {"structural_O"}
        assert {tuple(peak.fwhm_bounds) for peak in config.peaks} == {(0.8, 2.5)}


def test_o1s_stoichiometry_is_a_benchmark_not_an_area_link() -> None:
    for path in (
        FIT_CONFIGS / "pdi_h_cooh_o1s_2.json",
        FIT_CONFIGS / "pdi_h_cooh_o1s_3.json",
    ):
        config = load_config(path)

        assert config.metadata["nominal_structural_ratio"]
        assert all(peak.area_ratio_to is None for peak in config.peaks)
