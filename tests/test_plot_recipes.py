import json

import numpy as np
import pytest

from xps_fitting.cli import main
from xps_fitting.export import curve_table
from xps_fitting.plotting import PlotConfig, fit_result_from_dict, load_curve_result, load_plot_config
from xps_fitting.result import FitResult


def fixture() -> FitResult:
    x = np.linspace(0, 2, 21); bg = np.ones_like(x); peak = np.exp(-((x - 1) / 0.2) ** 2); total = bg + peak
    return FitResult(x, total, bg, {"p": peak}, total, np.zeros_like(x), {}, configuration={"region": "C 1s"})


def test_recipe_round_trip_and_validation(tmp_path) -> None:
    config = PlotConfig(theme="presentation", output_formats=("pdf",), output_filename="recipe", residual_panel=True, x_limits=(2, 0))
    path = config.save(tmp_path / "recipe.json")
    assert load_plot_config(path) == config
    with pytest.raises(ValueError): PlotConfig(component_display_mode="invented")
    with pytest.raises(ValueError, match="unsupported output"): PlotConfig(output_formats=("svg",))


def test_curve_and_serialised_loading_and_cli(tmp_path) -> None:
    result = fixture(); csv = tmp_path / "curves.csv"; curve_table(result).to_csv(csv, index=False)
    metadata = tmp_path / "metadata.json"; metadata.write_text(json.dumps({"configuration": result.configuration}))
    loaded = load_curve_result(csv, metadata)
    np.testing.assert_allclose(loaded.total_fit, result.total_fit)
    full = fit_result_from_dict(result.to_dict()); np.testing.assert_allclose(full.components["p"], result.components["p"])
    recipe = PlotConfig(output_formats=("png", "pdf"), output_filename="cli").save(tmp_path / "recipe.json")
    assert main(["plot", str(csv), "--metadata", str(metadata), "--recipe", str(recipe), "--output-dir", str(tmp_path)]) == 0
    assert (tmp_path / "cli.png").stat().st_size > 100
    assert (tmp_path / "cli.pdf").stat().st_size > 100
