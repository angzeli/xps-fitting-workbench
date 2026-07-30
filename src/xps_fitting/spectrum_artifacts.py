"""Durable reviewed artifacts for raw spectra such as Survey scans."""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from ._version import __version__
from .artifacts import ArtifactDescriptor, classify_origin, portable_path, utc_now
from .integrity import sha256_file, sha256_json
from .naming import safe_slug
from .spectrum import Spectrum

SPECTRUM_BUNDLE_FORMAT = "xps-fitting-workbench-spectrum-bundle"
SPECTRUM_REVIEW_SCHEMA_VERSION = 1
SPECTRUM_CONFIGURATION_SHA256 = sha256_json({"artifact_kind": "raw_spectrum"})


@dataclass(frozen=True)
class SpectrumReviewRecord:
    """Record an accepted human review of one raw experimental spectrum."""

    sample: str
    region: str
    decision: str
    reviewer: str
    review_date: str
    notes: tuple[str, ...]
    source_sha256: str
    review_version: int
    review_status: str = "reviewed"
    software_version: str = __version__
    schema_version: int = SPECTRUM_REVIEW_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.decision != "accepted" or self.review_status != "reviewed":
            raise ValueError("a spectrum review record must describe an accepted decision")
        if not self.reviewer.strip():
            raise ValueError("spectrum reviewer is required")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible spectrum review record."""
        return asdict(self)


@dataclass(frozen=True)
class SpectrumValidationReport:
    """Collect integrity findings and publication blockers for a spectrum bundle."""

    bundle_path: str
    sample: str
    region: str
    point_count: int
    calibration_status: str
    publication_eligible: bool
    errors: tuple[str, ...] = ()
    publication_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class SpectrumReviewPromotion:
    """Identify the reviewed spectrum bundle and record created by promotion."""

    reviewed_spectrum: Path
    review_record: Path
    version: int


def _check_bundle_collisions(paths: Mapping[str, Path], *, overwrite: bool) -> None:
    collisions = [path for path in paths.values() if path.exists()]
    if collisions and not overwrite:
        raise FileExistsError("spectrum bundle output already exists: " + ", ".join(map(str, collisions)))


def save_spectrum_bundle(
    spectrum: Spectrum,
    directory: str | Path,
    *,
    artifact: Mapping[str, Any] | None = None,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Persist aligned spectrum arrays, metadata, hashes, and optional lineage."""
    directory = Path(directory)
    paths = {
        "manifest": directory / "manifest.json",
        "spectrum": directory / "spectrum.csv",
        "metadata": directory / "metadata.json",
    }
    if directory.exists() and not directory.is_dir():
        raise NotADirectoryError(f"spectrum bundle path is not a directory: {directory}")
    _check_bundle_collisions(paths, overwrite=overwrite)
    directory.mkdir(parents=True, exist_ok=True)
    columns: dict[str, Any] = {
        "binding_energy_eV": spectrum.binding_energy,
        "intensity": spectrum.intensity,
    }
    if spectrum.normalised_intensity is not None:
        columns["normalised_intensity"] = spectrum.normalised_intensity
    pd.DataFrame(columns).to_csv(paths["spectrum"], index=False, float_format="%.17g")
    metadata = {
        "region": spectrum.region,
        "sample_name": spectrum.sample_name,
        "source_file": spectrum.source_file,
        "metadata": copy.deepcopy(spectrum.metadata),
        "acquisition_metadata": copy.deepcopy(spectrum.acquisition_metadata),
    }
    paths["metadata"].write_text(json.dumps(metadata, indent=2, default=str) + "\n", encoding="utf-8")
    manifest = {
        "format": SPECTRUM_BUNDLE_FORMAT,
        "format_version": 1,
        "package_version": __version__,
        "files": {"spectrum": "spectrum.csv", "metadata": "metadata.json"},
        "integrity": {
            "spectrum.csv": sha256_file(paths["spectrum"]),
            "metadata.json": sha256_file(paths["metadata"]),
        },
    }
    if artifact is not None:
        manifest["artifact"] = dict(artifact)
    paths["manifest"].write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return paths


def read_spectrum_bundle_manifest(directory: str | Path) -> dict[str, Any]:
    """Load a supported spectrum-bundle manifest without loading its arrays."""
    path = Path(directory) / "manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"spectrum bundle manifest is missing: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("format") != SPECTRUM_BUNDLE_FORMAT or manifest.get("format_version") != 1:
        raise ValueError(f"unsupported spectrum bundle manifest: {path}")
    return manifest


