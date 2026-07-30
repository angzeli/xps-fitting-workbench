"""Allowlisted cleanup for disposable generated files."""

from __future__ import annotations

import shutil
from pathlib import Path

GENERATED_DIRECTORIES = (Path("outputs"), Path("figures") / "diagnostic")
PROTECTED_DIRECTORIES = (Path("data") / "raw", Path("artifacts") / "reviewed")


def generated_cleanup_plan(repository_root: str | Path) -> tuple[Path, ...]:
    """List files beneath allowlisted generated roots after safety checks."""
    root = Path(repository_root).resolve()
    protected = tuple((root / path).resolve() for path in PROTECTED_DIRECTORIES)
    files: list[Path] = []
    for relative in GENERATED_DIRECTORIES:
        target = root / relative
        if target.is_symlink():
            raise ValueError(f"refusing to clean a symlinked generated directory: {target}")
        resolved = target.resolve()
        if root not in resolved.parents or any(resolved == item or item in resolved.parents for item in protected):
            raise ValueError(f"generated cleanup target is outside its allowlist: {target}")
        if resolved.is_dir():
            files.extend(path for path in sorted(resolved.rglob("*")) if path.is_file())
    return tuple(files)


def clean_generated(repository_root: str | Path, *, dry_run: bool = True) -> tuple[Path, ...]:
    """Delete only explicit disposable roots, returning every affected file."""
    root = Path(repository_root).resolve()
    files = generated_cleanup_plan(root)
    if dry_run:
        return files
    for relative in GENERATED_DIRECTORIES:
        target = root / relative
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
    return files
