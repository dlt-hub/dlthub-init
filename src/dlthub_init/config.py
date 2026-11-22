"""Project-wide constants for the `dlthub-init` CLI."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

DISTRIBUTION_NAME = "dlthub-init"

try:
    VERSION = version(DISTRIBUTION_NAME)
except PackageNotFoundError:
    VERSION = "0.0.0+unknown"

POSTHOG_HOST = "https://eu.i.posthog.com"

# 1.33.0a0 and a1 take `--agent` but cannot merge, so they run `dlthub ai init` separately
AGENT_INIT_MIN_DLT = "1.33.0a2"
"""First dlt whose `dlthub init` sets up the coding agent and merges into existing projects."""
