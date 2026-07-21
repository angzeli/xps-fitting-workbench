import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
PUBLICATION_EXAMPLE = ROOT / "examples" / "plot_pdi_h_cooh_c1s_publication.py"
EXAMPLES = sorted(
    path for path in (ROOT / "examples").glob("*.py") if not path.name.startswith("_") and path != PUBLICATION_EXAMPLE
)


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.stem)
def test_example_smoke(example: Path, tmp_path: Path) -> None:
    tree = ast.parse(example.read_text(encoding="utf-8"))
    assert any(isinstance(node, ast.FunctionDef) and node.name == "main" for node in tree.body)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    environment["MPLBACKEND"] = "Agg"
    environment["MPLCONFIGDIR"] = str(tmp_path / "matplotlib")
    command = [sys.executable, str(example), "--output-dir", str(tmp_path / example.stem)]
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


def test_experimental_publication_example_requires_calibrated_manifest(tmp_path: Path) -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    environment["MPLBACKEND"] = "Agg"
    completed = subprocess.run(
        [
            sys.executable,
            str(PUBLICATION_EXAMPLE),
            "--sample-manifest",
            str(tmp_path / "missing.json"),
            "--output-dir",
            str(tmp_path / "output"),
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 2
    assert "reviewed calibrated sample manifest not found" in completed.stderr
