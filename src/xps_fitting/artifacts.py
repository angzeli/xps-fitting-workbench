"""Durable scientific FitResult artifacts and publication eligibility."""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .export import load_fit_bundle, read_fit_bundle_manifest, save_fit_bundle
from .integrity import result_identity_metrics, sha256_file, sha256_json, validate_result_integrity
from .naming import safe_slug
from .result import FitResult

ARTIFACT_SCHEMA_VERSION = 1
ARTIFACT_STATES = {"candidate", "reviewed"}
CALIBRATION_STATES = {"uncalibrated", "calibrated"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_region(value: str) -> str:
    compact = "".join(character for character in value if character.isalnum()).casefold()
    aliases = {"c1s": "C1s", "n1s": "N1s", "o1s": "O1s", "cl2p": "Cl2p", "survey": "Survey"}
    return aliases.get(compact, value.strip().replace(" ", ""))


def display_region(value: str) -> str:
    canonical = canonical_region(value)
    return {"C1s": "C 1s", "N1s": "N 1s", "O1s": "O 1s", "Cl2p": "Cl 2p"}.get(canonical, canonical)


def portable_path(path: str | Path, repository_root: str | Path | None = None) -> str:
    resolved = Path(path).resolve()
    root = Path(repository_root).resolve() if repository_root is not None else None
    if root is not None and resolved.is_relative_to(root):
        return resolved.relative_to(root).as_posix()
    return str(resolved)


@dataclass(frozen=True)
class ArtifactDescriptor:
    artifact_id: str
    state: str
    sample: str
    region: str
    model: str
    created_at: str
    data_origin: str
    source_path: str
    source_sha256: str
    configuration_sha256: str
    review_status: str
    calibration_status: str
    source_point_count: int
    lineage: dict[str, Any] = field(default_factory=dict)
    review_record: str | None = None
    calibration_record: str | None = None
    schema_version: int = ARTIFACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.state not in ARTIFACT_STATES:
            raise ValueError(f"unsupported artifact state: {self.state}")
        if self.calibration_status not in CALIBRATION_STATES:
            raise ValueError(f"unsupported calibration state: {self.calibration_status}")
        if not self.sample or not self.region or not self.model:
            raise ValueError("artifact sample, region, and model must be non-empty")
        if len(self.source_sha256) != 64 or len(self.configuration_sha256) != 64:
            raise ValueError("artifact source and configuration SHA-256 values are required")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source"] = {
            "path": data.pop("source_path"),
            "sha256": data.pop("source_sha256"),
            "point_count": data.pop("source_point_count"),
        }
        data["configuration"] = {"sha256": data.pop("configuration_sha256")}
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtifactDescriptor":
        source = data.get("source", {})
        configuration = data.get("configuration", {})
        return cls(
            artifact_id=str(data["artifact_id"]),
            state=str(data["state"]),
            sample=str(data["sample"]),
            region=canonical_region(str(data["region"])),
            model=str(data["model"]),
            created_at=str(data["created_at"]),
            data_origin=str(data["data_origin"]),
            source_path=str(source["path"]),
            source_sha256=str(source["sha256"]),
            source_point_count=int(source["point_count"]),
            configuration_sha256=str(configuration["sha256"]),
            review_status=str(data["review_status"]),
            calibration_status=str(data["calibration_status"]),
            lineage=dict(data.get("lineage", {})),
            review_record=data.get("review_record"),
            calibration_record=data.get("calibration_record"),
            schema_version=int(data.get("schema_version", 0)),
        )


@dataclass(frozen=True)
class BundleValidationReport:
    bundle_path: str
    classification: str
    sample: str
    region: str
    model: str
    source_file: str
    source_sha256: str
    point_count: int
    energy_min_eV: float
    energy_max_eV: float
    intensity_min: float
    intensity_max: float
    max_abs_raw_minus_total: float
    background_min: float
    background_max: float
    component_envelope_error: float
    residual_reconstruction_error: float
    artifact_state: str
    review_status: str
    calibration_status: str
    publication_eligible: bool
    errors: tuple[str, ...] = ()
    publication_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def format_text(self) -> str:
        rows = [
            f"Bundle: {self.bundle_path}",
            f"Classification: {self.classification}",
            f"Sample: {self.sample or 'unknown'}",
            f"Region: {self.region or 'unknown'}",
            f"Model: {self.model or 'unknown'}",
            f"Source file: {self.source_file or 'unknown'}",
            f"Source SHA-256: {self.source_sha256 or 'missing'}",
            f"Points: {self.point_count}",
            f"Energy range: {self.energy_min_eV:.6g} to {self.energy_max_eV:.6g} eV",
            f"Intensity range: {self.intensity_min:.6g} to {self.intensity_max:.6g}",
            f"max(abs(raw - total)): {self.max_abs_raw_minus_total:.8g}",
            f"Background min/max: {self.background_min:.8g} / {self.background_max:.8g}",
            f"Component-envelope error: {self.component_envelope_error:.8g}",
            f"Residual reconstruction error: {self.residual_reconstruction_error:.8g}",
            f"Review state: {self.review_status}",
            f"Calibration state: {self.calibration_status}",
            f"Publication eligible: {'yes' if self.publication_eligible else 'no'}",
        ]
        rows.extend(f"ERROR: {message}" for message in self.errors)
        rows.extend(f"NOT PUBLICATION ELIGIBLE: {message}" for message in self.publication_reasons)
        rows.extend(f"WARNING: {message}" for message in self.warnings)
        return "\n".join(rows)


