import ast
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from xps_fitting.export import save_fit_bundle
from xps_fitting.result import FitResult

ROOT = Path(__file__).parents[1]
EXAMPLES = sorted(path for path in (ROOT / "examples").glob("*.py") if not path.name.startswith("_"))


def publication_bundle(path: Path) -> Path:
    energy = np.linspace(280, 294, 141)
    background = np.full_like(energy, 2.0)
    centres = {
        "aromatic_C-C_C=C": 284.4,
        "C-N_C-Cl": 285.3,
        "imide_N-C=O": 287.8,
        "acid_O-C=O": 288.7,
        "pi-pi_star": 290.5,
    }
    components = {
        label: (10 - index) * np.exp(-(((energy - centre) / 0.7) ** 2))
        for index, (label, centre) in enumerate(centres.items())
    }
    total = background + sum(components.values())
    result = FitResult(
        energy,
        total,
        background,
        components,
        total,
        np.zeros_like(energy),
        {f"{label}.centre": centre for label, centre in centres.items()},
        configuration={"region": "C 1s"},
        metadata={"sample_name": "PDI-H-COOH", "data_origin": "test fixture"},
    )
    save_fit_bundle(result, path)
    return path


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.stem)
def test_example_smoke(example: Path, tmp_path: Path) -> None:
    tree = ast.parse(example.read_text(encoding="utf-8"))
    assert any(isinstance(node, ast.FunctionDef) and node.name == "main" for node in tree.body)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    environment["MPLBACKEND"] = "Agg"
    environment["MPLCONFIGDIR"] = str(tmp_path / "matplotlib")
    command = [sys.executable, str(example), "--output-dir", str(tmp_path / example.stem)]
    if example.stem == "plot_pdi_h_cooh_c1s_publication":
        command.extend(("--fit-result", str(publication_bundle(tmp_path / "reviewed.bundle"))))
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert not list(tmp_path.rglob("*.svg"))
    assert not list(tmp_path.rglob("*.tif")) and not list(tmp_path.rglob("*.tiff"))
    if example.stem == "plot_pdi_h_cooh_c1s_publication":
        output = tmp_path / example.stem
        png = output / "pdi_h_cooh_c1s_publication.png"
        assert png.is_file()
        assert (output / "pdi_h_cooh_c1s_publication.pdf").is_file()
        data = png.read_bytes()
        physical_chunk = data.index(b"pHYs")
        pixels_per_metre = int.from_bytes(data[physical_chunk + 4 : physical_chunk + 8], "big")
        assert pixels_per_metre * 0.0254 == pytest.approx(600, abs=0.1)
