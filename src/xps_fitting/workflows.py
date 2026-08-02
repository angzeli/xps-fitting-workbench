"""Scientific lifecycle orchestration layered over numerical fitting APIs."""

from __future__ import annotations

from pathlib import Path

from .artifacts import canonical_region, save_candidate_bundle
from .naming import safe_slug
from .result import FitResult


def persist_candidate_results(
    results: dict[str, FitResult],
    *,
    sample: str,
    region: str,
    source_path: str | Path,
    artifacts_root: str | Path,
    repository_root: str | Path | None = None,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Persist every ordered candidate before diagnostics may be rendered.

    Each result is stored with raw-source lineage beneath the sample and canonical
    region. Bundle creation follows mapping order and stops on the first collision
    or persistence error; no plotting side effects occur here.
    """
    if not results:
        raise ValueError("candidate result mapping is empty")
    destination = Path(artifacts_root) / sample / canonical_region(region)
    bundles: dict[str, Path] = {}
    for model, result in results.items():
        bundle = destination / f"{safe_slug(model, fallback='candidate')}.bundle"
        save_candidate_bundle(
            result,
            bundle,
            sample=sample,
            region=region,
            source_path=source_path,
            repository_root=repository_root,
            overwrite=overwrite,
        )
        bundles[model] = bundle
    return bundles
