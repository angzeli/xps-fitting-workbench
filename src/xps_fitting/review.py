"""Record explicit human decisions and promote candidates immutably."""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

import numpy as np

from ._version import __version__
from .artifacts import ArtifactDescriptor, canonical_region, portable_path, utc_now, validate_fit_bundle
from .export import load_fit_bundle, read_fit_bundle_manifest, save_fit_bundle
from .integrity import result_arrays_equal, sha256_file, sha256_json
from .naming import safe_slug

REVIEW_RECORD_SCHEMA_VERSION = 1
REJECTION_RECORD_SCHEMA_VERSION = 1
ReviewDecision = Literal["accepted", "cancelled"]


class _CorrelationRecord(TypedDict):
    """Typed high-correlation entry emitted by the reviewer summary."""

    parameter_1: str
    parameter_2: str
    correlation: float


@dataclass(frozen=True)
class ReviewRecord:
    """Record an accepted human review and the candidate bundle it endorses.

    The candidate identifier and hashes bind the decision to immutable source,
    configuration, and bundle contents; ``review_version`` selects a new record
    rather than replacing a previous decision.
    """

    sample: str
    region: str
    candidate_source: str
    selected_model: str
    decision: str
    reviewer: str
    review_date: str
    notes: tuple[str, ...]
    residual_inspection_status: str
    background_approval_status: str
    component_assignment_approval_status: str
    constraints_reviewed: bool
    warnings_acknowledged: bool
    source_sha256: str
    configuration_sha256: str
    candidate_artifact_id: str
    candidate_bundle_sha256: str
    review_version: int
    software_version: str = __version__
    review_status: str = "reviewed"
    schema_version: int = REVIEW_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Require all scientific review gates for an accepted promotion."""
        if self.decision != "accepted" or self.review_status != "reviewed":
            raise ValueError("a durable review record must describe an accepted decision")
        if not self.reviewer.strip():
            raise ValueError("reviewer is required")
        for name, value in (
            ("residual inspection", self.residual_inspection_status),
            ("background approval", self.background_approval_status),
            ("component assignment approval", self.component_assignment_approval_status),
        ):
            if value not in {"approved", "reviewed_with_concerns"}:
                raise ValueError(f"{name} must be approved or reviewed_with_concerns")
        if not self.constraints_reviewed or not self.warnings_acknowledged:
            raise ValueError("constraints and warnings must be explicitly reviewed")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible review record."""
        return asdict(self)


@dataclass(frozen=True)
class ReviewPromotion:
    """Identify the immutable reviewed bundle and record created by promotion."""

    reviewed_bundle: Path
    review_record: Path
    version: int
    record: ReviewRecord


@dataclass(frozen=True)
class RejectionRecord:
    """Record an explicit decision to reject every candidate for one region."""

    sample: str
    region: str
    candidate_sources: tuple[str, ...]
    candidate_models: tuple[str, ...]
    candidate_bundle_sha256: dict[str, str]
    reviewer: str
    review_date: str
    notes: tuple[str, ...]
    rejection_version: int
    decision: str = "rejected_all"
    review_status: str = "rejected"
    software_version: str = __version__
    schema_version: int = REJECTION_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.reviewer.strip():
            raise ValueError("reviewer is required")
        if not self.candidate_sources:
            raise ValueError("at least one rejected candidate is required")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible rejection record."""
        return asdict(self)


@dataclass(frozen=True)
class ReviewRejection:
    """Identify the durable record created by a reject-all decision."""

    rejection_record: Path
    version: int
    record: RejectionRecord


def load_review_record(path: str | Path) -> ReviewRecord:
    """Load and validate an accepted review record from JSON."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data["notes"] = tuple(data.get("notes", ()))
    return ReviewRecord(**data)


def _bundle_fingerprint(manifest: dict[str, Any]) -> str:
    """Hash the artifact descriptor and recorded bundle-member integrity values."""
    return sha256_json({"artifact": manifest.get("artifact"), "integrity": manifest.get("integrity")})