def load_spectrum_bundle(directory: str | Path) -> Spectrum:
    """Load a spectrum bundle after verifying member paths and recorded hashes."""
    directory = Path(directory)
    manifest = read_spectrum_bundle_manifest(directory)

    def member(name: str) -> Path:
        candidate = (directory / str(manifest["files"][name])).resolve()
        if directory.resolve() not in candidate.parents or not candidate.is_file():
            raise ValueError(f"invalid spectrum bundle member: {candidate}")
        expected = manifest.get("integrity", {}).get(candidate.name)
        if expected is not None and sha256_file(candidate) != expected:
            raise ValueError(f"spectrum bundle member hash mismatch: {candidate}")
        return candidate

    table = pd.read_csv(member("spectrum"), float_precision="round_trip")
    details = json.loads(member("metadata").read_text(encoding="utf-8"))
    normalised = table["normalised_intensity"].to_numpy() if "normalised_intensity" in table else None
    return Spectrum(
        table["binding_energy_eV"].to_numpy(),
        table["intensity"].to_numpy(),
        region=str(details.get("region", "")),
        sample_name=str(details.get("sample_name", "")),
        source_file=details.get("source_file"),
        metadata=dict(details.get("metadata", {})),
        normalised_intensity=normalised,
        acquisition_metadata=dict(details.get("acquisition_metadata", {})),
    )


def _resolve_recorded_file(value: str, bundle: Path, repository_root: str | Path | None) -> Path | None:
    recorded = Path(value)
    candidates = [recorded] if recorded.is_absolute() else []
    if repository_root is not None and not recorded.is_absolute():
        candidates.append(Path(repository_root) / recorded)
    if not recorded.is_absolute():
        candidates.extend(parent / recorded for parent in bundle.resolve().parents)
    return next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)


def _canonical_region_name(value: str) -> str:
    compact = "".join(character for character in value if character.isalnum()).casefold()
    aliases = {
        "survey": "Survey",
        "surveyscan": "Survey",
        "xpssurvey": "Survey",
        "widescan": "Survey",
        "c1s": "C1s",
        "n1s": "N1s",
        "o1s": "O1s",
        "cl2p": "Cl2p",
    }
    return aliases.get(compact, value.strip())


def validate_spectrum_bundle(
    directory: str | Path,
    *,
    require_calibrated: bool = False,
    repository_root: str | Path | None = None,
) -> SpectrumValidationReport:
    """Validate spectrum integrity, provenance, review, and calibration lineage."""
    bundle = Path(directory).resolve()
    manifest = read_spectrum_bundle_manifest(bundle)
    spectrum = load_spectrum_bundle(bundle)
    errors: list[str] = []
    reasons: list[str] = []
    try:
        descriptor = ArtifactDescriptor.from_dict(dict(manifest.get("artifact") or {}))
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"invalid spectrum artifact descriptor: {exc}")
        descriptor = None
    if classify_origin(spectrum.metadata.get("data_origin")) != "experimental":
        reasons.append("spectrum data origin is not experimental")
    if descriptor is not None:
        if descriptor.state != "reviewed" or descriptor.review_status != "reviewed":
            reasons.append("spectrum artifact has not been scientifically reviewed")
        if descriptor.sample != spectrum.sample_name or _canonical_region_name(
            descriptor.region
        ) != _canonical_region_name(spectrum.region):
            errors.append("spectrum sample or region differs from the artifact descriptor")
        if descriptor.source_point_count != spectrum.binding_energy.size:
            errors.append("spectrum point count differs from the artifact descriptor")
        source = _resolve_recorded_file(descriptor.source_path, bundle, repository_root)
        if source is None or sha256_file(source) != descriptor.source_sha256:
            errors.append("spectrum source provenance does not resolve or match its SHA-256")
        if not descriptor.review_record:
            errors.append("reviewed spectrum artifact has no review record")
        else:
            record = _resolve_recorded_file(descriptor.review_record, bundle, repository_root)
            expected = descriptor.lineage.get("review_record_sha256")
            if record is None:
                errors.append("spectrum review record does not resolve")
            elif not expected or sha256_file(record) != expected:
                errors.append("spectrum review record SHA-256 does not match")
            else:
                review = json.loads(record.read_text(encoding="utf-8"))
                if review.get("decision") != "accepted" or review.get("review_status") != "reviewed":
                    errors.append("spectrum review record does not contain an accepted decision")
                if review.get("sample") != descriptor.sample or review.get("region") != descriptor.region:
                    errors.append("spectrum review record sample or region does not match")
                if review.get("source_sha256") != descriptor.source_sha256:
                    errors.append("spectrum review record source SHA-256 does not match")
        if require_calibrated and descriptor.calibration_status != "calibrated":
            reasons.append("publication workflow requires a calibrated reviewed spectrum")
        if descriptor.calibration_status == "calibrated":
            record = (
                _resolve_recorded_file(descriptor.calibration_record, bundle, repository_root)
                if descriptor.calibration_record
                else None
            )
            expected = descriptor.lineage.get("calibration_record_sha256")
            if record is None:
                errors.append("calibrated spectrum has no resolvable calibration record")
            elif not expected or sha256_file(record) != expected:
                errors.append("spectrum calibration record SHA-256 does not match")
            else:
                calibration = json.loads(record.read_text(encoding="utf-8"))
                calibration_metadata = spectrum.metadata.get("binding_energy_calibration", {})
                if calibration.get("sample") != descriptor.sample:
                    errors.append("spectrum calibration record sample does not match")
                if descriptor.region not in calibration.get("applied_regions", []):
                    errors.append("spectrum calibration record does not include this region")
                if calibration.get("energy_offset_eV") != calibration_metadata.get("offset_eV"):
                    errors.append("spectrum calibration record offset does not match metadata")
    return SpectrumValidationReport(
        bundle_path=str(bundle),
        sample=spectrum.sample_name,
        region=spectrum.region,
        point_count=int(spectrum.binding_energy.size),
        calibration_status=descriptor.calibration_status if descriptor is not None else "unknown",
        publication_eligible=not errors and not reasons,
        errors=tuple(errors),
        publication_reasons=tuple(reasons),
    )


