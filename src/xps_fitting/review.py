"""Explicit human review and immutable candidate promotion."""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

from ._version import __version__
from .artifacts import ArtifactDescriptor, canonical_region, portable_path, utc_now, validate_fit_bundle
from .export import load_fit_bundle, read_fit_bundle_manifest, save_fit_bundle
from .integrity import result_arrays_equal, sha256_file, sha256_json
from .naming import safe_slug

REVIEW_RECORD_SCHEMA_VERSION = 1
ReviewDecision = Literal["accepted", "cancelled"]


@dataclass(frozen=True)
class ReviewRecord:
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
        return asdict(self)


@dataclass(frozen=True)
class ReviewPromotion:
    reviewed_bundle: Path
    review_record: Path
    version: int
    record: ReviewRecord


def load_review_record(path: str | Path) -> ReviewRecord:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data["notes"] = tuple(data.get("notes", ()))
    return ReviewRecord(**data)


def _bundle_fingerprint(manifest: dict[str, Any]) -> str:
    return sha256_json({"artifact": manifest.get("artifact"), "integrity": manifest.get("integrity")})


def _next_review_version(directory: Path, region: str) -> int:
    prefix = f"{canonical_region(region)}.review-v"
    versions = []
    for candidate in directory.glob(f"{prefix}*.bundle"):
        suffix = candidate.name.removeprefix(prefix).removesuffix(".bundle")
        if suffix.isdigit():
            versions.append(int(suffix))
    return max(versions, default=0) + 1


def candidate_review_summary(candidate_bundle: str | Path) -> dict[str, Any]:
    """Return the numerical evidence a reviewer needs without selecting a model."""
    result = load_fit_bundle(candidate_bundle)
    areas = {label: float(result.fitted_parameters.get(f"{label}.area", 0.0)) for label in result.components}
    total_area = sum(areas.values())
    components = []
    for label in result.components:
        components.append(
            {
                "label": label,
                "centre_eV": result.fitted_parameters.get(f"{label}.centre"),
                "fwhm_eV": result.fitted_parameters.get(f"{label}.fwhm"),
                "area": areas[label],
                "area_fraction": areas[label] / total_area if total_area > 0 else None,
            }
        )
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
        "convergence": copy.deepcopy(result.convergence),
        "parameter_correlations": copy.deepcopy(result.correlation_matrix),
    }


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
    """Promote a candidate into a new reviewed version; cancellation writes nothing."""
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
