import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest

from xps_fitting.cli import main
from xps_fitting.export import curve_table, save_fit_bundle
from xps_fitting.plotting import PlotConfig, fit_result_from_dict, load_curve_result, load_plot_config, plot_from_config
from xps_fitting.result import FitResult


def fixture() -> FitResult:
    x = np.linspace(0, 2, 21)
    bg = np.ones_like(x)
    peak = np.exp(-(((x - 1) / 0.2) ** 2))
    total = bg + peak
    return FitResult(
        x,
        total,
        bg,
        {"p": peak},
        total,
        np.zeros_like(x),
        {"p.centre": 1.0},
        configuration={"region": "C 1s"},
    )


def test_recipe_round_trip_and_validation(tmp_path) -> None:
    config = PlotConfig(
        theme="presentation",
        figure_size_preset="detailed-publication",
        output_formats=("pdf",),
        output_filename="recipe",
        core_level="C 1s",
        residual_panel=True,
        x_limits=(2, 0),
        show_peak_positions=True,
        peak_annotation_offsets={"p": (2, 3)},
        peak_label_fontsize=9,
        peak_annotation_leader_width=0.5,
        x_minor_interval=0.5,
        show_y_ticks=False,
        show_top_ticks=False,
        show_sample_title=False,
        core_level_label_position=(0.97, 0.96),
    )
    path = config.save(tmp_path / "recipe.json")
    assert load_plot_config(path) == config
    figure, axis, paths = plot_from_config(config=config, result=fixture(), output_directory=tmp_path)
    assert any((text.get_gid() or "").startswith("peak-position:") for text in axis[0].texts)
    assert any(text.get_gid() == "core-level-label" for text in axis[0].texts)
    annotation = next(text for text in axis[0].texts if (text.get_gid() or "").startswith("peak-position:"))
    assert annotation.get_fontsize() == 9
    assert annotation.arrow_patch.get_linewidth() == 0.5
    assert paths["pdf"].stat().st_size > 100
    plt.close(figure)
    with pytest.raises(ValueError):
        PlotConfig(component_display_mode="invented")
    with pytest.raises(ValueError, match="unsupported output"):
        PlotConfig(output_formats=("svg",))
    with pytest.raises(ValueError, match="either figure_size"):
        PlotConfig(figure_size=(4, 3), figure_size_preset="single-column")


def test_curve_and_serialised_loading_and_cli(tmp_path) -> None:
    result = fixture()
    csv = tmp_path / "curves.csv"
    curve_table(result).to_csv(csv, index=False)
    metadata = tmp_path / "metadata.json"
    metadata.write_text(json.dumps({"configuration": result.configuration}))
    loaded = load_curve_result(csv, metadata)
    np.testing.assert_allclose(loaded.total_fit, result.total_fit)
    full = fit_result_from_dict(result.to_dict())
    np.testing.assert_allclose(full.components["p"], result.components["p"])
    recipe = PlotConfig(output_formats=("png", "pdf"), output_filename="cli").save(tmp_path / "recipe.json")
    assert (
        main(["plot", str(csv), "--metadata", str(metadata), "--recipe", str(recipe), "--output-dir", str(tmp_path)])
        == 0
    )
    assert (tmp_path / "cli.png").stat().st_size > 100
    assert (tmp_path / "cli.pdf").stat().st_size > 100


def test_multi_input_bundle_cli_collision_dry_run_and_errors(tmp_path, capsys) -> None:
    bundles = []
    for index, sample in enumerate(("PDI-H", "PDI-Me", "PDI-OMe")):
        result = fixture()
        result.metadata["sample_name"] = sample
        bundle = tmp_path / f"bundle-{index}"
        save_fit_bundle(result, bundle)
        bundles.append(str(bundle))
    recipe = PlotConfig(
        output_formats=("png", "pdf"),
        output_filename="three-sample",
        panel_layout="horizontal",
        panel_labels=("a", "b", "c"),
        core_level="C 1s",
    ).save(tmp_path / "multi.json")
    arguments = ["plot", *bundles, "--recipe", str(recipe), "--output-dir", str(tmp_path)]
    for label in ("PDI-H", "PDI-Me", "PDI-OMe"):
        arguments.extend(("--sample-label", label))
    assert main(arguments) == 0
    assert (tmp_path / "three-sample.png").stat().st_size > 100
    assert (tmp_path / "three-sample.pdf").stat().st_size > 100
    assert main(arguments) == 2
    assert "error:" in capsys.readouterr().err
    assert main([*arguments, "--overwrite"]) == 0

    dry_run = [
        "plot",
        *bundles,
        "--recipe",
        str(recipe),
        "--output-dir",
        str(tmp_path),
        "--output-name",
        "planned",
        "--dry-run",
    ]
    assert main(dry_run) == 0
    assert not (tmp_path / "planned.png").exists()

    invalid_recipe = tmp_path / "invalid.json"
    invalid_recipe.write_text(json.dumps({"output_formats": ["svg"]}), encoding="utf-8")
    assert main(["plot", bundles[0], "--recipe", str(invalid_recipe), "--output-dir", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert "unsupported output" in error and "Traceback" not in error


def test_c1s_publication_recipe_records_final_layout() -> None:
    root = Path(__file__).parents[1]
    config = load_plot_config(root / "configs" / "plots" / "c1s_publication.json")
    assert config.output_formats == ("png", "pdf")
    assert config.output_filename == "pdi_h_cooh_c1s_publication"
    assert config.figure_size_preset == "detailed-publication" and config.dpi == 600
    assert config.tick_spacing == 5 and config.x_minor_interval == 2.5
    assert not config.show_y_ticks and config.show_top_ticks is False
    assert not config.show_sample_title
    assert config.core_level_label_position == (0.97, 0.96)
    assert set(config.peak_annotation_offsets) == {
        "aromatic_C-C_C=C",
        "C-N_C-Cl",
        "imide_N-C=O",
        "acid_O-C=O",
        "pi-pi_star",
    }