def _next_version(directory: Path, region: str) -> int:
    prefix = f"{region}.review-v"
    versions = []
    for artifact in directory.glob(f"{prefix}*.spectrum"):
        value = artifact.name.removeprefix(prefix).removesuffix(".spectrum")
        if value.isdigit():
            versions.append(int(value))
    return max(versions, default=0) + 1


def review_spectrum(
    spectrum: Spectrum,
    reviewed_root: str | Path,
    *,
    source_path: str | Path,
    reviewer: str,
    notes: tuple[str, ...] = (),
    repository_root: str | Path | None = None,
    review_date: str | None = None,
    version: int | None = None,
) -> SpectrumReviewPromotion:
    """Create a versioned reviewed raw-spectrum artifact without changing its arrays."""
    source = Path(source_path)
    if not source.is_file():
        raise FileNotFoundError(f"experimental spectrum source is missing: {source}")
    if classify_origin(spectrum.metadata.get("data_origin")) != "experimental":
        raise ValueError("reviewed spectrum artifacts require data_origin='experimental'")
    sample = spectrum.sample_name.strip()
    region = _canonical_region_name(spectrum.region)
    if not sample or not region:
        raise ValueError("reviewed spectrum requires sample and region identities")
    root = Path(reviewed_root)
    uncalibrated = root / sample / "uncalibrated"
    records = root / sample / "review_records"
    selected = version or _next_version(uncalibrated, region)
    if selected < 1:
        raise ValueError("spectrum review version must be positive")
    bundle = uncalibrated / f"{region}.review-v{selected}.spectrum"
    record_path = records / f"{region}.review-v{selected}.json"
    if bundle.exists() or record_path.exists():
        raise FileExistsError(f"spectrum review version {selected} already exists")
    timestamp = review_date or utc_now()
    source_sha256 = sha256_file(source)
    record = SpectrumReviewRecord(
        sample=sample,
        region=region,
        decision="accepted",
        reviewer=reviewer,
        review_date=timestamp,
        notes=tuple(notes),
        source_sha256=source_sha256,
        review_version=selected,
    )
    records.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(record.to_dict(), indent=2) + "\n", encoding="utf-8")
    artifact_id = f"{safe_slug(sample)}-{safe_slug(region)}-spectrum-review-v{selected}"
    descriptor = ArtifactDescriptor(
        artifact_id=artifact_id,
        state="reviewed",
        sample=sample,
        region=region,
        model="raw_spectrum",
        created_at=timestamp,
        data_origin="experimental",
        source_path=portable_path(source, repository_root),
        source_sha256=source_sha256,
        configuration_sha256=SPECTRUM_CONFIGURATION_SHA256,
        review_status="reviewed",
        calibration_status="uncalibrated",
        source_point_count=int(spectrum.binding_energy.size),
        lineage={"review_version": selected, "review_record_sha256": sha256_file(record_path)},
        review_record=portable_path(record_path, repository_root),
    )
    stored = replace(
        spectrum,
        source_file=portable_path(source, repository_root),
        metadata={
            **copy.deepcopy(spectrum.metadata),
            "artifact_id": artifact_id,
            "artifact_state": "reviewed",
            "review_status": "reviewed",
            "review_version": selected,
            "calibration_status": "uncalibrated",
            "publication_eligible": False,
        },
    )
    try:
        save_spectrum_bundle(stored, bundle, artifact=descriptor.to_dict())
    except Exception:
        record_path.unlink(missing_ok=True)
        raise
    reloaded = load_spectrum_bundle(bundle)
    if not np.array_equal(reloaded.binding_energy, spectrum.binding_energy) or not np.array_equal(
        reloaded.intensity, spectrum.intensity
    ):
        raise RuntimeError("spectrum review persistence changed scientific arrays")
    return SpectrumReviewPromotion(bundle, record_path, selected)
