"""Install the bundled secrets-read guard hook into a scaffolded workspace.

The canonical guard script lives once in the repo-root hooks/ directory (synced
from the dltHub AI workbench by scripts/generate_skills.py). The wheel
force-includes it at dlthub_init/_bundled_hooks/; a source checkout reads it
from repo-root hooks/. The script is copied to .agents/hooks/ and referenced by
per-agent hook configs (.claude/settings.json, .cursor/hooks.json,
.codex/hooks.json) that all point at that single copy.

Agents give no common guarantee about the hook process's working directory:
Claude Code exposes $CLAUDE_PROJECT_DIR for project-level settings; Cursor and
Codex expose nothing, so their commands locate the project root via
`git rev-parse --show-toplevel`, falling back to the current directory.
Codex hooks are written to .codex/hooks.json rather than .codex/config.toml
because repo-local config.toml hooks do not fire in interactive sessions
(openai/codex#17532).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .errors import ScaffoldError
from . import strings

_PACKAGE_DIR = Path(__file__).resolve().parent
_BUNDLED_HOOKS = _PACKAGE_DIR / "_bundled_hooks"
_SOURCE_HOOKS = _PACKAGE_DIR.parents[1] / "hooks"

_SCRIPT_NAME = "secrets_guard.py"
CANONICAL_DIR = Path(".agents") / "hooks"

_CLAUDE_COMMAND = 'python3 "$CLAUDE_PROJECT_DIR"/.agents/hooks/secrets_guard.py'
_GIT_ROOT_COMMAND = 'python3 "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"/.agents/hooks/secrets_guard.py'


def hooks_source() -> Path | None:
    if _BUNDLED_HOOKS.is_dir():
        return _BUNDLED_HOOKS
    if _SOURCE_HOOKS.is_dir():
        return _SOURCE_HOOKS
    return None


def install_hooks(project_dir: Path) -> list[str]:
    """Copy the guard script into .agents/hooks/ and register it with each agent.

    Merges into existing config files without clobbering unrelated content, and
    skips any config that already references the guard script. Configs that
    exist but are not valid JSON are left untouched. Returns the names of the
    agent configs newly written or updated.
    """
    source = hooks_source()
    if source is None or not (source / _SCRIPT_NAME).is_file():
        return []

    try:
        script_dest = project_dir / CANONICAL_DIR / _SCRIPT_NAME
        if not script_dest.exists():
            script_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / _SCRIPT_NAME, script_dest)

        configured: list[str] = []
        if _configure_claude(project_dir):
            configured.append("claude")
        if _configure_cursor(project_dir):
            configured.append("cursor")
        if _configure_codex(project_dir):
            configured.append("codex")
    except OSError as exc:
        raise ScaffoldError(strings.ERROR_WRITE_FAILED.format(path=project_dir, reason=exc)) from exc
    return configured


def _pretooluse_entry(command: str, matcher: str) -> dict[str, Any]:
    return {
        "matcher": matcher,
        "hooks": [{"type": "command", "command": command}],
    }


def _configure_claude(project_dir: Path) -> bool:
    path = project_dir / ".claude" / "settings.json"
    settings = _load_json_object(path)
    if settings is None:
        return False

    pre_tool_use = settings.setdefault("hooks", {}).setdefault("PreToolUse", [])
    if _references_guard(pre_tool_use):
        return False
    pre_tool_use.append(_pretooluse_entry(_CLAUDE_COMMAND, "Read|Grep|Bash"))
    _write_json(path, settings)
    return True


def _configure_cursor(project_dir: Path) -> bool:
    path = project_dir / ".cursor" / "hooks.json"
    config = _load_json_object(path)
    if config is None:
        return False

    config.setdefault("version", 1)
    hooks = config.setdefault("hooks", {})
    changed = False
    for event in ("beforeReadFile", "beforeShellExecution"):
        entries = hooks.setdefault(event, [])
        if not _references_guard(entries):
            entries.append({"command": _GIT_ROOT_COMMAND})
            changed = True
    if changed:
        _write_json(path, config)
    return changed


def _configure_codex(project_dir: Path) -> bool:
    path = project_dir / ".codex" / "hooks.json"
    config = _load_json_object(path)
    if config is None:
        return False

    pre_tool_use = config.setdefault("hooks", {}).setdefault("PreToolUse", [])
    if _references_guard(pre_tool_use):
        return False
    # Codex has no dedicated Read/Grep tool; file access goes through shell
    pre_tool_use.append(_pretooluse_entry(_GIT_ROOT_COMMAND, "Bash"))
    _write_json(path, config)
    return True


def _references_guard(entries: object) -> bool:
    return _SCRIPT_NAME in json.dumps(entries)


def _load_json_object(path: Path) -> dict[str, Any] | None:
    """Read a JSON config, returning {} if absent and None if unusable."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
