import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
EXAMPLES = sorted(path for path in (ROOT / "examples").glob("*.py") if not path.name.startswith("_"))


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.stem)
def test_example_smoke(example: Path, tmp_path: Path) -> None:
    tree = ast.parse(example.read_text(encoding="utf-8"))
    assert any(isinstance(node, ast.FunctionDef) and node.name == "main" for node in tree.body)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    environment["MPLBACKEND"] = "Agg"
    environment["MPLCONFIGDIR"] = str(tmp_path / "matplotlib")
    completed = subprocess.run(
        [sys.executable, str(example), "--output-dir", str(tmp_path / example.stem)],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert not list(tmp_path.rglob("*.svg"))
    assert not list(tmp_path.rglob("*.tif")) and not list(tmp_path.rglob("*.tiff"))