def _next_review_version(directory: Path, region: str) -> int:
    """Return the next unused positive reviewed-bundle version for a region."""
    prefix = f"{canonical_region(region)}.review-v"
    versions = []
    for candidate in directory.glob(f"{prefix}*.bundle"):
        suffix = candidate.name.removeprefix(prefix).removesuffix(".bundle")
        if suffix.isdigit():
            versions.append(int(suffix))
    return max(versions, default=0) + 1


def _parse_optional_bounds(bounds: Any) -> tuple[float | None, float | None] | None:
    """Parse optional two-sided bounds without assigning values to open ends."""
    if not isinstance(bounds, list | tuple) or len(bounds) != 2:
        return None
    lower, upper = bounds
    return (None if lower is None else float(lower), None if upper is None else float(upper))


def candidate_review_summary(candidate_bundle: str | Path) -> dict[str, Any]:
    """Return numerical evidence for review without selecting or approving a model.

    Centres and FWHM values use eV; areas retain the fit's source-defined scale.
    Correlations are unique unordered parameter pairs sorted by decreasing
    absolute value, preserving values and tie order from the stored matrix.
    """
    result = load_fit_bundle(candidate_bundle)
    areas = {label: float(result.fitted_parameters.get(f"{label}.area", 0.0)) for label in result.components}
    total_area = sum(areas.values())
    high_correlations: list[_CorrelationRecord] = []
    seen_pairs: set[tuple[str, str]] = set()
    for first, row in result.correlation_matrix.items():
        for second, value in row.items():
            pair = (min(first, second), max(first, second))
            if first != second and pair not in seen_pairs and abs(float(value)) >= 0.9:
                seen_pairs.add(pair)
                high_correlations.append({"parameter_1": pair[0], "parameter_2": pair[1], "correlation": float(value)})
    high_correlations.sort(key=lambda item: abs(item["correlation"]), reverse=True)
    components = []
    bound_hits = []
    peaks = {str(peak.get("label")): peak for peak in result.configuration.get("peaks", ())}
    for label in result.components:
        parameter_bounds: dict[str, list[float | str]] = {}
        components.append(
            {
                "label": label,
                "centre_eV": result.fitted_parameters.get(f"{label}.centre"),
                "fwhm_eV": result.fitted_parameters.get(f"{label}.fwhm"),
                "area": areas[label],
                "area_fraction": areas[label] / total_area if total_area > 0 else None,
                "bounds": parameter_bounds,
            }
        )
        peak = peaks.get(label, {})
        for parameter in ("centre", "fwhm", "area", "lorentzian_fraction"):
            fitted_value = result.fitted_parameters.get(f"{label}.{parameter}")
            bounds = _parse_optional_bounds(peak.get(f"{parameter}_bounds"))
            if fitted_value is None or bounds is None:
                continue
            lower, upper = bounds
            parameter_bounds[parameter] = ["unbounded" if value is None else value for value in bounds]
            if lower is None and upper is None:
                continue
            numeric_value = float(fitted_value)
            finite_bound = cast(float, lower if lower is not None else upper)
            tolerance = (
                max(1e-8, abs(upper - lower) * 1e-5)
                if lower is not None and upper is not None
                else max(1e-8, max(abs(numeric_value), abs(finite_bound)) * 1e-5)
            )
            if lower is not None and abs(numeric_value - lower) <= tolerance:
                bound_hits.append({"parameter": f"{label}.{parameter}", "bound": "lower", "value": float(fitted_value)})
            elif upper is not None and abs(numeric_value - upper) <= tolerance:
                bound_hits.append({"parameter": f"{label}.{parameter}", "bound": "upper", "value": float(fitted_value)})
    return {
        "bundle": str(Path(candidate_bundle).resolve()),
        "model": result.configuration.get("name", "unknown"),
        "background": result.configuration.get("background", "unknown"),
        "components": components,
        "residual": {
            "mean": float(np.mean(result.residual)),
            "rms": float(np.sqrt(np.mean(np.square(result.residual)))),
            "max_abs": float(np.max(np.abs(result.residual))),
        },
        "fit_statistics": copy.deepcopy(result.fit_statistics),
        "warnings": list(result.warnings),
        "bound_hits": bound_hits,
        "convergence": copy.deepcopy(result.convergence),
        "high_parameter_correlations": high_correlations,
    }


