import pytest

from xps_fitting.naming import make_output_name, safe_slug, validate_output_stem


def test_output_names_are_safe_predictable_and_bounded() -> None:
    assert safe_slug("PDI-H / C 1s") == "pdi-h-c-1s"
    assert (
        make_output_name(sample="PDI-H", region="C 1s", model="five peak", plot_type="publication")
        == "pdi-h-c-1s-five-peak-publication"
    )
    assert len(make_output_name(sample="x" * 200, max_length=40)) == 40
    assert validate_output_stem("pdi_three-sample_v2") == "pdi_three-sample_v2"
    with pytest.raises(ValueError, match="filesystem-safe"):
        validate_output_stem("../escape")
