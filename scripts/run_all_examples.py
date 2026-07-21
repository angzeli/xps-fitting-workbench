"""Run every public example independently and fail if any example fails."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/examples"))
    parser.add_argument(
        "--overwrite", action="store_true", help="Allow examples to replace their own existing outputs."
    )
    parser.add_argument(
        "--pdi-h-c1s-fit-result", type=Path, help="Reviewed FitResult source for the experimental example."
    )
    parser.add_argument("--pdi-h-c1s-metadata", type=Path, help="Metadata JSON when that source is a curve table.")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    examples = sorted(path for path in (root / "examples").glob("*.py") if not path.name.startswith("_"))
    environment = dict(os.environ)
    current_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, (str(root / "src"), current_pythonpath)))
    environment.setdefault("MPLBACKEND", "Agg")
    failures = []
    for example in examples:
        destination = args.output_dir / example.stem
        command = [sys.executable, str(example), "--output-dir", str(destination)]
        if example.stem == "plot_pdi_h_cooh_c1s_publication" and args.pdi_h_c1s_fit_result:
            command.extend(("--fit-result", str(args.pdi_h_c1s_fit_result)))
            if args.pdi_h_c1s_metadata:
                command.extend(("--metadata", str(args.pdi_h_c1s_metadata)))
        if args.overwrite:
            command.append("--overwrite")
        completed = subprocess.run(command, cwd=root, env=environment, text=True, capture_output=True)
        state = "PASS" if completed.returncode == 0 else "FAIL"
        print(f"{state} {example.name}")
        if completed.returncode:
            failures.append(example.name)
            print(completed.stderr.strip() or completed.stdout.strip())
    print(f"Summary: {len(examples) - len(failures)} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
