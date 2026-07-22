import json
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10 CI
    import tomli as tomllib


def test_package_imports() -> None:
    import xps_fitting

    assert xps_fitting.__version__ == "0.3.0"


def test_editable_backend_uses_the_source_package() -> None:
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    assert project["build-system"]["build-backend"] == "uv_build"
    assert project["tool"]["uv"]["build-backend"]["module-name"] == "xps_fitting"


def test_console_entry_point_imports() -> None:
    completed = subprocess.run(
        [str(Path(sys.executable).with_name("xps-fit")), "--version"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "xps-fit 0.3.0"


def test_doctor_reports_the_repository_source(capsys) -> None:
    from xps_fitting.cli import main

    root = Path(__file__).resolve().parents[1]
    assert main(["--repository", str(root), "doctor"]) == 0
    report = json.loads(capsys.readouterr().out)

    assert report["healthy"] is True
    assert report["editable"] is True
    assert Path(report["package_import_path"]) == root / "src" / "xps_fitting"
    assert report["source_and_installed_versions_match"] is True
