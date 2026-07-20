"""Predictable, filesystem-safe output naming."""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .result import FitResult


def safe_slug(value: object, *, fallback: str = "untitled", max_length: int = 48) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-") or fallback
    return slug[:max_length].rstrip("-")


def make_output_name(
    *,
    sample: object | None = None,
    region: object | None = None,
    model: object | None = None,
    plot_type: object = "fit",
    max_length: int = 96,
) -> str:
    parts = [safe_slug(value) for value in (sample, region, model, plot_type) if value not in (None, "")]
    name = "-".join(parts) or "xps-fit"
    return name[:max_length].rstrip("-")


def result_output_name(result: FitResult, *, plot_type: str = "fit") -> str:
    sample = result.metadata.get("sample_name") or result.metadata.get("sample_id") or "sample"
    region = result.configuration.get("region") or result.metadata.get("region") or "region"
    model = result.configuration.get("name") or "model"
    return make_output_name(sample=sample, region=region, model=model, plot_type=plot_type)


def validate_output_stem(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", value):
        raise ValueError("output filename must be a 1-96 character filesystem-safe stem")
    return value
