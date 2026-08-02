"""Verify PDI fit-configuration contracts and workflow dry-run isolation."""

from pathlib import Path

import pytest

from xps_fitting.configuration import FitConfig, PeakConfig, load_config
from xps_fitting.constraints import validate_links
from xps_fitting.project_workflow import fit_region_candidates

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


def test_fit_configuration_rejects_unsupported_background() -> None:
    with pytest.raises(ValueError, match="background"):
        FitConfig("invalid", "N 1s", [PeakConfig("N", 400.0, (399.0, 401.0), 100.0)], background="none")


def test_fit_region_dry_run_does_not_run_optimizer(monkeypatch) -> None:
    def unexpected_optimizer(*args, **kwargs):
        """Fail if dry-run planning reaches numerical optimisation."""
        raise AssertionError("dry-run called the optimizer")

    monkeypatch.setattr("xps_fitting.project_workflow.compare_models", unexpected_optimizer)

    plan = fit_region_candidates(ROOT, "PDI-H-COOH", "N1s", dry_run=True)

    assert plan["optimizer_ran"] is False
    assert plan["files_written"] is False
    assert [item["model"] for item in plan["configurations"]] == ["N1s_1_linear", "N1s_1_shirley"]
