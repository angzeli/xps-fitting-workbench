"""Shared deterministic inputs for executable examples."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from xps_fitting.lineshapes import pseudo_voigt
from xps_fitting.spectrum import Spectrum

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "outputs" / "examples"


def add_output_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT, help="Directory for generated example files."
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace this example's existing output files.")


def prepare_output(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def check_output_paths(paths: list[Path], *, overwrite: bool) -> None:
    collisions = [path for path in paths if path.exists()]
    if collisions and not overwrite:
        names = ", ".join(str(path) for path in collisions)
        raise FileExistsError(f"example output already exists: {names}; pass --overwrite to replace it")


def synthetic_c1s(points: int = 401) -> Spectrum:
    energy = np.linspace(280, 294, points)
    peaks = ((1000, 284.65, 1.4), (500, 285.85, 1.4), (400, 287.9, 1.5), (250, 289.15, 1.5), (150, 290.7, 2.2))
    intensity = 20 + sum(pseudo_voigt(energy, area, centre, width, 0.5) for area, centre, width in peaks)
    return Spectrum(
        energy,
        intensity,
        region="C 1s",
        sample_name="synthetic PDI-H-COOH",
        metadata={"data_origin": "deterministic synthetic"},
    )
