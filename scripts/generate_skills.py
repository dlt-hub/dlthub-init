"""Populate the root skills/ directory from the dltHub AI workbench.

Resolves WORKBENCH_REF_SHORT to a full SHA (pinned into WORKBENCH_REF), then
copies each SKILL_TOOLKITS toolkit's skills into skills/, flat. Run via
`make generate-skills`. Env overrides (one-off, no file writeback):
DLTHUB_WORKBENCH_REPO, DLTHUB_WORKBENCH_REF, DLTHUB_SKILL_TOOLKITS.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
SKILLS_DIR = SCRIPT_PATH.parent.parent / "skills"

WORKBENCH_REPO = os.environ.get("DLTHUB_WORKBENCH_REPO", "https://github.com/dlt-hub/dlthub-ai-workbench.git")
WORKBENCH_BRANCH = "master"
WORKBENCH_REF_SHORT = "e8bcc26"
WORKBENCH_REF = "e8bcc26a8a2c72c0228f2c917802cdfed25f9af0"
SKILL_TOOLKITS = ("init",)

_KEEP = ".gitkeep"
_IGNORE = shutil.ignore_patterns(".DS_Store", "__pycache__")
_FULL_REF_RE = re.compile(r'^(?P<prefix>WORKBENCH_REF\s*=\s*)"[^"]*"', re.MULTILINE)


def _selected_toolkits() -> tuple[str, ...]:
    override = os.environ.get("DLTHUB_SKILL_TOOLKITS", "")
    parsed = tuple(name.strip() for name in override.split(",") if name.strip())
    return parsed or SKILL_TOOLKITS


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def _pin_full_ref(full: str) -> None:
    if full == WORKBENCH_REF:
        return
    content = SCRIPT_PATH.read_text(encoding="utf-8")
    new_content, count = _FULL_REF_RE.subn(rf'\g<prefix>"{full}"', content)
    if count != 1:
        raise SystemExit(f"error: expected one WORKBENCH_REF assignment, found {count}")
    SCRIPT_PATH.write_text(new_content, encoding="utf-8")
    print(f"Pinned WORKBENCH_REF: {WORKBENCH_REF} -> {full}")


def _reset_skills_dir() -> None:
    SKILLS_DIR.mkdir(exist_ok=True)
    for entry in SKILLS_DIR.iterdir():
        if entry.name == _KEEP:
            continue
        shutil.rmtree(entry) if entry.is_dir() else entry.unlink()


def _copy_toolkit_skills(workbench: Path, toolkits: tuple[str, ...]) -> dict[str, str]:
    collected: dict[str, str] = {}
    for toolkit in toolkits:
        skills_root = workbench / "workbench" / toolkit / "skills"
        if not skills_root.is_dir():
            raise SystemExit(f"error: toolkit {toolkit!r} has no skills/ directory")
        for skill in sorted(p for p in skills_root.iterdir() if p.is_dir()):
            if skill.name in collected:
                raise SystemExit(
                    f"error: duplicate skill {skill.name!r} from {toolkit!r} and {collected[skill.name]!r}"
                )
            collected[skill.name] = toolkit
            shutil.copytree(skill, SKILLS_DIR / skill.name, ignore=_IGNORE)
    return collected


def main() -> int:
    toolkits = _selected_toolkits()
    ref_override = os.environ.get("DLTHUB_WORKBENCH_REF")
    with tempfile.TemporaryDirectory(prefix="dlthub-skills-") as tmp:
        workbench = Path(tmp) / "workbench"
        subprocess.run(["git", "clone", "--quiet", WORKBENCH_REPO, str(workbench)], check=True)
        if ref_override:
            print(f"Building from override ref {ref_override!r} (not pinning)")
            _git(workbench, "checkout", "--quiet", ref_override)
        else:
            full = _git(workbench, "rev-parse", WORKBENCH_REF_SHORT)
            _pin_full_ref(full)
            _git(workbench, "checkout", "--quiet", full)
        _reset_skills_dir()
        collected = _copy_toolkit_skills(workbench, toolkits)
    print(f"Wrote {len(collected)} skill(s) from [{', '.join(toolkits)}]: {', '.join(sorted(collected))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
