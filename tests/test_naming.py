"""Verify deterministic, bounded, and path-safe output naming rules."""

import pytest

from xps_fitting.naming import (
    make_output_name,
    resolve_sample_output_stem,
    safe_slug,
    sample_slug,
    validate_output_stem,
)


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


@pytest.mark.parametrize(
    ("sample", "expected"),
    [
        ("PDI-H-COOH", "pdi_h_cooh"),
        ("PDI-Me-COOH", "pdi_me_cooh"),
        ("PDI-OMe-COOH", "pdi_ome_cooh"),
    ],
)
def test_sample_slug_uses_deterministic_publication_spelling(sample, expected) -> None:
    assert sample_slug(sample) == expected


def test_sample_output_template_resolution_is_strict_and_preserves_literals() -> None:
    samples = ("PDI-H-COOH", "PDI-Me-COOH", "PDI-OMe-COOH")
    stems = {resolve_sample_output_stem("{sample_slug}_c1s", sample=sample) for sample in samples}
    assert stems == {"pdi_h_cooh_c1s", "pdi_me_cooh_c1s", "pdi_ome_cooh_c1s"}
    assert resolve_sample_output_stem("custom_figure", sample="PDI-Me-COOH") == "custom_figure"
    with pytest.raises(ValueError, match="unsupported output filename template field"):
        resolve_sample_output_stem("{unknown}_c1s", sample="PDI-H-COOH")
