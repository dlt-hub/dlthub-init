"""Non-destructive write planning for `dlthub-init`.

Before writing anything, classify every path the scaffold would touch so the run
can abort cleanly on a hard collision instead of clobbering user files.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

PYPROJECT = Path("pyproject.toml")
GITIGNORE = Path(".gitignore")

# Never written when present, never the cause of a hard failure (the scaffold
# ship empty templates; a real secrets file is left untouched).
SECRET_FILES = frozenset({Path(".dlt") / "secrets.toml"})

# Additively updatable when present (with --merge); otherwise skipped.
MERGEABLE_FILES = frozenset({GITIGNORE})


class Outcome(Enum):
    CREATE = "create"
    OVERWRITE = "overwrite"
    MERGE = "merge"
    SKIP = "skip"
    DISABLED = "disabled"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class Flags:
    force: bool = False
    merge: bool = False
    no_pyproject: bool = False
    no_gitignore: bool = False


@dataclass(frozen=True)
class PlannedPath:
    relative: Path
    outcome: Outcome


def build_plan(relatives: list[Path], project_dir: Path, flags: Flags) -> list[PlannedPath]:
    return [PlannedPath(rel, _classify(rel, project_dir, flags)) for rel in sorted(relatives)]


def conflicts(plan: list[PlannedPath]) -> list[str]:
    return [str(p.relative) for p in plan if p.outcome is Outcome.CONFLICT]


def _classify(rel: Path, project_dir: Path, flags: Flags) -> Outcome:
    if _disabled_by_flag(rel, flags):
        return Outcome.DISABLED

    exists = (project_dir / rel).exists()
    if rel in SECRET_FILES:
        return Outcome.CREATE if not exists else Outcome.SKIP
    if not exists:
        return Outcome.CREATE
    if rel in MERGEABLE_FILES:
        return Outcome.MERGE if flags.merge else Outcome.SKIP
    return Outcome.OVERWRITE if flags.force else Outcome.CONFLICT


def _disabled_by_flag(rel: Path, flags: Flags) -> bool:
    if rel == PYPROJECT:
        return flags.no_pyproject
    if rel == GITIGNORE:
        return flags.no_gitignore
    return False
