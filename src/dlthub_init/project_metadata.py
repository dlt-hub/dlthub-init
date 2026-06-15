"""Customize the generated workspace's identity."""

from __future__ import annotations

import re
from pathlib import Path

from . import strings
from .errors import ScaffoldError

CONFIG_PATH = Path(".dlt") / "config.toml"
_SECTION = "[workspace.settings]"


def apply_workspace_name(project_dir: Path, workspace_name: str) -> str:
    """Set the workspace name in `.dlt/config.toml` and return the normalized value."""
    name = normalize_project_name(workspace_name)
    config = project_dir / CONFIG_PATH
    if not config.exists():
        return name

    try:
        content = config.read_text(encoding="utf-8")
        config.write_text(_replace_workspace_name(content, name), encoding="utf-8")
    except OSError as exc:
        raise ScaffoldError(strings.ERROR_WRITE_FAILED.format(path=config, reason=exc)) from exc
    return name


def normalize_project_name(name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower()
    return normalized or "dlthub-workspace"


def _replace_workspace_name(content: str, name: str) -> str:
    lines = content.splitlines(keepends=True)
    in_section = False

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == _SECTION:
            in_section = True
            continue
        if in_section and stripped.startswith("["):
            break
        if in_section and re.match(r"^name\s*=", stripped):
            newline = "\n" if line.endswith("\n") else ""
            lines[index] = f'name = "{name}"{newline}'
            return "".join(lines)

    section_at = next((i for i, line in enumerate(lines) if line.strip() == _SECTION), None)
    if section_at is None:
        return content
    lines.insert(section_at + 1, f'name = "{name}"\n')
    return "".join(lines)
