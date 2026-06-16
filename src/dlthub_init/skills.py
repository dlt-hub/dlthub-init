"""Install the bundled workbench skills into a scaffolded workspace.

Canonical skills live once in the repo-root skills/ directory (the source of
truth, written by scripts/generate_skills.py). The wheel force-includes them at
dlthub_init/_bundled_skills/; a source checkout reads them from repo-root skills/.
They are copied into the workspace's .agents/skills/ and linked into
.claude/skills/ (symlink, or copy on Windows / when symlinks are unavailable).
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from . import strings
from .errors import ScaffoldError

_PACKAGE_DIR = Path(__file__).resolve().parent
_BUNDLED_SKILLS = _PACKAGE_DIR / "_bundled_skills"
_SOURCE_SKILLS = _PACKAGE_DIR.parents[1] / "skills"

CANONICAL_DIR = Path(".agents") / "skills"
CLAUDE_DIR = Path(".claude") / "skills"

_IGNORE = shutil.ignore_patterns(".DS_Store", "__pycache__")


def skills_source() -> Path | None:
    if _BUNDLED_SKILLS.is_dir():
        return _BUNDLED_SKILLS
    if _SOURCE_SKILLS.is_dir():
        return _SOURCE_SKILLS
    return None


def install_skills(project_dir: Path) -> list[str]:
    """Copy bundled skills into .agents/skills/ and link them into .claude/skills/.

    Skips skills already present (never clobbers). Returns the names newly added
    to .agents/skills/.
    """
    source = skills_source()
    if source is None:
        return []

    canonical_root = project_dir / CANONICAL_DIR
    created: list[str] = []
    try:
        for skill in sorted(p for p in source.iterdir() if p.is_dir()):
            dest = canonical_root / skill.name
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(skill, dest, ignore=_IGNORE)
                created.append(skill.name)
            _ensure_claude_link(project_dir, skill.name)
    except OSError as exc:
        raise ScaffoldError(strings.ERROR_WRITE_FAILED.format(path=project_dir, reason=exc)) from exc
    return created


def _ensure_claude_link(project_dir: Path, name: str) -> None:
    link = project_dir / CLAUDE_DIR / name
    if os.path.lexists(link):
        return
    canonical = project_dir / CANONICAL_DIR / name
    link.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        shutil.copytree(canonical, link, ignore=_IGNORE)
        return
    try:
        os.symlink(os.path.relpath(canonical, link.parent), link, target_is_directory=True)
    except OSError:
        shutil.copytree(canonical, link, ignore=_IGNORE)
