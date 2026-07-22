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
