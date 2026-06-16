"""Non-destructive write planning for `dlthub-init`."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

PYPROJECT = Path("pyproject.toml")
UV_LOCK = Path("uv.lock")
GITIGNORE = Path(".gitignore")
WORKSPACE_MARKER = Path(".dlt") / ".workspace"
SECRET_FILES = frozenset({Path(".dlt") / "secrets.toml"})
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
    outcomes = {rel: _classify(rel, project_dir, flags) for rel in relatives}
    _couple_lock_to_pyproject(outcomes, project_dir)
    return [PlannedPath(rel, outcomes[rel]) for rel in sorted(outcomes)]


def conflicts(plan: list[PlannedPath]) -> list[str]:
    return [str(p.relative) for p in plan if p.outcome is Outcome.CONFLICT]


def _classify(rel: Path, project_dir: Path, flags: Flags) -> Outcome:
    if _disabled_by_flag(rel, flags):
        return Outcome.DISABLED
    if not (project_dir / rel).exists():
        return Outcome.CREATE
    if rel in SECRET_FILES:
        return Outcome.SKIP
    if rel in MERGEABLE_FILES:
        return Outcome.MERGE if flags.merge else Outcome.SKIP
    if flags.force:
        return Outcome.OVERWRITE
    if rel == WORKSPACE_MARKER:
        return Outcome.CONFLICT
    return Outcome.SKIP


def _couple_lock_to_pyproject(outcomes: dict[Path, Outcome], project_dir: Path) -> None:
    # The bundled uv.lock only matches the bundled pyproject, so ship them together.
    if UV_LOCK not in outcomes:
        return
    if outcomes.get(PYPROJECT) in (Outcome.CREATE, Outcome.OVERWRITE):
        outcomes[UV_LOCK] = Outcome.OVERWRITE if (project_dir / UV_LOCK).exists() else Outcome.CREATE
    elif (project_dir / UV_LOCK).exists():
        outcomes[UV_LOCK] = Outcome.SKIP
    else:
        del outcomes[UV_LOCK]


def _disabled_by_flag(rel: Path, flags: Flags) -> bool:
    if rel == PYPROJECT:
        return flags.no_pyproject
    if rel == GITIGNORE:
        return flags.no_gitignore
    return False
