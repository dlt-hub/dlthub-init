"""Enumerate a bundled scaffold and write it into a workspace directory."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from . import strings
from .collisions import Flags, Outcome, PlannedPath, build_plan, conflicts
from .errors import CollisionError, ScaffoldError

SCAFFOLDS_DIR = Path(__file__).parent / "scaffolds"

_IGNORE_DIRS = frozenset({"__pycache__", ".venv", ".pytest_cache", ".ruff_cache", ".mypy_cache"})
_DLT_RUNTIME_DIRS = frozenset({"data", "state", ".var"})

_MERGE_MARKER = "# Added by dlthub-init"


def resolve_target(requested_arg: str | None) -> Path:
    if requested_arg is not None:
        return Path(requested_arg).expanduser().resolve()
    return Path.cwd().resolve()


def validate_scaffold_name(scaffold: str) -> None:
    source = SCAFFOLDS_DIR / scaffold
    if not source.is_dir():
        available = ", ".join(sorted(p.name for p in SCAFFOLDS_DIR.iterdir() if p.is_dir()))
        raise ScaffoldError(strings.ERROR_UNKNOWN_SCAFFOLD.format(scaffold=scaffold, available=available or "(none)"))


def enumerate_payload(scaffold: str) -> dict[Path, Path]:
    """Map each scaffold file's workspace-relative path to its source path."""
    source = SCAFFOLDS_DIR / scaffold
    payload: dict[Path, Path] = {}
    try:
        for dirpath, dirnames, filenames in os.walk(source):
            parent = Path(dirpath).name
            dirnames[:] = [
                d for d in dirnames if d not in _IGNORE_DIRS and not (parent == ".dlt" and d in _DLT_RUNTIME_DIRS)
            ]
            for filename in filenames:
                if filename.endswith(".pyc"):
                    continue
                src = Path(dirpath) / filename
                payload[src.relative_to(source)] = src
    except OSError as exc:
        raise ScaffoldError(strings.ERROR_READ_FAILED.format(path=source, reason=exc)) from exc
    return payload


def apply_scaffold(project_dir: Path, *, scaffold: str, flags: Flags) -> list[PlannedPath]:
    """Preflight then write the scaffold. Raises before any write on a hard collision."""
    validate_scaffold_name(scaffold)
    payload = enumerate_payload(scaffold)
    plan = build_plan(list(payload), project_dir, flags)

    blocking = conflicts(plan)
    if blocking:
        raise CollisionError(blocking)

    for planned in plan:
        dest = project_dir / planned.relative
        source = payload[planned.relative]
        if planned.outcome in (Outcome.CREATE, Outcome.OVERWRITE):
            _copy_file(source, dest)
        elif planned.outcome is Outcome.MERGE:
            _merge_lines(source, dest)
    return plan


def _copy_file(source: Path, dest: Path) -> None:
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
    except OSError as exc:
        raise ScaffoldError(strings.ERROR_WRITE_FAILED.format(path=dest, reason=exc)) from exc


def _merge_lines(source: Path, dest: Path) -> None:
    try:
        existing = dest.read_text(encoding="utf-8")
        seen = {line.strip() for line in existing.splitlines()}
        additions = [
            line
            for line in source.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#") and line.strip() not in seen
        ]
        if not additions:
            return
        suffix = "" if existing.endswith("\n") else "\n"
        dest.write_text(f"{existing}{suffix}\n{_MERGE_MARKER}\n" + "\n".join(additions) + "\n", encoding="utf-8")
    except OSError as exc:
        raise ScaffoldError(strings.ERROR_WRITE_FAILED.format(path=dest, reason=exc)) from exc
