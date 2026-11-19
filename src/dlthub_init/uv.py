"""uv detection and `uv sync` execution."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from . import strings
from .errors import UvError


def find_uv() -> str | None:
    # uv sets `UV` to its own executable for the commands it runs, `uvx` included
    return os.environ.get("UV") or shutil.which("uv")


def run_uv_sync(uv_executable: str, project_dir: Path, *, verbose: bool = False) -> None:
    command = [uv_executable, "sync"]
    try:
        subprocess.run(command, cwd=project_dir, env=isolated_project_env(), check=True, capture_output=not verbose)
    except FileNotFoundError as exc:
        raise UvError(strings.ERROR_UV_COMMAND_NOT_FOUND.format(cmd=uv_executable)) from exc
    except subprocess.CalledProcessError as exc:
        message = strings.ERROR_UV_COMMAND_FAILED.format(returncode=exc.returncode, cmd=" ".join(command))
        captured = _format_captured(exc.stderr, exc.stdout)
        if captured:
            message = f"{message}\n\n{captured}"
        raise UvError(message) from exc


def isolated_project_env() -> dict[str, str]:
    """The current environment without the variables that point uv at another environment."""
    env = os.environ.copy()
    for name in ("VIRTUAL_ENV", "CONDA_PREFIX", "PYTHONPATH"):
        env.pop(name, None)
    return env


def _format_captured(stderr: bytes | None, stdout: bytes | None) -> str:
    parts: list[str] = []
    for stream in (stderr, stdout):
        if not stream:
            continue
        decoded = stream.decode("utf-8", errors="replace").rstrip()
        if decoded:
            parts.append(decoded)
    return "\n\n".join(parts)
