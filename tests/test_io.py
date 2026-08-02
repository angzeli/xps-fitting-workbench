"""Verify tabular coercion, duplicate averaging, ordering, and file loading."""

import numpy as np
import pandas as pd

from xps_fitting.io import read_csv, read_xlsx, spectrum_from_dataframe


def test_dataframe_cleaning_order_duplicates_and_crop() -> None:
    frame = pd.DataFrame({"E": [3, 2, 2, "bad", 1, np.nan], "I": [4, 2, 4, 9, 1, 5]})
    spectrum = spectrum_from_dataframe(frame, "E", "I")
    np.testing.assert_allclose(spectrum.binding_energy, [1, 2, 3])
    np.testing.assert_allclose(spectrum.intensity, [1, 3, 4])
    assert spectrum.metadata["original_order"] == "unordered"
    np.testing.assert_allclose(spectrum.crop(1, 2).binding_energy, [1, 2])


def test_csv_and_xlsx(tmp_path) -> None:
    frame = pd.DataFrame({"binding_energy_eV": [2, 1], "intensity": [20, 10]})
    csv_path, xlsx_path = tmp_path / "s.csv", tmp_path / "s.xlsx"
    frame.to_csv(csv_path, index=False)
    frame.to_excel(xlsx_path, index=False)
    assert read_csv(csv_path).metadata["original_order"] == "descending"
    np.testing.assert_allclose(read_xlsx(xlsx_path).intensity, [10, 20])
