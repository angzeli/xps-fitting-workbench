"""Run every public example in an isolated subprocess with a headless backend."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Run each public example in isolation and summarise pass/skip/fail counts.

    Args:
        argv: Optional output, overwrite, and calibrated-manifest arguments.

    Returns:
        One if any subprocess fails; otherwise zero. The experimental publication
        example is skipped unless its calibrated sample manifest is supplied.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/examples"))
    parser.add_argument(
        "--overwrite", action="store_true", help="Allow examples to replace their own existing outputs."
    )
    parser.add_argument(
        "--pdi-h-c1s-sample-manifest",
        type=Path,
        help="Sample manifest for the calibrated experimental example.",
    )
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    examples = sorted(path for path in (root / "examples").glob("*.py") if not path.name.startswith("_"))
    environment = dict(os.environ)
    # Make current sources importable and force non-interactive rendering in children.
    current_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, (str(root / "src"), current_pythonpath)))
    environment.setdefault("MPLBACKEND", "Agg")
    failures = []
    skipped = []
    for example in examples:
        if example.stem == "plot_pdi_h_cooh_c1s_publication" and not args.pdi_h_c1s_sample_manifest:
            skipped.append(example.name)
            print(f"SKIP {example.name} (no calibrated reviewed sample manifest supplied)")
            continue
        destination = args.output_dir / example.stem
        command = [sys.executable, str(example), "--output-dir", str(destination)]
        if example.stem == "plot_pdi_h_cooh_c1s_publication" and args.pdi_h_c1s_sample_manifest:
            command.extend(("--sample-manifest", str(args.pdi_h_c1s_sample_manifest)))
        if args.overwrite:
            command.append("--overwrite")
        completed = subprocess.run(command, cwd=root, env=environment, text=True, capture_output=True)
        state = "PASS" if completed.returncode == 0 else "FAIL"
        print(f"{state} {example.name}")
        if completed.returncode:
            failures.append(example.name)
            print(completed.stderr.strip() or completed.stdout.strip())
    passed = len(examples) - len(failures) - len(skipped)
    print(f"Summary: {passed} passed, {len(failures)} failed, {len(skipped)} skipped")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