def classify_origin(value: object) -> str:
    origin = str(value or "").strip().casefold()
    if any(marker in origin for marker in ("synthetic", "fixture", "generated")):
        return "synthetic"
    if origin == "experimental":
        return "experimental"
    return "unclassified"


def fit_configuration_sha256(result: FitResult) -> str:
    """Hash the JSON-safe configuration representation stored in a bundle."""
    return sha256_json(result.to_dict()["configuration"])


def _descriptor_for_candidate(
    result: FitResult,
    *,
    sample: str,
    region: str,
    source_path: str | Path,
    repository_root: str | Path | None,
    created_at: str | None,
) -> ArtifactDescriptor:
    source = Path(source_path)
    if not source.is_file():
        raise FileNotFoundError(f"experimental source file is missing: {source}")
    if classify_origin(result.metadata.get("data_origin")) != "experimental":
        raise ValueError("candidate artifacts require explicit data_origin='experimental'")
    timestamp = created_at or utc_now()
    configuration_sha256 = fit_configuration_sha256(result)
    source_sha256 = sha256_file(source)
    identity = sha256_json(
        {
            "sample": sample,
            "region": canonical_region(region),
            "model": result.configuration.get("name", "model"),
            "source_sha256": source_sha256,
            "configuration_sha256": configuration_sha256,
            "created_at": timestamp,
        }
    )[:16]
    return ArtifactDescriptor(
        artifact_id=f"{safe_slug(sample)}-{safe_slug(region)}-{identity}",
        state="candidate",
        sample=sample,
        region=canonical_region(region),
        model=str(result.configuration.get("name") or "model"),
        created_at=timestamp,
        data_origin="experimental",
        source_path=portable_path(source, repository_root),
        source_sha256=source_sha256,
        configuration_sha256=configuration_sha256,
        review_status="candidate",
        calibration_status="uncalibrated",
        source_point_count=int(result.energy.size),
        lineage={
            "historical_result_recovered": False,
            "review_generation": "new_review",
            "replaces_unrecoverable_historical_plot": True,
        },
    )


