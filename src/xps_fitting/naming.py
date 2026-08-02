"""Predictable filesystem-safe names derived from sample and result identity."""

from __future__ import annotations

import re
import unicodedata
from string import Formatter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .result import FitResult


def safe_slug(value: object, *, fallback: str = "untitled", max_length: int = 48) -> str:
    """Return a lowercase ASCII slug truncated deterministically to ``max_length``."""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-") or fallback
    return slug[:max_length].rstrip("-")


def sample_slug(sample: str) -> str:
    """Return the underscore-separated sample token used by publication exports."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", sample.strip()).strip("_").lower()
    return slug or "sample"


def resolve_sample_output_stem(template: str, *, sample: str) -> str:
    """Resolve only ``sample_slug`` fields and validate the resulting filename stem."""
    try:
        fields = tuple(Formatter().parse(template))
    except ValueError as exc:
        raise ValueError(f"invalid output filename template: {template!r}") from exc
    for _, field, format_spec, conversion in fields:
        if field is None:
            continue
        if field != "sample_slug":
            raise ValueError(f"unsupported output filename template field: {field!r}")
        if format_spec or conversion:
            raise ValueError("output filename template fields do not support formatting or conversion")
    try:
        resolved = template.format(sample_slug=sample_slug(sample))
    except (IndexError, KeyError, ValueError) as exc:
        raise ValueError(f"invalid output filename template: {template!r}") from exc
    return validate_output_stem(resolved)


def make_output_name(
    *,
    sample: object | None = None,
    region: object | None = None,
    model: object | None = None,
    plot_type: object = "fit",
    max_length: int = 96,
) -> str:
    """Compose a deterministic filesystem-safe name from available identity fields."""
    parts = [safe_slug(value) for value in (sample, region, model, plot_type) if value not in (None, "")]
    name = "-".join(parts) or "xps-fit"
    return name[:max_length].rstrip("-")


def result_output_name(result: FitResult, *, plot_type: str = "fit") -> str:
    """Derive an output name from a result's sample, region, and model metadata."""
    sample = result.metadata.get("sample_name") or result.metadata.get("sample_id") or "sample"
    region = result.configuration.get("region") or result.metadata.get("region") or "region"
    model = result.configuration.get("name") or "model"
    return make_output_name(sample=sample, region=region, model=model, plot_type=plot_type)


def validate_output_stem(value: str) -> str:
    """Validate a 1--96 character ASCII filename stem without path separators."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", value):
        raise ValueError("output filename must be a 1-96 character filesystem-safe stem")
    return value
