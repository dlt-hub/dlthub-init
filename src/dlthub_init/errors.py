"""CLI-specific exceptions."""

from __future__ import annotations


class WorkspaceError(Exception):
    """Base exception for expected user-facing failures."""


class ScaffoldError(WorkspaceError):
    """Raised when the bundled scaffold cannot be copied into the target directory."""


class CollisionError(ScaffoldError):
    """Raised when existing paths would block initialization.

    Carries the conflicting relative paths so the CLI can render an actionable
    response listing exactly what stopped the run.
    """

    def __init__(self, conflicts: list[str]) -> None:
        self.conflicts = conflicts
        super().__init__(", ".join(conflicts))


class UvError(WorkspaceError):
    """Raised when uv detection, installation, or execution fails."""
