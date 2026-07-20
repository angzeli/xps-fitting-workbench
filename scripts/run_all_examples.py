"""Run every public example independently and fail if any example fails."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/examples"))
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
        completed = subprocess.run(command, cwd=root, env=environment, text=True, capture_output=True)
        state = "PASS" if completed.returncode == 0 else "FAIL"
        print(f"{state} {example.name}")
        if completed.returncode:
            failures.append(example.name); print(completed.stderr.strip() or completed.stdout.strip())
    print(f"Summary: {len(examples) - len(failures)} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
