"""Persisted calibration of complete sets of reviewed sample artifacts."""

from __future__ import annotations

import copy
import json
import shutil
import uuid
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from ._version import __version__
from .artifacts import (
    ArtifactDescriptor,
    bundle_scientific_sha256,
    canonical_region,
    fit_configuration_sha256,
    portable_path,
    utc_now,
    validate_fit_bundle,
)
from .calibration import calibrate_sample_binding_energy
from .export import load_fit_bundle, read_fit_bundle_manifest, save_fit_bundle
from .integrity import result_arrays_equal, sha256_file
from .sample_manifest import EXPECTED_REGIONS, SampleManifest, load_sample_manifest, save_sample_manifest
from .spectrum_artifacts import (
    SPECTRUM_CONFIGURATION_SHA256,
    load_spectrum_bundle,
    read_spectrum_bundle_manifest,
    save_spectrum_bundle,
    validate_spectrum_bundle,
)

CALIBRATION_RECORD_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class CalibrationPlan:
    """Preview a sample-wide rigid energy shift before any files are written."""

    sample: str
    reference_region: str
    reference_component: str
    reference_component_label: str
    reference_center_before_eV: float
    target_energy_eV: float
    energy_offset_eV: float
    applied_regions: tuple[str, ...]
    missing_regions: tuple[str, ...]

    def format_text(self) -> str:
        """Format the proposed shift and its unchanged quantities for confirmation."""
        exact_offset = repr(self.energy_offset_eV)
        if not exact_offset.startswith("-"):
            exact_offset = "+" + exact_offset
        lines = [
            f"Exact fitted reference centre: {self.reference_center_before_eV!r} eV",
            f"Requested target:              {self.target_energy_eV!r} eV",
            f"Calculated common shift:       {exact_offset} eV",
            "",
            "This shift will be applied to:",
            *(f"- {region}" for region in self.applied_regions),
        ]
        if self.missing_regions:
            lines.extend(["", "Missing required regions:", *(f"- {region}" for region in self.missing_regions)])
        lines.extend(
            [
                "",
                "The following will not change:",
                "- intensity",
                "- background",
                "- component shapes",
                "- residuals",
                "- widths",
                "- areas",
            ]
        )
        return "\n".join(lines)


