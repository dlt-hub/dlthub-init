"""CLI-specific exceptions."""

from __future__ import annotations


class WorkspaceError(Exception):
    """Base exception for expected user-facing failures."""


class UvError(WorkspaceError):
    """Raised when running uv fails."""


class DlthubCommandError(WorkspaceError):
    """Raised when a `dlthub` command exits non-zero. Its output is already on the screen."""

    def __init__(self, step: str, returncode: int, hint: str | None = None) -> None:
        self.step = step
        self.returncode = returncode
        self.hint = hint
        super().__init__(f"dlthub {step} failed with exit code {returncode}")