def save_candidate_bundle(
    result: FitResult,
    directory: str | Path,
    *,
    sample: str,
    region: str,
    source_path: str | Path,
    repository_root: str | Path | None = None,
    created_at: str | None = None,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Persist an experimental candidate without mutating the in-memory result."""
    validate_result_integrity(result)
    descriptor = _descriptor_for_candidate(
        result,
        sample=sample,
        region=region,
        source_path=source_path,
        repository_root=repository_root,
        created_at=created_at,
    )
    stored = copy.deepcopy(result)
    stored.metadata.update(
        {
            "artifact_id": descriptor.artifact_id,
            "artifact_state": descriptor.state,
            "review_status": descriptor.review_status,
            "calibration_status": descriptor.calibration_status,
            "publication_eligible": False,
            "sample_name": descriptor.sample,
            "region": descriptor.region,
            "source_file": descriptor.source_path,
            "source_sha256": descriptor.source_sha256,
            "configuration_sha256": descriptor.configuration_sha256,
            "artifact_created_at": descriptor.created_at,
            **descriptor.lineage,
        }
    )
    return save_fit_bundle(stored, directory, artifact=descriptor.to_dict(), overwrite=overwrite)


def _resolve_source(path: str, bundle: Path, repository_root: str | Path | None) -> Path | None:
    source = Path(path)
    if source.is_absolute():
        return source if source.is_file() else None
    roots = []
    if repository_root is not None:
        roots.append(Path(repository_root))
    roots.extend(parent for parent in bundle.resolve().parents if (parent / "pyproject.toml").is_file())
    roots.append(bundle.parent)
    for root in roots:
        candidate = (root / source).resolve()
        if candidate.is_file():
            return candidate
    return None


def bundle_scientific_sha256(directory: str | Path) -> str:
    """Hash a bundle's immutable identity and member-file integrity records."""
    manifest = json.loads((Path(directory) / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") not in {
        "xps-fitting-workbench-fit-bundle",
        "xps-fitting-workbench-spectrum-bundle",
    }:
        raise ValueError(f"unsupported scientific artifact bundle: {directory}")
    artifact = manifest.get("artifact") or {}
    return sha256_json(
        {
            "artifact_id": artifact.get("artifact_id"),
            "integrity": manifest.get("integrity", {}),
        }
    )


def validate_fit_bundle(
    directory: str | Path,
    *,
    require_calibrated: bool = False,
    repository_root: str | Path | None = None,
) -> BundleValidationReport:
    """Audit a bundle and derive publication eligibility from stored evidence."""
    bundle = Path(directory).resolve()
    manifest = read_fit_bundle_manifest(bundle)
    result = load_fit_bundle(bundle)
    errors: list[str] = []
    publication_reasons: list[str] = []
    warnings: list[str] = list(result.warnings)
    artifact_data = manifest.get("artifact")
    descriptor: ArtifactDescriptor | None = None
    if artifact_data is None:
        publication_reasons.append("legacy bundle has no scientific artifact descriptor")
    else:
        try:
            descriptor = ArtifactDescriptor.from_dict(dict(artifact_data))
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"invalid artifact descriptor: {exc}")
    classification = classify_origin(result.metadata.get("data_origin"))
    if classification != "experimental":
        publication_reasons.append(f"data origin is {classification}, not experimental")
    try:
        validate_result_integrity(result)
    except ValueError as exc:
        errors.append(str(exc))
    if np.allclose(result.raw_intensity, result.total_fit, rtol=1e-10, atol=1e-12):
        publication_reasons.append("raw_intensity is identical to total_fit")
    background_span = float(np.ptp(result.background))
    background_scale = max(float(np.max(np.abs(result.background))), 1.0)
    if background_span <= 1e-10 * background_scale:
        publication_reasons.append("background is absent or numerically trivial")
    if not result.components:
        errors.append("bundle has no fitted component arrays")
    missing_centres = [label for label in result.components if f"{label}.centre" not in result.fitted_parameters]
    if missing_centres:
        errors.append("missing fitted centres: " + ", ".join(sorted(missing_centres)))
    sample = str(result.metadata.get("sample_name") or "")
    region = canonical_region(str(result.metadata.get("region") or result.configuration.get("region") or ""))
    model = str(result.configuration.get("name") or "")
    source_file = str(result.metadata.get("source_file") or "")
    source_sha256 = str(result.metadata.get("source_sha256") or "")
    state = "legacy"
    review_status = str(result.metadata.get("review_status") or "legacy")
    calibration_status = str(result.metadata.get("calibration_status") or "unknown")
    if descriptor is not None:
        state = descriptor.state
        if sample != descriptor.sample:
            errors.append("sample identity differs between metadata and manifest")
        if region != descriptor.region:
            errors.append("region identity differs between metadata and manifest")
        if model != descriptor.model:
            errors.append("model identity differs between configuration and manifest")
        if descriptor.configuration_sha256 != fit_configuration_sha256(result):
            errors.append("configuration SHA-256 does not match stored configuration")
        resolved_source = _resolve_source(descriptor.source_path, bundle, repository_root)
        if resolved_source is None:
            errors.append("source file does not resolve from recorded provenance")
        elif sha256_file(resolved_source) != descriptor.source_sha256:
            errors.append("source SHA-256 does not match the recorded raw file")
        if descriptor.source_point_count != result.energy.size:
            errors.append("point count differs from the artifact source record")
        source_file = descriptor.source_path
        source_sha256 = descriptor.source_sha256
        review_status = descriptor.review_status
        calibration_status = descriptor.calibration_status
        if state != "reviewed" or review_status != "reviewed":
            publication_reasons.append("artifact has not been scientifically reviewed")
        if state == "reviewed" and not descriptor.review_record:
            errors.append("reviewed artifact has no review record")
        elif state == "reviewed" and descriptor.review_record:
            resolved_review = _resolve_source(descriptor.review_record, bundle, repository_root)
            if resolved_review is None:
                errors.append("review record does not resolve from artifact provenance")
            else:
                expected_review_sha256 = descriptor.lineage.get("review_record_sha256")
                if not expected_review_sha256:
                    errors.append("review record SHA-256 is missing from artifact lineage")
                elif sha256_file(resolved_review) != expected_review_sha256:
                    errors.append("review record SHA-256 does not match the artifact lineage")
                try:
                    review = json.loads(resolved_review.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    errors.append(f"review record is unreadable: {exc}")
                else:
                    if review.get("decision") != "accepted" or review.get("review_status") != "reviewed":
                        errors.append("review record does not contain an accepted decision")
                    if (
                        review.get("sample") != descriptor.sample
                        or canonical_region(str(review.get("region"))) != region
                    ):
                        errors.append("review record sample or region does not match the bundle")
                    if review.get("selected_model") != descriptor.model:
                        errors.append("review record model does not match the bundle")
                    if review.get("source_sha256") != descriptor.source_sha256:
                        errors.append("review record source SHA-256 does not match the bundle")
                    reviewed_configuration_sha256 = descriptor.lineage.get(
                        "reviewed_configuration_sha256", descriptor.configuration_sha256
                    )
                    if review.get("configuration_sha256") != reviewed_configuration_sha256:
                        errors.append("review record configuration SHA-256 does not match the bundle")
                    parent_id = descriptor.lineage.get(
                        "review_candidate_artifact_id", descriptor.lineage.get("parent_artifact_id")
                    )
                    if review.get("candidate_artifact_id") != parent_id:
                        errors.append("review record candidate lineage does not match the bundle")
        if require_calibrated and calibration_status != "calibrated":
            publication_reasons.append("publication workflow requires a calibrated reviewed artifact")
        if calibration_status == "calibrated" and not descriptor.calibration_record:
            errors.append("calibrated artifact has no calibration record")
        elif calibration_status == "calibrated" and descriptor.calibration_record:
            resolved_calibration = _resolve_source(descriptor.calibration_record, bundle, repository_root)
            if resolved_calibration is None:
                errors.append("calibration record does not resolve from artifact provenance")
            else:
                expected_calibration_sha256 = descriptor.lineage.get("calibration_record_sha256")
                if not expected_calibration_sha256:
                    errors.append("calibration record SHA-256 is missing from artifact lineage")
                elif sha256_file(resolved_calibration) != expected_calibration_sha256:
                    errors.append("calibration record SHA-256 does not match the artifact lineage")
                try:
                    calibration = json.loads(resolved_calibration.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    errors.append(f"calibration record is unreadable: {exc}")
                else:
                    calibration_metadata = result.metadata.get("binding_energy_calibration", {})
                    if calibration.get("sample") != descriptor.sample:
                        errors.append("calibration record sample does not match the bundle")
                    if descriptor.region not in calibration.get("applied_regions", []):
                        errors.append("calibration record does not include the bundle region")
                    if calibration.get("energy_offset_eV") != calibration_metadata.get("offset_eV"):
                        errors.append("calibration record offset does not match bundle metadata")
    metrics = result_identity_metrics(result)
    return BundleValidationReport(
        bundle_path=str(bundle),
        classification=classification,
        sample=sample,
        region=region,
        model=model,
        source_file=source_file,
        source_sha256=source_sha256,
        point_count=int(result.energy.size),
        energy_min_eV=float(np.min(result.energy)),
        energy_max_eV=float(np.max(result.energy)),
        intensity_min=float(np.min(result.raw_intensity)),
        intensity_max=float(np.max(result.raw_intensity)),
        max_abs_raw_minus_total=float(np.max(np.abs(result.raw_intensity - result.total_fit))),
        background_min=float(np.min(result.background)),
        background_max=float(np.max(result.background)),
        component_envelope_error=metrics["max_abs_component_envelope_error"],
        residual_reconstruction_error=metrics["max_abs_residual_reconstruction_error"],
        artifact_state=state,
        review_status=review_status,
        calibration_status=calibration_status,
        publication_eligible=not errors and not publication_reasons,
        errors=tuple(errors),
        publication_reasons=tuple(publication_reasons),
        warnings=tuple(warnings),
    )


def load_publication_bundle(
    directory: str | Path,
    *,
    require_calibrated: bool = True,
    repository_root: str | Path | None = None,
) -> tuple[FitResult, BundleValidationReport]:
    """Load a result only after it passes the strict final-publication gate."""
    report = validate_fit_bundle(
        directory,
        require_calibrated=require_calibrated,
        repository_root=repository_root,
    )
    if not report.publication_eligible:
        reasons = (*report.errors, *report.publication_reasons)
        raise ValueError("bundle is not publication eligible:\n" + "\n".join(reasons))
    return load_fit_bundle(directory), report