def reject_all_candidates(
    candidate_bundles: tuple[str | Path, ...],
    reviewed_root: str | Path,
    *,
    reviewer: str,
    notes: tuple[str, ...] = (),
    repository_root: str | Path | None = None,
    review_date: str | None = None,
) -> ReviewRejection:
    """Persist a versioned rejection without promoting or modifying candidates."""
    if not candidate_bundles:
        raise ValueError("at least one candidate is required")
    paths = tuple(Path(path).resolve() for path in candidate_bundles)
    descriptors = []
    fingerprints = {}
    for path in paths:
        report = validate_fit_bundle(path, repository_root=repository_root)
        if report.errors:
            raise ValueError(f"candidate bundle failed validation: {path}\n" + "\n".join(report.errors))
        manifest = read_fit_bundle_manifest(path)
        descriptor = ArtifactDescriptor.from_dict(dict(manifest.get("artifact") or {}))
        if descriptor.state != "candidate" or descriptor.review_status != "candidate":
            raise ValueError("rejection requires candidate artifacts")
        descriptors.append(descriptor)
        fingerprints[descriptor.artifact_id] = _bundle_fingerprint(manifest)
    sample_regions = {(item.sample, item.region) for item in descriptors}
    if len(sample_regions) != 1:
        raise ValueError("all rejected candidates must belong to one sample and region")
    sample, region = sample_regions.pop()
    record_dir = Path(reviewed_root) / sample / "review_records"
    versions = []
    prefix = f"{region}.rejection-v"
    for existing in record_dir.glob(f"{prefix}*.json"):
        suffix = existing.stem.removeprefix(prefix)
        if suffix.isdigit():
            versions.append(int(suffix))
    version = max(versions, default=0) + 1
    record = RejectionRecord(
        sample=sample,
        region=region,
        candidate_sources=tuple(portable_path(path, repository_root) for path in paths),
        candidate_models=tuple(item.model for item in descriptors),
        candidate_bundle_sha256=fingerprints,
        reviewer=reviewer,
        review_date=review_date or utc_now(),
        notes=notes,
        rejection_version=version,
    )
    record_path = record_dir / f"{region}.rejection-v{version}.json"
    record_dir.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(record.to_dict(), indent=2) + "\n", encoding="utf-8")
    return ReviewRejection(record_path, version, record)


