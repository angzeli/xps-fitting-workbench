"""Command-line entry points."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from ._version import __version__
from .artifacts import validate_fit_bundle
from .calibration_workflow import calibrate_reviewed_sample, prepare_sample_calibration
from .cleanup import clean_generated
from .naming import make_output_name, result_output_name, validate_output_stem
from .plotting.configuration import load_plot_config
from .plotting.io import load_curve_result
from .plotting.recipes import plot_from_config, plot_series_from_config
from .project_workflow import (
    discover_fit_configs,
    ensure_sample_manifest,
    find_repository_root,
    fit_region_candidates,
    inspect_sample,
    sample_manifest_path,
    validate_sample,
)
from .publication import plot_publication_region
from .review import candidate_review_summary, review_candidate
from .sample_manifest import activate_reviewed_bundle
from .spectrum_artifacts import validate_spectrum_bundle


def _metadata_sources(values: list[str] | None, count: int) -> list[str | None]:
    if not values:
        return [None] * count
    if len(values) != count:
        raise ValueError("repeat --metadata once for each input source")
    return list(values)


def _print_paths(paths: dict[str, Path], *, dry_run: bool) -> None:
    prefix = "Would create" if dry_run else "Created"
    for path in paths.values():
        print(f"{prefix}: {path}")


def _json_output(value) -> None:
    print(json.dumps(value, indent=2, default=str))


def _repository(args: argparse.Namespace) -> Path:
    return find_repository_root(args.repository)


def _run_stored_plot(args: argparse.Namespace) -> int:
    config = load_plot_config(args.recipe)
    metadata = _metadata_sources(args.metadata, len(args.sources))
    results = [load_curve_result(source, details) for source, details in zip(args.sources, metadata)]
    if args.sample_label and len(args.sample_label) != len(results):
        raise ValueError("repeat --sample-label once for each input source")
    if args.output_name:
        config = replace(config, output_filename=validate_output_stem(args.output_name))
    elif config.output_filename == "xps_fit":
        if len(results) == 1:
            config = replace(config, output_filename=result_output_name(results[0], plot_type="plot"))
        else:
            generated = make_output_name(
                sample=f"{len(results)}-samples",
                region=config.core_level,
                model="comparison",
                plot_type="multipanel",
            )
            config = replace(config, output_filename=generated)
    if len(results) == 1:
        figure, _, paths = plot_from_config(
            results[0], config, args.output_dir, overwrite=args.overwrite, dry_run=args.dry_run
        )
    else:
        figure, _, paths = plot_series_from_config(
            results,
            config,
            args.output_dir,
            sample_labels=args.sample_label,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
    import matplotlib.pyplot as plt

    plt.close(figure)
    _print_paths(paths, dry_run=args.dry_run)
    return 0


def _run_inspect(args: argparse.Namespace) -> int:
    _json_output(inspect_sample(_repository(args), args.sample))
    return 0


def _run_fit_region(args: argparse.Namespace) -> int:
    result = fit_region_candidates(
        _repository(args),
        args.sample,
        args.region,
        configuration_paths=tuple(args.config or ()),
        overwrite_candidates=args.overwrite_candidates,
        overwrite_figures=args.overwrite_figures,
    )
    _json_output(result)
    return 0


def _run_fit_sample(args: argparse.Namespace) -> int:
    root = _repository(args)
    fitted: dict[str, object] = {}
    for region in ("C1s", "N1s", "O1s", "Cl2p"):
        configs = discover_fit_configs(root, args.sample, region)
        if configs:
            fitted[region] = fit_region_candidates(
                root,
                args.sample,
                region,
                configuration_paths=configs,
                overwrite_candidates=args.overwrite_candidates,
                overwrite_figures=args.overwrite_figures,
            )
    if not fitted:
        raise FileNotFoundError(f"no candidate fit configurations found for {args.sample}")
    _json_output({"sample": args.sample, "regions": fitted, "review_required": True})
    return 0


def _candidate_paths(root: Path, sample: str, region: str) -> list[Path]:
    from .artifacts import canonical_region

    return sorted((root / "artifacts" / "candidates" / sample / canonical_region(region)).glob("*.bundle"))


def _yes(prompt: str) -> bool:
    return input(f"{prompt} [y/N] ").strip().casefold() in {"y", "yes"}


def _run_review(args: argparse.Namespace) -> int:
    root = _repository(args)
    candidates = _candidate_paths(root, args.sample, args.region)
    if not candidates:
        raise FileNotFoundError(f"no persisted candidates found for {args.sample} {args.region}")
    summaries = [candidate_review_summary(path) for path in candidates]
    for index, summary in enumerate(summaries, 1):
        print(f"\n[{index}] {summary['model']}")
        print(json.dumps(summary, indent=2, default=str))
    print(f"\n[{len(candidates) + 1}] Cancel")
    if args.candidate:
        selected = next(
            (
                path
                for path, summary in zip(candidates, summaries)
                if path.name == args.candidate or summary["model"] == args.candidate
            ),
            None,
        )
        if selected is None:
            raise ValueError(f"candidate not found: {args.candidate}")
    else:
        choice = input("Choose a candidate number: ").strip()
        if not choice.isdigit() or int(choice) == len(candidates) + 1:
            print("Review cancelled; no reviewed artifact was created.")
            return 0
        if int(choice) < 1 or int(choice) > len(candidates):
            raise ValueError("invalid candidate selection")
        selected = candidates[int(choice) - 1]
    if not args.approve and not _yes(f"Approve {selected.name} as the reviewed scientific fit?"):
        print("Review cancelled; no reviewed artifact was created.")
        return 0
    reviewer = args.reviewer or input("Reviewer name: ").strip()
    checks = args.confirm_checks
    residual = checks or _yes("Residuals inspected and acceptable?")
    background = checks or _yes("Background inspected and acceptable?")
    assignments = checks or _yes("Component assignments inspected and acceptable?")
    constraints = checks or _yes("Constraints reviewed?")
    warnings = checks or _yes("Warnings inspected and acknowledged?")
    promotion = review_candidate(
        selected,
        root / "artifacts" / "reviewed",
        decision="accepted",
        reviewer=reviewer,
        notes=tuple(args.note or ()),
        residual_inspection_status="approved" if residual else "",
        background_approval_status="approved" if background else "",
        component_assignment_approval_status="approved" if assignments else "",
        constraints_reviewed=constraints,
        warnings_acknowledged=warnings,
        repository_root=root,
    )
    assert promotion is not None
    ensure_sample_manifest(root, args.sample)
    manifest = activate_reviewed_bundle(
        sample_manifest_path(root, args.sample),
        promotion.reviewed_bundle,
        repository_root=root,
        replace_active=args.replace_active,
    )
    _json_output(
        {
            "reviewed_bundle": str(promotion.reviewed_bundle),
            "review_record": str(promotion.review_record),
            "active_review_version": manifest.active_review_versions[promotion.record.region],
        }
    )
    return 0


def _run_calibrate(args: argparse.Namespace) -> int:
    root = _repository(args)
    manifest = sample_manifest_path(root, args.sample)
    plan = prepare_sample_calibration(
        manifest,
        reference_region=args.reference_region,
        reference_component=args.reference_component,
        reference_component_label=args.reference_component_label,
        target_energy_eV=args.target_energy,
        allow_incomplete=args.allow_incomplete,
        repository_root=root,
    )
    print(plan.format_text())
    if not args.yes and not _yes("Continue?"):
        print("Calibration cancelled; no files were written.")
        return 0
    reviewer = args.reviewer or input("Reviewer name: ").strip()
    rationale = args.rationale or input("Scientific rationale for this reference component: ").strip()
    outcome = calibrate_reviewed_sample(
        manifest,
        reference_region=args.reference_region,
        reference_component=args.reference_component,
        reference_component_label=args.reference_component_label,
        reviewer=reviewer,
        scientific_rationale=rationale,
        target_energy_eV=args.target_energy,
        allow_incomplete=args.allow_incomplete,
        confirmed=True,
        repository_root=root,
    )
    _json_output(
        {
            "calibration_record": str(outcome.calibration_record),
            "energy_offset_eV": outcome.record.energy_offset_eV,
            "calibrated_bundles": {key: str(value) for key, value in outcome.calibrated_bundles.items()},
        }
    )
    return 0


def _run_plot_region(args: argparse.Namespace) -> int:
    root = _repository(args)
    figure, _, paths, provenance = plot_publication_region(
        sample_manifest_path(root, args.sample),
        args.region,
        args.recipe,
        args.output_dir or root / "figures" / "final" / args.sample,
        repository_root=root,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    import matplotlib.pyplot as plt

    plt.close(figure)
    _print_paths(paths, dry_run=args.dry_run)
    print(f"Calibration offset: {provenance['energy_offset_eV']:+.8g} eV")
    print(f"Reviewed source: {provenance['reviewed_calibrated_bundle']}")
    return 0


def _run_plot_sample(args: argparse.Namespace) -> int:
    config = load_plot_config(args.recipe)
    if not config.core_level:
        raise ValueError("plot-sample recipe must identify a core_level")
    args.region = config.core_level
    return _run_plot_region(args)


def _run_validate_bundle(args: argparse.Namespace) -> int:
    path = Path(args.path)
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") == "xps-fitting-workbench-fit-bundle":
        report = validate_fit_bundle(
            path,
            require_calibrated=args.require_calibrated,
            repository_root=_repository(args),
        )
        print(report.format_text())
    else:
        report = validate_spectrum_bundle(
            path,
            require_calibrated=args.require_calibrated,
            repository_root=_repository(args),
        )
        _json_output(report.__dict__)
    return 0 if report.publication_eligible else 1


def _run_validate_sample(args: argparse.Namespace) -> int:
    result = validate_sample(
        _repository(args),
        args.sample,
        require_calibrated=args.require_calibrated,
    )
    _json_output(result)
    return 0 if result["valid"] else 1


def _run_cleanup(args: argparse.Namespace) -> int:
    files = clean_generated(_repository(args), dry_run=args.dry_run)
    prefix = "Would remove" if args.dry_run else "Removed"
    for path in files:
        print(f"{prefix}: {path}")
    print(f"{prefix} {len(files)} generated file(s).")
    return 0


def _run_wizard(args: argparse.Namespace) -> int:
    root = _repository(args)
    samples = sorted(path.name for path in (root / "example_data").iterdir() if path.is_dir())
    print("Available samples:")
    for index, sample in enumerate(samples, 1):
        print(f"[{index}] {sample}")
    print(f"[{len(samples) + 1}] Cancel")
    choice = input("Choose a sample number: ").strip()
    if not choice.isdigit() or int(choice) not in range(1, len(samples) + 1):
        print("Wizard cancelled; no files were changed.")
        return 0
    sample = samples[int(choice) - 1]
    _json_output(inspect_sample(root, sample))
    print("\nNext safe step:")
    print(f"  xps-fit fit-sample --sample {sample}")
    print("The wizard stops here so candidate fitting and scientific review remain explicit.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="xps-fit", description="Persist, review, calibrate, validate, and plot XPS results."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--repository", default=".", help="repository root or a directory inside it")
    subparsers = parser.add_subparsers(dest="command", required=True)
    plot_parser = subparsers.add_parser("plot", help="render one result or an ordered multipanel comparison")
    plot_parser.add_argument(
        "sources", nargs="+", help="fit bundle directory, full-result JSON, or CSV/XLSX curve table"
    )
    plot_parser.add_argument(
        "--metadata", action="append", help="metadata JSON paired with a CSV/XLSX source; repeat in source order"
    )
    plot_parser.add_argument("--recipe", required=True, help="validated plotting recipe JSON")
    plot_parser.add_argument("--output-dir", default=".", help="directory for created PNG/PDF figures")
    plot_parser.add_argument("--output-name", help="filesystem-safe output stem overriding the recipe")
    plot_parser.add_argument("--sample-label", action="append", help="panel label; repeat in source order")
    plot_parser.add_argument("--overwrite", action="store_true", help="replace an existing output with the same name")
    plot_parser.add_argument(
        "--dry-run", action="store_true", help="validate inputs and print planned paths without writing figures"
    )
    plot_parser.add_argument("--verbose", action="store_true", help="show a traceback for unexpected failures")

    inspect_parser = subparsers.add_parser("inspect-sample", help="inspect raw files and artifact states")
    inspect_parser.add_argument("--sample", required=True)

    fit_region_parser = subparsers.add_parser("fit-region", help="persist configured candidates before diagnostics")
    fit_region_parser.add_argument("--sample", required=True)
    fit_region_parser.add_argument("--region", required=True)
    fit_region_parser.add_argument("--config", action="append", help="candidate configuration; repeat as needed")
    fit_region_parser.add_argument("--overwrite-candidates", action="store_true")
    fit_region_parser.add_argument("--overwrite-figures", action="store_true")

    fit_sample_parser = subparsers.add_parser("fit-sample", help="fit every region with discovered configurations")
    fit_sample_parser.add_argument("--sample", required=True)
    fit_sample_parser.add_argument("--overwrite-candidates", action="store_true")
    fit_sample_parser.add_argument("--overwrite-figures", action="store_true")

    review_parser = subparsers.add_parser("review-region", help="approve one persisted candidate explicitly")
    review_parser.add_argument("--sample", required=True)
    review_parser.add_argument("--region", required=True)
    review_parser.add_argument("--candidate", help="candidate model name or bundle directory name")
    review_parser.add_argument("--reviewer")
    review_parser.add_argument("--note", action="append")
    review_parser.add_argument("--approve", action="store_true", help="explicitly approve the selected candidate")
    review_parser.add_argument(
        "--confirm-checks",
        action="store_true",
        help="confirm residual, background, assignment, constraint, and warning inspection",
    )
    review_parser.add_argument("--replace-active", action="store_true")

    calibrate_parser = subparsers.add_parser("calibrate-sample", help="apply one reviewed C 1s shift sample-wide")
    calibrate_parser.add_argument("--sample", required=True)
    calibrate_parser.add_argument("--reference-region", default="C1s")
    calibrate_parser.add_argument("--reference-component", required=True)
    calibrate_parser.add_argument("--reference-component-label", required=True)
    calibrate_parser.add_argument("--target-energy", type=float, default=284.8)
    calibrate_parser.add_argument("--reviewer")
    calibrate_parser.add_argument("--rationale")
    calibrate_parser.add_argument("--allow-incomplete", action="store_true")
    calibrate_parser.add_argument("--yes", action="store_true", help="confirm the printed calibration plan")

    plot_region_parser = subparsers.add_parser("plot-region", help="plot one calibrated reviewed region")
    plot_region_parser.add_argument("--sample", required=True)
    plot_region_parser.add_argument("--region", required=True)
    plot_region_parser.add_argument("--recipe", required=True)
    plot_region_parser.add_argument("--output-dir")
    plot_region_parser.add_argument("--overwrite", action="store_true")
    plot_region_parser.add_argument("--dry-run", action="store_true")

    plot_sample_parser = subparsers.add_parser("plot-sample", help="plot the recipe's calibrated sample region")
    plot_sample_parser.add_argument("--sample", required=True)
    plot_sample_parser.add_argument("--recipe", required=True)
    plot_sample_parser.add_argument("--output-dir")
    plot_sample_parser.add_argument("--overwrite", action="store_true")
    plot_sample_parser.add_argument("--dry-run", action="store_true")

    validate_bundle_parser = subparsers.add_parser("validate-bundle", help="audit one scientific artifact bundle")
    validate_bundle_parser.add_argument("path")
    validate_bundle_parser.add_argument("--require-calibrated", action="store_true")

    validate_sample_parser = subparsers.add_parser("validate-sample", help="audit linked sample artifacts")
    validate_sample_parser.add_argument("--sample", required=True)
    validate_sample_parser.add_argument("--require-calibrated", action="store_true")

    validate_calibration_parser = subparsers.add_parser(
        "validate-calibration", help="audit calibrated sample artifacts and their common record"
    )
    validate_calibration_parser.add_argument("--sample", required=True)
    validate_calibration_parser.set_defaults(require_calibrated=True)

    cleanup_parser = subparsers.add_parser("clean-generated", help="remove only allowlisted disposable outputs")
    cleanup_parser.add_argument("--dry-run", action="store_true")

    subparsers.add_parser("wizard", help="start the guided beginner workflow")
    args = parser.parse_args(argv)
    try:
        handlers = {
            "plot": _run_stored_plot,
            "inspect-sample": _run_inspect,
            "fit-region": _run_fit_region,
            "fit-sample": _run_fit_sample,
            "review-region": _run_review,
            "calibrate-sample": _run_calibrate,
            "plot-region": _run_plot_region,
            "plot-sample": _run_plot_sample,
            "validate-bundle": _run_validate_bundle,
            "validate-sample": _run_validate_sample,
            "validate-calibration": _run_validate_sample,
            "clean-generated": _run_cleanup,
            "wizard": _run_wizard,
        }
        return handlers[args.command](args)
    except Exception as exc:
        if getattr(args, "verbose", False):
            raise
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
