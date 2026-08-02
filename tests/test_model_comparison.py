"""Verify ordered candidate comparison on a known five-component signal."""

from pathlib import Path

import numpy as np

from xps_fitting.configuration import load_config
from xps_fitting.lineshapes import pseudo_voigt
from xps_fitting.model_comparison import compare_models, comparison_table
from xps_fitting.spectrum import Spectrum


def test_five_component_signal_supports_five_component_candidate() -> None:
    root = Path(__file__).parents[1]
    x = np.linspace(280, 294, 401)
    y = 20 + sum(
        pseudo_voigt(x, a, c, w, 0.5)
        for a, c, w in [
            (1000, 284.65, 1.4),
            (500, 285.85, 1.4),
            (400, 287.9, 1.5),
            (250, 289.15, 1.5),
            (150, 290.7, 2.2),
        ]
    )
    configs = [load_config(root / "configs" / "fits" / f"pdi_h_cooh_c1s_{n}.json") for n in (4, 5)]
    table = comparison_table(compare_models(Spectrum(x, y), configs))
    assert {row["model"] for row in table} == {"C1s_4", "C1s_5"}
    assert (
        next(row for row in table if row["model"] == "C1s_5")["bic"]
        < next(row for row in table if row["model"] == "C1s_4")["bic"]
    )
