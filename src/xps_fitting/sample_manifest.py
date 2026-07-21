"""Sample-level links between raw data and reviewed scientific artifacts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .artifacts import ArtifactDescriptor, canonical_region, portable_path, utc_now, validate_fit_bundle
from .export import read_fit_bundle_manifest
from .integrity import sha256_file

SAMPLE_MANIFEST_SCHEMA_VERSION = 1
EXPECTED_REGIONS = ("C1s", "N1s", "O1s", "Cl2p", "Survey")


def _region_from_vgd_name(path: Path) -> str | None:
    compact = "".join(character for character in path.stem if character.isalnum()).casefold()
    if "survey" in compact:
        return "Survey"
    for region in EXPECTED_REGIONS[:-1]:
        if compact.startswith(region.casefold()):
            return region
    return None


def discover_raw_regions(directory: str | Path) -> dict[str, Path]:
    """Find recognised raw VGD regions without reading or modifying their contents."""
    raw_directory = Path(directory)
    if not raw_directory.is_dir():
        raise FileNotFoundError(f"raw sample directory is missing: {raw_directory}")
    regions: dict[str, Path] = {}
    for source in sorted(raw_directory.glob("*.VGD")):
        region = _region_from_vgd_name(source)
        if region is None:
            continue
        if region in regions:
            raise ValueError(f"multiple raw VGD files resolve to {region}: {regions[region]}, {source}")
        regions[region] = source.resolve()
    return regions


@dataclass
class SampleManifest:
    sample: str
    raw_regions: dict[str, str]
    raw_sha256: dict[str, str]
    expected_regions: tuple[str, ...] = EXPECTED_REGIONS
    reviewed_uncalibrated: dict[str, str] = field(default_factory=dict)
    active_review_versions: dict[str, int] = field(default_factory=dict)
    calibrated: dict[str, str] = field(default_factory=dict)
    calibration: str | None = None
    calibration_status: str = "uncalibrated"
    energy_offset_eV: float | None = None
    calibrated_at: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    schema_version: int = SAMPLE_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.sample.strip():
            raise ValueError("sample manifest requires a sample name")
        if self.calibration_status not in {"uncalibrated", "calibrated"}:
            raise ValueError(f"unsupported sample calibration state: {self.calibration_status}")
        if set(self.raw_regions) != set(self.raw_sha256):
            raise ValueError("raw region paths and SHA-256 records must have identical keys")
        if any(len(digest) != 64 for digest in self.raw_sha256.values()):
            raise ValueError("every raw region requires a SHA-256 digest")

    @property
    def missing_raw_regions(self) -> tuple[str, ...]:
        return tuple(region for region in self.expected_regions if region not in self.raw_regions)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["expected_regions"] = list(self.expected_regions)
        data["missing_raw_regions"] = list(self.missing_raw_regions)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SampleManifest":
        values = dict(data)
        values.pop("missing_raw_regions", None)
        values["expected_regions"] = tuple(values.get("expected_regions", EXPECTED_REGIONS))
        return cls(**values)


def save_sample_manifest(
    manifest: SampleManifest,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    destination = Path(path)
    if destination.exists() and not overwrite:
        raise FileExistsError(f"sample manifest already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
    return destination


def load_sample_manifest(path: str | Path) -> SampleManifest:
    return SampleManifest.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def create_sample_manifest(
    sample: str,
    raw_directory: str | Path,
    path: str | Path,
    *,
    repository_root: str | Path | None = None,
    created_at: str | None = None,
    overwrite: bool = False,
) -> SampleManifest:
    regions = discover_raw_regions(raw_directory)
    timestamp = created_at or utc_now()
    manifest = SampleManifest(
        sample=sample,
        raw_regions={region: portable_path(source, repository_root) for region, source in regions.items()},
        raw_sha256={region: sha256_file(source) for region, source in regions.items()},
        created_at=timestamp,
        updated_at=timestamp,
    )
    save_sample_manifest(manifest, path, overwrite=overwrite)
    return manifest


def activate_reviewed_bundle(
    manifest_path: str | Path,
    bundle: str | Path,
    *,
    repository_root: str | Path | None = None,
    replace_active: bool = False,
) -> SampleManifest:
    """Make one immutable reviewed version active without modifying its bundle."""
    path = Path(manifest_path)
    manifest = load_sample_manifest(path)
    bundle_path = Path(bundle).resolve()
    report = validate_fit_bundle(bundle_path, repository_root=repository_root)
    descriptor = ArtifactDescriptor.from_dict(dict(read_fit_bundle_manifest(bundle_path).get("artifact") or {}))
    if report.errors:
        raise ValueError("reviewed bundle failed validation:\n" + "\n".join(report.errors))
    if descriptor.state != "reviewed" or descriptor.review_status != "reviewed":
        raise ValueError("sample manifests can activate only reviewed artifacts")
    if descriptor.calibration_status != "uncalibrated":
        raise ValueError("reviewed_uncalibrated entries require an uncalibrated artifact")
    if descriptor.sample != manifest.sample:
        raise ValueError(f"reviewed bundle belongs to {descriptor.sample}, not manifest sample {manifest.sample}")
    region = canonical_region(descriptor.region)
    if region in manifest.reviewed_uncalibrated and not replace_active:
        raise FileExistsError(
            f"an active reviewed {region} artifact already exists; pass replace_active=True explicitly"
        )
    version = int(descriptor.lineage.get("review_version", 0))
    if version < 1:
        raise ValueError("reviewed bundle has no valid review version")
    manifest.reviewed_uncalibrated[region] = portable_path(bundle_path, repository_root)
    manifest.active_review_versions[region] = version
    manifest.updated_at = utc_now()
    save_sample_manifest(manifest, path, overwrite=True)
    return manifest
