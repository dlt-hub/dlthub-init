"""Project-wide constants for the `dlthub-init` CLI."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

DISTRIBUTION_NAME = "dlthub-init"

try:
    VERSION = version(DISTRIBUTION_NAME)
except PackageNotFoundError:
    VERSION = "0.0.0+unknown"

DEFAULT_SCAFFOLD = "minimal_workspace"