@dataclass(frozen=True)
class CalibrationRecord:
    """Persist the approved shift, rationale, and immutable artifact lineage."""

    sample: str
    reference_region: str
    reference_component: str
    reference_component_label: str
    reference_center_before_eV: float
    target_energy_eV: float
    energy_offset_eV: float
    sign_convention: str
    applied_regions: tuple[str, ...]
    missing_regions: tuple[str, ...]
    calibration_date: str
    reviewer: str
    scientific_rationale: str
    source_reviewed_bundle_sha256: dict[str, str]
    calibrated_bundle_sha256: dict[str, str]
    software_version: str = __version__
    schema_version: int = CALIBRATION_RECORD_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible calibration record."""
        return asdict(self)


@dataclass(frozen=True)
class CalibrationOutcome:
    """Report the plan, record, and calibrated bundles created by a run."""

    plan: CalibrationPlan
    record: CalibrationRecord
    calibration_record: Path
    calibrated_bundles: dict[str, Path]


def _repository_root(anchor: Path, explicit: str | Path | None) -> Path | None:
    if explicit is not None:
        return Path(explicit).resolve()
    for parent in (anchor.resolve(), *anchor.resolve().parents):
        if (parent / "pyproject.toml").is_file():
            return parent
    return None


def _resolve_path(value: str, anchor: Path, repository_root: Path | None) -> Path:
    candidate = Path(value)
    attempts = [candidate] if candidate.is_absolute() else []
    if repository_root is not None and not candidate.is_absolute():
        attempts.append(repository_root / candidate)
    if not candidate.is_absolute():
        attempts.append(anchor / candidate)
    for attempt in attempts:
        if attempt.exists():
            return attempt.resolve()
    raise FileNotFoundError(f"artifact path from sample manifest does not resolve: {value}")


def _reviewed_inputs(
    manifest_path: Path,
    manifest: SampleManifest,
    repository_root: Path | None,
) -> tuple[dict[str, Path], dict[str, Any], dict[str, Any]]:
    paths: dict[str, Path] = {}
    results: dict[str, Any] = {}
    spectra: dict[str, Any] = {}
    for region, value in manifest.reviewed_uncalibrated.items():
        canonical = canonical_region(region)
        bundle = _resolve_path(value, manifest_path.parent, repository_root)
        raw_manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        report: Any
        if raw_manifest.get("format") == "xps-fitting-workbench-fit-bundle":
            report = validate_fit_bundle(bundle, repository_root=repository_root)
            results[canonical] = load_fit_bundle(bundle)
        elif raw_manifest.get("format") == "xps-fitting-workbench-spectrum-bundle":
            report = validate_spectrum_bundle(bundle, repository_root=repository_root)
            spectra[canonical] = load_spectrum_bundle(bundle)
        else:
            raise ValueError(f"unsupported active reviewed artifact: {bundle}")
        if report.errors or not report.publication_eligible:
            reasons = (*report.errors, *report.publication_reasons)
            raise ValueError(f"active reviewed {canonical} bundle is invalid:\n" + "\n".join(reasons))
        if report.sample != manifest.sample or report.calibration_status != "uncalibrated":
            raise ValueError(f"active reviewed {canonical} bundle has inconsistent sample or calibration state")
        paths[canonical] = bundle
    return paths, results, spectra


def prepare_sample_calibration(
    manifest_path: str | Path,
    *,
    reference_region: str,
    reference_component: str,
    reference_component_label: str,
    target_energy_eV: float = 284.8,
    required_regions: tuple[str, ...] = EXPECTED_REGIONS,
    allow_incomplete: bool = False,
    repository_root: str | Path | None = None,
) -> CalibrationPlan:
    """Validate reviewed inputs and calculate a sample-wide energy-shift plan.

    The returned plan is read-only: preparation never calibrates arrays or writes
    artifact bundles. Missing required regions block the plan unless the caller
    explicitly allows an incomplete sample.
    """
    path = Path(manifest_path).resolve()
    manifest = load_sample_manifest(path)
    root = _repository_root(path.parent, repository_root)
    _, results, spectra = _reviewed_inputs(path, manifest, root)
    reference = canonical_region(reference_region)
    required = tuple(canonical_region(region) for region in required_regions)
    available = (*results, *spectra)
    missing = tuple(region for region in required if region not in available)
    if missing and not allow_incomplete:
        raise ValueError(
            "sample is incomplete; missing reviewed regions: "
            + ", ".join(missing)
            + "; explicitly allow an incomplete calibration to continue"
        )
    if reference not in results:
        raise KeyError(f"reviewed reference region is unavailable: {reference}")
    centre_key = f"{reference_component}.centre"
    if centre_key not in results[reference].fitted_parameters:
        raise KeyError(f"fitted reference centre is unavailable: {centre_key}")
    observed = float(results[reference].fitted_parameters[centre_key])
    if not np.isfinite(observed) or not np.isfinite(target_energy_eV):
        raise ValueError("reference and target energies must be finite")
    return CalibrationPlan(
        sample=manifest.sample,
        reference_region=reference,
        reference_component=reference_component,
        reference_component_label=reference_component_label,
        reference_center_before_eV=observed,
        target_energy_eV=float(target_energy_eV),
        energy_offset_eV=float(target_energy_eV - observed),
        applied_regions=tuple(available),
        missing_regions=missing,
    )


def _validate_pair(original: Any, calibrated: Any, offset_eV: float) -> None:
    if not result_arrays_equal(original, calibrated, energy_offset=offset_eV):
        raise RuntimeError("calibration changed intensity-domain FitResult arrays")
    for name, value in original.fitted_parameters.items():
        expected = float(value) + offset_eV if name.endswith(".centre") else value
        if not np.isclose(calibrated.fitted_parameters[name], expected, rtol=0.0, atol=1e-12):
            raise RuntimeError(f"calibration changed fitted parameter incorrectly: {name}")
    for unchanged in (
        "parameter_uncertainties",
        "correlation_matrix",
        "fit_statistics",
        "warnings",
        "convergence",
        "software_versions",
    ):
        if getattr(original, unchanged) != getattr(calibrated, unchanged):
            raise RuntimeError(f"calibration changed {unchanged}")


def _validate_spectrum_pair(original: Any, calibrated: Any, offset_eV: float) -> None:
    if not np.allclose(calibrated.binding_energy, original.binding_energy + offset_eV, rtol=0.0, atol=1e-12):
        raise RuntimeError("calibration changed a spectrum energy axis incorrectly")
    if not np.array_equal(calibrated.intensity, original.intensity):
        raise RuntimeError("calibration changed spectrum intensity")
    if original.normalised_intensity is None:
        if calibrated.normalised_intensity is not None:
            raise RuntimeError("calibration created normalised spectrum intensity")
    elif not np.array_equal(calibrated.normalised_intensity, original.normalised_intensity):
        raise RuntimeError("calibration changed normalised spectrum intensity")


def _patch_calibration_record_hash(bundle: Path, record_sha256: str) -> None:
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact"].setdefault("lineage", {})["calibration_record_sha256"] = record_sha256
    temporary = manifest_path.with_name(".manifest.json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    temporary.replace(manifest_path)


def calibrate_reviewed_sample(
    manifest_path: str | Path,
    *,
    reference_region: str,
    reference_component: str,
    reference_component_label: str,
    reviewer: str,
    scientific_rationale: str,
    target_energy_eV: float = 284.8,
    required_regions: tuple[str, ...] = EXPECTED_REGIONS,
    allow_incomplete: bool = False,
    confirmed: bool = False,
    repository_root: str | Path | None = None,
    calibration_date: str | None = None,
) -> CalibrationOutcome:
    """Create calibrated copies only after the caller records explicit confirmation."""
    path = Path(manifest_path).resolve()
    plan = prepare_sample_calibration(
        path,
        reference_region=reference_region,
        reference_component=reference_component,
        reference_component_label=reference_component_label,
        target_energy_eV=target_energy_eV,
        required_regions=required_regions,
        allow_incomplete=allow_incomplete,
        repository_root=repository_root,
    )
    if not confirmed:
        raise PermissionError("calibration confirmation is required; no files were written")
    if not reviewer.strip() or not scientific_rationale.strip():
        raise ValueError("calibration requires both a reviewer and a scientific rationale")
    manifest = load_sample_manifest(path)
    if manifest.calibration is not None or manifest.calibration_status == "calibrated":
        raise FileExistsError("sample calibration already exists; reviewed uncalibrated artifacts were not changed")
    root = _repository_root(path.parent, repository_root)
    source_paths, source_results, source_spectra = _reviewed_inputs(path, manifest, root)
    calibrated_results, calibrated_spectra, numerical = calibrate_sample_binding_energy(
        source_results,
        spectra=source_spectra,
        reference_core_level=plan.reference_region,
        reference_component=plan.reference_component,
        target_eV=plan.target_energy_eV,
    )
    if not np.isclose(numerical.offset_eV, plan.energy_offset_eV, rtol=0.0, atol=1e-12):
        raise RuntimeError("calibration plan changed before persistence")
    for region in plan.applied_regions:
        if region in source_results:
            _validate_pair(source_results[region], calibrated_results[region], plan.energy_offset_eV)
        else:
            _validate_spectrum_pair(source_spectra[region], calibrated_spectra[region], plan.energy_offset_eV)

    calibrated_directory = path.parent / "calibrated"
    calibration_record_path = path.parent / "calibration.json"
    final_bundles = {}
    for region in plan.applied_regions:
        suffix = "bundle" if region in source_results else "spectrum"
        final_bundles[region] = (
            calibrated_directory / f"{region}.review-v{manifest.active_review_versions[region]}.{suffix}"
        )
    collisions = [
        destination for destination in (*final_bundles.values(), calibration_record_path) if destination.exists()
    ]
    if collisions:
        raise FileExistsError("calibration output already exists: " + ", ".join(str(item) for item in collisions))

    timestamp = calibration_date or utc_now()
    record_reference = portable_path(calibration_record_path, root)
    staging = path.parent / f".calibration-{uuid.uuid4().hex}.tmp"
    staging.mkdir(parents=True)
    staged_bundles: dict[str, Path] = {}
    try:
        for region in plan.applied_regions:
            is_fit_result = region in source_results
            source_manifest = (
                read_fit_bundle_manifest(source_paths[region])
                if is_fit_result
                else read_spectrum_bundle_manifest(source_paths[region])
            )
            source_descriptor = ArtifactDescriptor.from_dict(dict(source_manifest["artifact"]))
            calibrated_id = f"{source_descriptor.artifact_id}-calibrated"
            calibrated: Any
            if is_fit_result:
                calibrated = copy.deepcopy(calibrated_results[region])
                calibrated_configuration_sha256 = fit_configuration_sha256(calibrated)
                calibrated.metadata.update(
                    {
                        "artifact_id": calibrated_id,
                        "artifact_state": "reviewed",
                        "review_status": "reviewed",
                        "calibration_status": "calibrated",
                        "calibration_record": record_reference,
                        "configuration_sha256": calibrated_configuration_sha256,
                        "publication_eligible": True,
                    }
                )
            else:
                shifted_spectrum = calibrated_spectra[region]
                calibrated_configuration_sha256 = SPECTRUM_CONFIGURATION_SHA256
                calibrated = replace(
                    shifted_spectrum,
                    metadata={
                        **shifted_spectrum.metadata,
                        "artifact_id": calibrated_id,
                        "artifact_state": "reviewed",
                        "review_status": "reviewed",
                        "calibration_status": "calibrated",
                        "calibration_record": record_reference,
                        "publication_eligible": True,
                    },
                )
            descriptor = ArtifactDescriptor(
                artifact_id=calibrated_id,
                state="reviewed",
                sample=source_descriptor.sample,
                region=source_descriptor.region,
                model=source_descriptor.model,
                created_at=timestamp,
                data_origin=source_descriptor.data_origin,
                source_path=source_descriptor.source_path,
                source_sha256=source_descriptor.source_sha256,
                configuration_sha256=calibrated_configuration_sha256,
                review_status="reviewed",
                calibration_status="calibrated",
                source_point_count=source_descriptor.source_point_count,
                lineage={
                    **source_descriptor.lineage,
                    "parent_artifact_id": source_descriptor.artifact_id,
                    **(
                        {
                            "review_candidate_artifact_id": source_descriptor.lineage.get("parent_artifact_id"),
                            "reviewed_configuration_sha256": source_descriptor.configuration_sha256,
                        }
                        if is_fit_result
                        else {}
                    ),
                    "source_reviewed_bundle_sha256": bundle_scientific_sha256(source_paths[region]),
                    "energy_offset_eV": plan.energy_offset_eV,
                },
                review_record=source_descriptor.review_record,
                calibration_record=record_reference,
            )
            staged = staging / final_bundles[region].name
            if is_fit_result:
                save_fit_bundle(calibrated, staged, artifact=descriptor.to_dict())
                _validate_pair(source_results[region], load_fit_bundle(staged), plan.energy_offset_eV)
            else:
                save_spectrum_bundle(calibrated, staged, artifact=descriptor.to_dict())
                _validate_spectrum_pair(source_spectra[region], load_spectrum_bundle(staged), plan.energy_offset_eV)
            staged_bundles[region] = staged

        record = CalibrationRecord(
            sample=plan.sample,
            reference_region=plan.reference_region,
            reference_component=plan.reference_component,
            reference_component_label=plan.reference_component_label,
            reference_center_before_eV=plan.reference_center_before_eV,
            target_energy_eV=plan.target_energy_eV,
            energy_offset_eV=plan.energy_offset_eV,
            sign_convention="calibrated_energy = uncalibrated_energy + energy_offset_eV",
            applied_regions=plan.applied_regions,
            missing_regions=plan.missing_regions,
            calibration_date=timestamp,
            reviewer=reviewer,
            scientific_rationale=scientific_rationale,
            source_reviewed_bundle_sha256={
                region: bundle_scientific_sha256(source_paths[region]) for region in plan.applied_regions
            },
            calibrated_bundle_sha256={
                region: bundle_scientific_sha256(staged_bundles[region]) for region in plan.applied_regions
            },
        )
        staged_record = staging / "calibration.json"
        staged_record.write_text(json.dumps(record.to_dict(), indent=2) + "\n", encoding="utf-8")
        record_sha256 = sha256_file(staged_record)
        for bundle in staged_bundles.values():
            _patch_calibration_record_hash(bundle, record_sha256)

        calibrated_directory.mkdir(parents=True, exist_ok=True)
        for region, staged in staged_bundles.items():
            staged.replace(final_bundles[region])
        staged_record.replace(calibration_record_path)
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    manifest.calibrated = {region: portable_path(bundle, root) for region, bundle in final_bundles.items()}
    manifest.calibration = portable_path(calibration_record_path, root)
    manifest.calibration_status = "calibrated"
    manifest.energy_offset_eV = plan.energy_offset_eV
    manifest.calibrated_at = timestamp
    manifest.updated_at = timestamp
    save_sample_manifest(manifest, path, overwrite=True)
    return CalibrationOutcome(plan, record, calibration_record_path, final_bundles)
