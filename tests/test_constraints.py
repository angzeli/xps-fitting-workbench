"""Verify parameter-domain checks and declared cross-peak relationships."""

import pytest

from xps_fitting.configuration import PeakConfig
from xps_fitting.constraints import cl2p_doublet, validate_links


def test_nonnegative_area_and_valid_links() -> None:
    with pytest.raises(ValueError):
        PeakConfig("bad", 1, (0, 2), -1)
    peaks = cl2p_doublet("Cl", 200.0, 100.0)
    validate_links(peaks)
    assert peaks[1].centre == pytest.approx(peaks[0].centre + 1.6)
    assert peaks[1].area == pytest.approx(peaks[0].area / 2)
    assert peaks[0].width_group == peaks[1].width_group