def review_candidate(
    candidate_bundle: str | Path,
    reviewed_root: str | Path,
    *,
    decision: ReviewDecision,
    reviewer: str = "",
    notes: tuple[str, ...] = (),
    residual_inspection_status: str = "",
    background_approval_status: str = "",
    component_assignment_approval_status: str = "",
    constraints_reviewed: bool = False,
    warnings_acknowledged: bool = False,
    repository_root: str | Path | None = None,
    review_date: str | None = None,
    version: int | None = None,
) -> ReviewPromotion | None:
    """Promote a candidate into a new reviewed version; cancellation writes nothing.

    Promotion validates stored evidence, records the accepted decision, and writes
    a distinct reviewed version. Existing reviewed artifacts are never replaced.
    """
    if decision == "cancelled":
        return None
    candidate_path = Path(candidate_bundle).resolve()
    report = validate_fit_bundle(candidate_path, repository_root=repository_root)
    if report.errors:
        raise ValueError("candidate bundle failed validation:\n" + "\n".join(report.errors))
    blockers = [reason for reason in report.publication_reasons if "has not been scientifically reviewed" not in reason]
    if blockers:
        raise ValueError("candidate bundle cannot be promoted:\n" + "\n".join(blockers))
    manifest = read_fit_bundle_manifest(candidate_path)
    descriptor = ArtifactDescriptor.from_dict(dict(manifest.get("artifact") or {}))
    if descriptor.state != "candidate" or descriptor.review_status != "candidate":
        raise ValueError("review promotion requires a candidate artifact")
    candidate_result = load_fit_bundle(candidate_path)
    root = Path(reviewed_root)
    uncalibrated_dir = root / descriptor.sample / "uncalibrated"
    record_dir = root / descriptor.sample / "review_records"
    selected_version = version or _next_review_version(uncalibrated_dir, descriptor.region)
    if selected_version < 1:
        raise ValueError("review version must be positive")
    bundle_path = uncalibrated_dir / f"{descriptor.region}.review-v{selected_version}.bundle"
    record_path = record_dir / f"{descriptor.region}.review-v{selected_version}.json"
    if bundle_path.exists() or record_path.exists():
        raise FileExistsError(
            f"review version {selected_version} already exists; create a new version instead of overwriting it"
        )
    timestamp = review_date or utc_now()
    record = ReviewRecord(
        sample=descriptor.sample,
        region=descriptor.region,
        candidate_source=portable_path(candidate_path, repository_root),
        selected_model=descriptor.model,
        decision="accepted",
        reviewer=reviewer,
        review_date=timestamp,
        notes=tuple(notes),
        residual_inspection_status=residual_inspection_status,
        background_approval_status=background_approval_status,
        component_assignment_approval_status=component_assignment_approval_status,
        constraints_reviewed=constraints_reviewed,
        warnings_acknowledged=warnings_acknowledged,
        source_sha256=descriptor.source_sha256,
        configuration_sha256=descriptor.configuration_sha256,
        candidate_artifact_id=descriptor.artifact_id,
        candidate_bundle_sha256=_bundle_fingerprint(manifest),
        review_version=selected_version,
    )
    reviewed = copy.deepcopy(candidate_result)
    reviewed_id = f"{safe_slug(descriptor.sample)}-{safe_slug(descriptor.region)}-review-v{selected_version}"
    record_reference = portable_path(record_path, repository_root)
    reviewed.metadata.update(
        {
            "artifact_id": reviewed_id,
            "artifact_state": "reviewed",
            "review_status": "reviewed",
            "review_version": selected_version,
            "review_record": record_reference,
            "reviewer": reviewer,
            "review_date": timestamp,
            "calibration_status": "uncalibrated",
            "publication_eligible": False,
        }
    )
    record_dir.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(record.to_dict(), indent=2) + "\n", encoding="utf-8")
    reviewed_descriptor = ArtifactDescriptor(
        artifact_id=reviewed_id,
        state="reviewed",
        sample=descriptor.sample,
        region=descriptor.region,
        model=descriptor.model,
        created_at=timestamp,
        data_origin=descriptor.data_origin,
        source_path=descriptor.source_path,
        source_sha256=descriptor.source_sha256,
        configuration_sha256=descriptor.configuration_sha256,
        review_status="reviewed",
        calibration_status="uncalibrated",
        source_point_count=descriptor.source_point_count,
        lineage={
            "parent_artifact_id": descriptor.artifact_id,
            "candidate_bundle_sha256": record.candidate_bundle_sha256,
            "review_record_sha256": sha256_file(record_path),
            "review_version": selected_version,
        },
        review_record=record_reference,
    )
    try:
        save_fit_bundle(reviewed, bundle_path, artifact=reviewed_descriptor.to_dict())
    except Exception:
        record_path.unlink(missing_ok=True)
        raise
    reloaded = load_fit_bundle(bundle_path)
    if not result_arrays_equal(candidate_result, reloaded):
        raise RuntimeError("review promotion changed FitResult arrays")
    return ReviewPromotion(bundle_path, record_path, selected_version, record)
